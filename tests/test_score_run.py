import json

import pytest

from bharatbench import cli
from bharatbench.cache import ResponseCache
from bharatbench.scoring.rubric import Judge
from bharatbench.scoring.run import load_task_map, score_run
from fakes import FakeAdapter


def T(tid, category, atype, ref, **kw):
    return {"id": tid, "category": category, "prompt": f"prompt {tid}", "language": "en", "answer_type": atype,
            "reference_answer": ref, "worked_solution": "w", "difficulty": "easy", "verified": True, **kw}


TASKS = {t["id"]: t for t in [
    T("gst-001", "gst_tax", "numeric", 100, tolerance=0.01),
    T("gst-002", "gst_tax", "numeric", 200, tolerance=0.01),
    T("pay-001", "payments_banking", "exact", "T+1"),
    T("doc-001", "documents", "extraction", {"a": 1, "b": "x"}),
    T("hin-016", "hinglish_support", "rubric", ["Be polite"]),
]}

ANSWERS = {
    "good": {"gst-001": "₹100", "gst-002": "200", "pay-001": "t+1", "doc-001": '{"a": 1, "b": "x"}', "hin-016": "namaste"},
    "bad": {"gst-001": "99", "gst-002": "200", "pay-001": "T+2", "doc-001": '{"a": 1, "b": "y"}', "hin-016": "go away"},
}


def make_run(results, run_id="r1", extra_rows=()):
    d = results / run_id
    d.mkdir(parents=True)
    rows = []
    for model, answers in ANSWERS.items():
        for tid, resp in answers.items():
            rows.append({"run_id": run_id, "task_id": tid, "category": TASKS[tid]["category"], "provider": "fake",
                         "model": model, "prompt": TASKS[tid]["prompt"], "response": resp, "error": None})
    rows.extend(extra_rows)
    (d / "responses.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return d


def fake_judge(tmp_path):
    def reply(prompt, system):
        return json.dumps({"reason": "polite" if "namaste" in prompt else "rude", "score": 2 if "namaste" in prompt else 0})
    return Judge(FakeAdapter("judge", reply=reply), ResponseCache(tmp_path / "c"))


def test_scores_json_per_model_and_category(tmp_path):
    d = make_run(tmp_path)
    rep = score_run(d, TASKS, judge=fake_judge(tmp_path), iterations=300)
    on_disk = json.loads((d / "scores.json").read_text(encoding="utf-8"))
    assert on_disk["run_id"] == "r1" and on_disk["bootstrap"]["iterations"] == 300
    good, bad = rep["models"]["fake/good"], rep["models"]["fake/bad"]
    assert good["overall"]["mean"] == 1.0 and good["overall"]["n"] == 5
    # bad: gst 1/2, pay 0, doc 1/2, hinglish 0 -> (0+1+0+0.5+0)/5
    assert bad["overall"]["mean"] == pytest.approx(0.3)
    assert bad["categories"]["gst_tax"]["mean"] == 0.5 and bad["categories"]["gst_tax"]["n"] == 2
    for stat in (good["overall"], bad["overall"], *bad["categories"].values()):
        lo, hi = stat["ci95"]
        assert lo <= stat["mean"] <= hi
    assert set(good["categories"]) == {"gst_tax", "payments_banking", "documents", "hinglish_support"}
    assert on_disk["judge"]["model"] == "fake/judge"


def test_item_scores_are_written_with_reasons(tmp_path):
    d = make_run(tmp_path)
    score_run(d, TASKS, judge=fake_judge(tmp_path), iterations=50)
    items = [json.loads(l) for l in (d / "item_scores.jsonl").read_text(encoding="utf-8").splitlines()]
    rub = [i for i in items if i["answer_type"] == "rubric"]
    assert {i["detail"] for i in rub} == {"polite", "rude"} and len(items) == 10


def test_api_errors_are_excluded_not_counted_wrong(tmp_path):
    err = {"run_id": "r1", "task_id": "gst-001", "category": "gst_tax", "provider": "fake", "model": "good",
           "prompt": TASKS["gst-001"]["prompt"], "response": None, "error": "429 gave up"}
    d = make_run(tmp_path, extra_rows=[err])
    rep = score_run(d, TASKS, judge=fake_judge(tmp_path), iterations=50)
    assert rep["models"]["fake/good"]["api_errors_excluded"] == 1
    assert rep["models"]["fake/good"]["overall"]["n"] == 5


def test_rubric_without_judge_is_refused_unless_skipped(tmp_path):
    d = make_run(tmp_path)
    with pytest.raises(ValueError, match="rubric"):
        score_run(d, TASKS, iterations=50)
    rep = score_run(d, TASKS, skip_rubric=True, iterations=50)
    assert rep["rubric_skipped"] is True and rep["models"]["fake/good"]["overall"]["n"] == 4
    assert rep["models"]["fake/good"]["unscored"] == 1 and rep["judge"] is None


def test_unparseable_judge_output_leaves_item_unscored(tmp_path):
    d = make_run(tmp_path)
    j = Judge(FakeAdapter("judge", reply=lambda p, s: "garbage"), ResponseCache(tmp_path / "c"))
    rep = score_run(d, TASKS, judge=j, iterations=50)
    assert rep["models"]["fake/good"]["unscored"] == 1 and rep["models"]["fake/good"]["overall"]["n"] == 4


def test_task_edited_after_run_is_refused(tmp_path):
    d = make_run(tmp_path)
    edited = {**TASKS, "gst-001": {**TASKS["gst-001"], "prompt": "changed"}}
    with pytest.raises(ValueError, match="edited"):
        score_run(d, edited, judge=fake_judge(tmp_path), iterations=50)


def test_validation_summary_is_recorded(tmp_path):
    d = make_run(tmp_path)
    v = {"judge": "fake/judge", "exact_agreement": 0.9, "passed": True}
    rep = score_run(d, TASKS, judge=fake_judge(tmp_path), iterations=50, judge_validation=v)
    assert rep["judge"]["validation"] == v


# ---------- CLI ----------
@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)


def cli_env(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "t.jsonl").write_text("\n".join(json.dumps(t) for t in TASKS.values()), encoding="utf-8")
    results = tmp_path / "results"
    make_run(results)
    return ["--data-dir", str(data), "--results-dir", str(results), "--cache-dir", str(tmp_path / "cache")], results


def factory(spec, settings):
    def reply(prompt, system):
        return json.dumps({"reason": "ok", "score": 2})
    return FakeAdapter(spec, reply=reply)


def test_cli_score_writes_scores_and_warns_when_judge_unvalidated(tmp_path, capsys):
    dirs, results = cli_env(tmp_path)
    code = cli.main(["score", "--run-id", "r1", "--judge", "judge-x", "--iterations", "100", *dirs], factory)
    out = capsys.readouterr().out
    assert code == 0 and (results / "r1" / "scores.json").exists()
    assert "has not been validated" in out and "fake/good" in out


def test_cli_score_requires_judge_or_skip(tmp_path, capsys):
    dirs, _ = cli_env(tmp_path)
    assert cli.main(["score", "--run-id", "r1", *dirs], factory) == 2
    assert "rubric" in capsys.readouterr().err
    assert cli.main(["score", "--run-id", "r1", "--skip-rubric", "--iterations", "50", *dirs], factory) == 0


def test_cli_score_missing_run(tmp_path, capsys):
    dirs, _ = cli_env(tmp_path)
    assert cli.main(["score", "--run-id", "nope", *dirs], factory) == 2


def test_cli_judge_sample_then_agree(tmp_path, capsys):
    dirs, results = cli_env(tmp_path)
    sheet = tmp_path / "sheet.csv"
    assert cli.main(["judge-sample", "--run-ids", "r1", "--n", "50", "--out", str(sheet), *dirs], factory) == 0
    assert "only 2 rubric replies" in capsys.readouterr().out   # warns: fewer than the 50 requested
    import csv
    rows = list(csv.DictReader(sheet.open(encoding="utf-8-sig")))
    for r in rows:
        r["human_score"] = "2"                                  # judge in `factory` always says 2
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    assert cli.main(["judge-agree", "--grades", str(sheet), "--judge", "judge-x", *dirs], factory) == 0
    result = json.loads(sheet.with_suffix(".agreement.json").read_text(encoding="utf-8"))
    assert result["passed"] is True and result["agreement"]["n"] == 2

    # feed the agreement back into scores.json
    agree = sheet.with_suffix(".agreement.json")
    assert cli.main(["score", "--run-id", "r1", "--judge", "judge-x", "--judge-agreement", str(agree),
                     "--iterations", "50", *dirs], factory) == 0
    scores = json.loads((results / "r1" / "scores.json").read_text(encoding="utf-8"))
    assert scores["judge"]["validation"]["passed"] is True


def test_cli_judge_agree_exit_code_3_when_below_threshold(tmp_path, capsys):
    dirs, _ = cli_env(tmp_path)
    sheet = tmp_path / "sheet.csv"
    cli.main(["judge-sample", "--run-ids", "r1", "--n", "2", "--out", str(sheet), *dirs], factory)
    import csv
    rows = list(csv.DictReader(sheet.open(encoding="utf-8-sig")))
    for r in rows:
        r["human_score"] = "0"                                  # judge says 2 -> total disagreement
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    capsys.readouterr()
    assert cli.main(["judge-agree", "--grades", str(sheet), "--judge", "judge-x", *dirs], factory) == 3
    assert "Do not trust the judge" in capsys.readouterr().out
