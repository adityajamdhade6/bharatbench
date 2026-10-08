import json

import pytest

from bharatbench import cli
from bharatbench.export import build_export
from bharatbench.scoring.run import score_run
from test_score_run import ANSWERS, TASKS, fake_judge, make_run


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)


def scored_run(tmp_path):
    results = tmp_path / "results"
    d = make_run(results)
    score_run(d, TASKS, judge=fake_judge(tmp_path), iterations=100)
    data = tmp_path / "data"
    data.mkdir()
    (data / "t.jsonl").write_text("\n".join(json.dumps(t) for t in TASKS.values()), encoding="utf-8")
    return d, data


def test_language_breakdown_is_in_scores_json(tmp_path):
    d, _ = scored_run(tmp_path)
    langs = json.loads((d / "scores.json").read_text(encoding="utf-8"))["models"]["fake/good"]["languages"]
    assert langs["en"]["n"] == 5 and langs["en"]["mean"] == 1.0


def test_export_numbers_come_from_scores_json(tmp_path):
    d, data = scored_run(tmp_path)
    scores = json.loads((d / "scores.json").read_text(encoding="utf-8"))
    out = build_export(d, data)
    by_id = {m["id"]: m for m in out["models"]}
    for name, m in scores["models"].items():
        assert by_id[name]["overall"] == m["overall"]
        assert by_id[name]["categories"] == m["categories"]
        assert by_id[name]["languages"] == m["languages"]
    assert out["run_id"] == "r1" and out["last_updated"] == scores["generated"]
    assert out["bootstrap"]["iterations"] == 100


def test_export_totals_and_categories(tmp_path):
    d, data = scored_run(tmp_path)
    out = build_export(d, data)
    t = out["totals"]
    assert t["dataset_tasks"] == 5 and t["verified_tasks"] == 5 and t["scored_tasks"] == 5 and t["models"] == 2
    assert t["scored_by_category"]["gst_tax"] == 2
    assert [c["slug"] for c in out["categories"]] == ["gst-tax", "hinglish-support", "documents", "payments-banking"]


def test_examples_are_scored_tasks_with_answers_and_capped_at_three(tmp_path):
    d, data = scored_run(tmp_path)
    ex = build_export(d, data)["examples"]
    assert {e["id"] for e in ex["gst_tax"]} == {"gst-001", "gst-002"}
    assert all("reference_answer" in e and "prompt" in e for v in ex.values() for e in v)
    assert all(len(v) <= 3 for v in ex.values())


def test_export_cli(tmp_path, capsys):
    d, data = scored_run(tmp_path)
    out = tmp_path / "site" / "data" / "leaderboard.json"
    args = ["export", "--run-id", "r1", "--data-dir", str(data), "--results-dir", str(tmp_path / "results"), "--out", str(out)]
    assert cli.main(args) == 0 and json.loads(out.read_text(encoding="utf-8"))["run_id"] == "r1"
    assert cli.main(["export", "--run-id", "nope", "--results-dir", str(tmp_path / "results")]) == 2


def test_params_and_verification_record_are_exported(tmp_path):
    d, data = scored_run(tmp_path)
    (data / "VERIFICATION.md").write_text(
        "# Verification record\n\nFlags were set by `Claude`.\nChecked twice.\n\n| Tasks | How confirmed |\n|---|---|\n"
        "| gst-001 – gst-020 | Recomputed. |\n| law-001 | Read the **Act**. |\n\n## Held back\nhin-016 – hin-020: rubric tasks.\n",
        encoding="utf-8")
    out = build_export(d, data)
    assert out["params"]["numeric_relative_tolerance"] == 0.005 and out["params"]["judge_agreement_threshold"] == 0.8
    assert out["params"]["temperature"] == 0.0 and "2 =" in out["params"]["rubric_scale"]
    v = out["verification"]
    assert v["statement"] == "Flags were set by Claude. Checked twice."
    assert v["rows"] == [{"tasks": "gst-001 – gst-020", "method": "Recomputed."},
                         {"tasks": "law-001", "method": "Read the Act."}]
    assert v["held_back"] == "hin-016 – hin-020: rubric tasks."


def test_missing_verification_file_is_reported_not_hidden(tmp_path):
    d, data = scored_run(tmp_path)
    assert build_export(d, data)["verification"]["rows"] == []


def test_run_notes_count_repaired_and_excluded_replies(tmp_path):
    from bharatbench.export import run_notes
    d = tmp_path / "run"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"note": "retried empties"}), encoding="utf-8")
    rows = [{"response": "a", "error": None}, {"response": "b", "error": None, "repaired_with_max_output_tokens": 8192},
            {"response": None, "error": "empty"}]
    (d / "responses.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert run_notes(d) == {"note": "retried empties", "repaired_replies": 1, "excluded_replies": 1, "total_replies": 3}
