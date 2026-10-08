import dataclasses

from bharatbench.adapters.base import Settings
from bharatbench.cache import ResponseCache, cache_key

S = Settings()


def k(**over):
    args = dict(provider="groq", model="m", prompt="p", system=None, settings=S)
    args.update(over)
    return cache_key(**args)


def test_key_is_stable():
    assert k() == k()


def test_key_changes_with_every_input():
    base = k()
    variants = [k(provider="gemini"), k(model="m2"), k(prompt="p2"), k(system="s"),
                k(settings=dataclasses.replace(S, temperature=0.7)),
                k(settings=dataclasses.replace(S, max_output_tokens=5))]
    assert len({base, *variants}) == 7


def test_roundtrip_and_miss(tmp_path):
    c = ResponseCache(tmp_path)
    assert c.get(k()) is None
    c.put(k(), "जवाब ✓", model="m")
    assert c.get(k()) == "जवाब ✓"
    assert ResponseCache(tmp_path).get(k()) == "जवाब ✓"  # persisted on disk


def test_corrupt_entry_is_a_miss(tmp_path):
    c = ResponseCache(tmp_path)
    c.put(k(), "x")
    next(tmp_path.rglob("*.json")).write_text("{broken", encoding="utf-8")
    assert c.get(k()) is None


def test_no_temp_files_left(tmp_path):
    ResponseCache(tmp_path).put(k(), "x")
    assert not list(tmp_path.rglob("*.tmp"))
