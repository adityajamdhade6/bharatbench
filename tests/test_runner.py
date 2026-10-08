import json

import pytest

from bharatbench.adapters.base import Settings
from bharatbench.cache import ResponseCache
from bharatbench.runner import run
from fakes import FakeAdapter, make_task


def rows(summary):
    return [json.loads(l) for l in (summary.out_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def env(tmp_path):
    return ResponseCache(tmp_path / "cache"), tmp_path / "results"


def test_saves_every_raw_response(env):
    cache, results = env
    tasks = [make_task("gst-001"), make_task("gst-002")]
    s = run([FakeAdapter()], tasks, cache, results, run_id="r1")
    r = rows(s)
    assert [x["task_id"] for x in r] == ["gst-001", "gst-002"]
    assert r[0]["response"] == "echo:prompt for gst-001"
    assert r[0]["model"] == "fake-1" and r[0]["temperature"] == 0.0 and r[0]["cached"] is False
    assert (results / "r1" / "meta.json").exists()
    assert s.api_calls == 2 and s.errors == 0


def test_runs_each_model_over_each_task(env):
    cache, results = env
    a, b = FakeAdapter("m-a"), FakeAdapter("m-b")
    s = run([a, b], [make_task("gst-001"), make_task("gst-002")], cache, results)
    assert len(a.calls) == len(b.calls) == 2 and s.total == 4


def test_unverified_tasks_are_refused(env):
    cache, results = env
    a = FakeAdapter()
    with pytest.raises(ValueError, match="unverified"):
        run([a], [make_task("gst-001"), make_task("gst-002", verified=False)], cache, results)
    assert a.calls == []


def test_non_zero_temperature_is_refused(env):
    cache, results = env
    a = FakeAdapter(settings=Settings(temperature=0.7))
    with pytest.raises(ValueError, match="temperature"):
        run([a], [make_task("gst-001")], cache, results)


def test_rerun_costs_nothing(env):
    cache, results = env
    tasks = [make_task("gst-001"), make_task("gst-002")]
    run([FakeAdapter()], tasks, cache, results, run_id="r1")
    second = FakeAdapter()
    s = run([second], tasks, cache, results, run_id="r2")
    assert second.calls == [] and s.cache_hits == 2 and s.api_calls == 0
    assert all(x["cached"] for x in rows(s))
    assert rows(s)[0]["response"] == "echo:prompt for gst-001"


def test_cache_is_per_model_and_per_system_prompt(env):
    cache, results = env
    t = [make_task("gst-001")]
    run([FakeAdapter("m-a")], t, cache, results, run_id="r1")
    other_model, same_model_new_system = FakeAdapter("m-b"), FakeAdapter("m-a")
    run([other_model], t, cache, results, run_id="r2")
    run([same_model_new_system], t, cache, results, run_id="r3", system="be terse")
    assert len(other_model.calls) == 1 and len(same_model_new_system.calls) == 1


def test_failures_are_recorded_not_cached_and_do_not_stop_the_run(env):
    cache, results = env
    tasks = [make_task("gst-001"), make_task("gst-002")]
    a = FakeAdapter(fail_on={"prompt for gst-001"})
    s = run([a], tasks, cache, results, run_id="r1")
    r = rows(s)
    assert r[0]["error"] == "boom" and r[0]["response"] is None
    assert r[1]["response"] == "echo:prompt for gst-002"
    assert s.errors == 1
    retry = FakeAdapter()
    run([retry], tasks, cache, results, run_id="r2")
    assert len(retry.calls) == 1  # only the failed one is called again


def test_existing_run_id_is_never_overwritten(env):
    cache, results = env
    run([FakeAdapter()], [make_task("gst-001")], cache, results, run_id="r1")
    with pytest.raises(FileExistsError):
        run([FakeAdapter()], [make_task("gst-001")], cache, results, run_id="r1")


def test_system_prompt_is_passed_through(env):
    cache, results = env
    a = FakeAdapter()
    run([a], [make_task("gst-001")], cache, results, system="answer briefly")
    assert a.calls == [("prompt for gst-001", "answer briefly")]


def test_models_run_concurrently_and_every_row_is_written(env):
    import threading
    cache, results = env
    barrier = threading.Barrier(2, timeout=5)  # both models must be inside generate() at once

    class Waiting(FakeAdapter):
        def generate(self, prompt, system=None):
            if not self.calls:
                barrier.wait()
            return super().generate(prompt, system)

    s = run([Waiting("m-a"), Waiting("m-b")], [make_task("gst-001"), make_task("gst-002")], cache, results)
    r = rows(s)
    assert len(r) == 4 and s.total == 4 and s.api_calls == 4
    assert {(x["model"], x["task_id"]) for x in r} == {(m, t) for m in ("m-a", "m-b") for t in ("gst-001", "gst-002")}
    per_model = [[x["task_id"] for x in r if x["model"] == m] for m in ("m-a", "m-b")]
    assert per_model == [["gst-001", "gst-002"]] * 2   # order kept within each model
