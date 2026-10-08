import json
from pathlib import Path

import pytest

from bharatbench import cli
from fakes import FakeAdapter, make_task

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)  # never read a real .env in tests


def setup_data(tmp_path, tasks):
    data = tmp_path / "data"
    data.mkdir()
    (data / "t.jsonl").write_text("\n".join(json.dumps(t) for t in tasks), encoding="utf-8")
    return data


def argv(tmp_path, data, *extra):
    return ["run", "--data-dir", str(data), "--results-dir", str(tmp_path / "results"),
            "--cache-dir", str(tmp_path / "cache"), *extra]


def test_run_end_to_end_with_fake_adapter(tmp_path, capsys):
    data = setup_data(tmp_path, [make_task("gst-001"), make_task("gst-002", verified=False)])
    fake = FakeAdapter("gemini-flash")
    code = cli.main(argv(tmp_path, data, "--models", "gemini-flash", "--run-id", "r1"),
                    adapter_factory=lambda spec, settings: fake)
    assert code == 0
    out = (tmp_path / "results" / "r1" / "responses.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["task_id"] for l in out] == ["gst-001"]  # unverified one skipped
    assert "1 API calls" in capsys.readouterr().out


def test_no_verified_tasks_runs_nothing(tmp_path, capsys):
    data = setup_data(tmp_path, [make_task("gst-001", verified=False)])
    fake = FakeAdapter()
    code = cli.main(argv(tmp_path, data, "--models", "x"), adapter_factory=lambda s, st: fake)
    assert code == 0 and fake.calls == []
    assert "No verified tasks" in capsys.readouterr().out
    assert not (tmp_path / "results").exists()


def test_categories_and_limit(tmp_path):
    tasks = [make_task(f"gst-00{i}") for i in range(1, 4)] + [make_task("law-001", "law_policy")]
    tasks[-1]["source_url"] = "https://example.gov.in"
    data = setup_data(tmp_path, tasks)
    fake = FakeAdapter()
    cli.main(argv(tmp_path, data, "--models", "x", "--categories", "gst", "--limit", "2"),
             adapter_factory=lambda s, st: fake)
    assert [c[0] for c in fake.calls] == ["prompt for gst-001", "prompt for gst-002"]


def test_multiple_models_are_comma_separated(tmp_path):
    data = setup_data(tmp_path, [make_task("gst-001")])
    made = []

    def factory(spec, settings):
        made.append(spec)
        return FakeAdapter(spec)

    cli.main(argv(tmp_path, data, "--models", "gemini-flash,llama-3.3-70b"), adapter_factory=factory)
    assert made == ["gemini-flash", "llama-3.3-70b"]


def test_invalid_dataset_refuses_to_run(tmp_path, capsys):
    bad = make_task("gst-001")
    del bad["difficulty"]
    data = setup_data(tmp_path, [bad])
    fake = FakeAdapter()
    code = cli.main(argv(tmp_path, data, "--models", "x"), adapter_factory=lambda s, st: fake)
    assert code == 1 and fake.calls == []
    assert "Dataset is invalid" in capsys.readouterr().err


def test_unknown_model_is_a_clean_error(tmp_path, capsys):
    data = setup_data(tmp_path, [make_task("gst-001")])
    assert cli.main(argv(tmp_path, data, "--models", "no-such-model")) == 2
    assert "unknown model" in capsys.readouterr().err


def test_missing_api_key_is_a_clean_error(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    data = setup_data(tmp_path, [make_task("gst-001")])
    assert cli.main(argv(tmp_path, data, "--models", "gemini-flash")) == 2
    assert "GEMINI_API_KEY" in capsys.readouterr().err


def test_any_error_gives_nonzero_exit(tmp_path):
    data = setup_data(tmp_path, [make_task("gst-001")])
    fake = FakeAdapter(fail_on={"prompt for gst-001"})
    assert cli.main(argv(tmp_path, data, "--models", "x"), adapter_factory=lambda s, st: fake) == 1
