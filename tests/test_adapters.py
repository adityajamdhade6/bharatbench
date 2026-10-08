import json

import httpx
import pytest

from bharatbench.adapters import (GeminiAdapter, GroqAdapter, OpenRouterAdapter, build_adapter,
                                  resolve_model)
from bharatbench.adapters.base import (Adapter, AdapterError, MissingKeyError, RateLimiter,
                                       RateLimitError, RetryPolicy, Settings, TransientError)


class Clock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def test_rate_limiter_spaces_calls():
    c = Clock()
    rl = RateLimiter(rpm=30, clock=c.now, sleep=c.sleep)  # one call every 2s
    for _ in range(3):
        rl.wait()
    assert c.sleeps == [2.0, 2.0]


def test_rate_limiter_no_wait_when_idle():
    c = Clock()
    rl = RateLimiter(rpm=60, clock=c.now, sleep=c.sleep)
    rl.wait()
    c.t = 100
    rl.wait()
    assert c.sleeps == []


def test_retry_policy_backoff_and_cap():
    p = RetryPolicy(base_delay=2, max_delay=10, jitter=0)
    assert [p.delay(n, None, 0) for n in (1, 2, 3, 4, 5)] == [2, 4, 8, 10, 10]
    assert p.delay(1, 30, 0) == 30  # Retry-After wins when larger


class Flaky(Adapter):
    provider = "flaky"

    def __init__(self, errors, **kw):
        super().__init__("m", **kw)
        self.errors = list(errors)
        self.n = 0

    def _request(self, prompt, system):
        self.n += 1
        if self.errors:
            raise self.errors.pop(0)
        return "ok"


def flaky(errors, **kw):
    c = Clock()
    a = Flaky(errors, sleep=c.sleep, rand=lambda: 0.0,
              retry=RetryPolicy(max_attempts=4, base_delay=1, jitter=0), **kw)
    return a, c


def test_retries_then_succeeds():
    a, c = flaky([RateLimitError("429"), TransientError("5xx")])
    assert a.generate("hi") == "ok"
    assert a.n == 3 and c.sleeps == [1, 2]


def test_retry_after_is_honoured():
    a, c = flaky([RateLimitError("429", retry_after=30)])
    a.generate("hi")
    assert c.sleeps == [30]


def test_gives_up_after_max_attempts():
    a, _ = flaky([TransientError("x")] * 10)
    with pytest.raises(AdapterError, match="gave up after 4 attempts"):
        a.generate("hi")
    assert a.n == 4


def test_permanent_error_not_retried():
    a, c = flaky([AdapterError("bad request")])
    with pytest.raises(AdapterError, match="bad request"):
        a.generate("hi")
    assert a.n == 1 and c.sleeps == []


def test_limiter_is_used_per_attempt():
    c = Clock()
    rl = RateLimiter(rpm=60, clock=c.now, sleep=c.sleep)
    a = Flaky([TransientError("x")], limiter=rl, sleep=c.sleep, rand=lambda: 0.0,
              retry=RetryPolicy(base_delay=0, jitter=0))
    a.generate("hi")
    assert a.n == 2 and 1.0 in c.sleeps  # limiter spaced the retry from the first call


# ---- HTTP adapters, using httpx.MockTransport (no real network) ----

def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def gemini_ok(request):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Hel"}, {"text": "lo"}]}}]})


def chat_ok(request):
    return httpx.Response(200, json={"choices": [{"message": {"content": "Hello"}}]})


def test_gemini_request_and_parse():
    seen = {}

    def handler(request):
        seen["url"], seen["key"] = str(request.url), request.headers["x-goog-api-key"]
        seen["body"] = json.loads(request.content)
        return gemini_ok(request)

    a = GeminiAdapter("gemini-x", api_key="k", client=client_for(handler))
    assert a.generate("नमस्ते", system="be brief") == "Hello"
    assert seen["url"].endswith("/models/gemini-x:generateContent")
    assert seen["key"] == "k"
    body = seen["body"]
    assert body["contents"][0]["parts"][0]["text"] == "नमस्ते"
    assert body["systemInstruction"]["parts"][0]["text"] == "be brief"
    assert body["generationConfig"]["temperature"] == 0.0


@pytest.mark.parametrize("cls,host", [(GroqAdapter, "api.groq.com"), (OpenRouterAdapter, "openrouter.ai")])
def test_openai_compatible_request_and_parse(cls, host):
    seen = {}

    def handler(request):
        seen["host"], seen["auth"] = request.url.host, request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return chat_ok(request)

    a = cls("some-model", Settings(temperature=0.0, max_output_tokens=77), api_key="secret",
            client=client_for(handler))
    assert a.generate("hi", system="sys") == "Hello"
    assert seen["host"] == host and seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "some-model"
    assert seen["body"]["temperature"] == 0.0 and seen["body"]["max_tokens"] == 77
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


def test_http_429_retries_using_retry_after():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "7"})
        return chat_ok(request)

    c = Clock()
    a = GroqAdapter("m", api_key="k", client=client_for(handler), sleep=c.sleep, rand=lambda: 0.0)
    assert a.generate("hi") == "Hello"
    assert calls["n"] == 2 and c.sleeps == [7.0]


def test_http_500_is_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else chat_ok(request)

    c = Clock()
    a = GroqAdapter("m", api_key="k", client=client_for(handler), sleep=c.sleep, rand=lambda: 0.0)
    assert a.generate("hi") == "Hello" and calls["n"] == 3


def test_http_400_is_not_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, text="bad model")

    a = GroqAdapter("m", api_key="k", client=client_for(handler), sleep=lambda s: None)
    with pytest.raises(AdapterError, match="HTTP 400"):
        a.generate("hi")
    assert calls["n"] == 1


def test_network_error_is_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("down")
        return chat_ok(request)

    a = GroqAdapter("m", api_key="k", client=client_for(handler), sleep=lambda s: None, rand=lambda: 0.0)
    assert a.generate("hi") == "Hello" and calls["n"] == 2


def test_gemini_blocked_response_is_an_error():
    def handler(request):
        return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

    a = GeminiAdapter("m", api_key="k", client=client_for(handler))
    with pytest.raises(AdapterError, match="SAFETY"):
        a.generate("hi")


@pytest.mark.parametrize("cls,var", [(GeminiAdapter, "GEMINI_API_KEY"), (GroqAdapter, "GROQ_API_KEY"),
                                     (OpenRouterAdapter, "OPENROUTER_API_KEY")])
def test_key_read_from_environment(monkeypatch, cls, var):
    monkeypatch.delenv(var, raising=False)
    with pytest.raises(MissingKeyError, match=var):
        cls("m")
    monkeypatch.setenv(var, "from-env")
    assert cls("m")._key == "from-env"


def test_resolve_model():
    assert resolve_model("gemini-flash")[0] == "gemini"
    assert resolve_model("llama-3.3-70b")[0] == "groq"
    assert resolve_model("openrouter:acme/model-1") == ("openrouter", "acme/model-1")
    with pytest.raises(ValueError):
        resolve_model("nope")
    with pytest.raises(ValueError):
        resolve_model("bogus:model")


def test_build_adapter_attaches_rate_limiter(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    a = build_adapter("llama-3.3-70b", Settings())
    assert a.provider == "groq" and a.limiter is not None


def test_daily_quota_429_fails_fast_without_retrying():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(429, text='{"error": {"details": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}}')

    a = GeminiAdapter("m", api_key="k", client=client_for(handler), sleep=lambda s: pytest.fail("must not sleep"))
    with pytest.raises(AdapterError, match="daily quota"):
        a.generate("hi")
    assert calls["n"] == 1


def test_one_limiter_is_shared_per_provider(monkeypatch):
    from bharatbench.adapters import provider_limiter
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    a, b = build_adapter("gemini-flash-lite"), build_adapter("gemini-3.1-flash-lite")
    assert a.limiter is b.limiter is provider_limiter("gemini")


def test_empty_reply_is_an_error_not_a_cached_answer():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "\n\n"}, "finish_reason": "length"}]})

    a = GroqAdapter("m", api_key="k", client=client_for(handler))
    with pytest.raises(AdapterError, match="empty reply"):
        a.generate("hi")

    def gemini_empty(request):
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": " "}]}}]})

    with pytest.raises(AdapterError, match="empty reply"):
        GeminiAdapter("m", api_key="k", client=client_for(gemini_empty)).generate("hi")


def test_default_token_budget_leaves_room_for_reasoning_models():
    assert Settings().max_output_tokens >= 8192 and Settings().temperature == 0.0


def test_in_flight_credit_402_is_retried_but_other_402_is_not():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(402, text="would exceed your available credits given your current in-flight requests")
        return chat_ok(request)

    c = Clock()
    a = GroqAdapter("m", api_key="k", client=client_for(handler), sleep=c.sleep, rand=lambda: 0.0)
    assert a.generate("hi") == "Hello" and calls["n"] == 2

    b = GroqAdapter("m", api_key="k", client=client_for(lambda r: httpx.Response(402, text="add credits")), sleep=c.sleep)
    with pytest.raises(AdapterError, match="HTTP 402"):
        b.generate("hi")
