"""Common adapter interface, rate limiting and retry logic."""
from __future__ import annotations

import os
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

import httpx


@dataclass(frozen=True)
class Settings:
    """Generation settings. Part of the cache key."""

    temperature: float = 0.0
    max_output_tokens: int = 8192  # reasoning models spend much of this on hidden thinking


class AdapterError(Exception):
    """A non-retryable provider error."""


class MissingKeyError(AdapterError):
    pass


class TransientError(AdapterError):
    """A retryable error (network problem or 5xx)."""


class RateLimitError(TransientError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    """Spaces calls at least 60/rpm seconds apart. Thread-safe."""

    def __init__(self, rpm: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        if rpm <= 0:
            raise ValueError("rpm must be positive")
        self.interval = 60.0 / rpm
        self._clock, self._sleep = clock, sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            self._sleep(start - now)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 6
    base_delay: float = 2.0
    max_delay: float = 60.0
    jitter: float = 0.25  # up to +25% random extra delay

    def delay(self, attempt: int, retry_after: float | None, rand: float) -> float:
        backoff = min(self.max_delay, self.base_delay * 2 ** (attempt - 1))
        backoff *= 1 + self.jitter * rand
        if retry_after is not None:
            return max(retry_after, backoff)
        return backoff


class Adapter(ABC):
    """One provider + model. `generate(prompt, system) -> text`."""

    provider: str = ""

    def __init__(self, model: str, settings: Settings = Settings(), *,
                 limiter: RateLimiter | None = None, retry: RetryPolicy = RetryPolicy(),
                 sleep: Callable[[float], None] = time.sleep,
                 rand: Callable[[], float] = random.random):
        self.model = model
        self.settings = settings
        self.limiter = limiter
        self.retry = retry
        self._sleep = sleep
        self._rand = rand

    @abstractmethod
    def _request(self, prompt: str, system: str | None) -> str:
        """One raw call. Raise RateLimitError / TransientError / AdapterError."""

    def generate(self, prompt: str, system: str | None = None) -> str:
        last: Exception | None = None
        for attempt in range(1, self.retry.max_attempts + 1):
            if self.limiter:
                self.limiter.wait()
            try:
                return self._request(prompt, system)
            except TransientError as e:
                last = e
                if attempt == self.retry.max_attempts:
                    break
                retry_after = e.retry_after if isinstance(e, RateLimitError) else None
                self._sleep(self.retry.delay(attempt, retry_after, self._rand()))
        raise AdapterError(f"{self.provider}/{self.model}: gave up after "
                           f"{self.retry.max_attempts} attempts: {last}") from last


def require_key(env_var: str, api_key: str | None) -> str:
    key = api_key or os.environ.get(env_var)
    if not key:
        raise MissingKeyError(f"{env_var} is not set. Add it to .env (see .env.example).")
    return key


class HttpAdapter(Adapter):
    """Adds an httpx client and maps HTTP failures to adapter errors."""

    def __init__(self, model: str, settings: Settings = Settings(), *,
                 client: httpx.Client | None = None, **kw):
        super().__init__(model, settings, **kw)
        self.client = client or httpx.Client(timeout=120.0)

    def _post(self, url: str, headers: dict, payload: dict) -> dict:
        try:
            r = self.client.post(url, headers=headers, json=payload)
        except httpx.TransportError as e:
            raise TransientError(f"network error: {e}") from e
        if r.status_code == 429:
            if "PerDay" in r.text:  # daily quota exhausted: waiting seconds will not help
                raise AdapterError(f"daily quota exhausted: {r.text[:200]}")
            raise RateLimitError("rate limited (429)", _retry_after(r))
        if r.status_code == 402 and "in-flight" in r.text:  # credit reserved by pending requests; retry later
            raise TransientError("temporarily out of credit reservation (402 in-flight)")
        if r.status_code >= 500:
            raise TransientError(f"server error {r.status_code}")
        if r.status_code >= 400:
            raise AdapterError(f"HTTP {r.status_code}: {r.text[:300]}")
        try:
            return r.json()
        except ValueError as e:
            raise TransientError("invalid JSON in response") from e


def _retry_after(r: httpx.Response) -> float | None:
    v = r.headers.get("retry-after")
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def chat_messages(prompt: str, system: str | None) -> list[dict]:
    msgs = [{"role": "system", "content": system}] if system else []
    msgs.append({"role": "user", "content": prompt})
    return msgs
