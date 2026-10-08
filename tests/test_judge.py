import csv
import json

import pytest

from bharatbench.cache import ResponseCache
from bharatbench.scoring.calibration import (read_grades, run_agreement, sample_items, write_sheet)
from bharatbench.scoring.rubric import (Judge, JudgeParseError, build_judge_prompt, parse_judgement,
                                        score_rubric)
from bharatbench.scoring.stats import agreement, bootstrap_ci, wilson_interval
from fakes import FakeAdapter

CRITERIA = ["Written in Hinglish", "Never asks for an OTP"]
TASK = {"id": "hin-016", "category": "hinglish_support", "prompt": "Reply to the customer.",
        "answer_type": "rubric", "reference_answer": CRITERIA}


# ---------- parsing and prompt ----------
def test_parse_judgement_variants():
    assert parse_judgement('{"reason": "ok", "score": 2}').score == 2
    assert parse_judgement('```json\n{"reason": "meh", "score": "1"}\n```').score == 1
    assert parse_judgement('Here you go: {"score": 0, "reason": "asked for OTP"}').reason == "asked for OTP"


@pytest.mark.parametrize("bad", ["no json", '{"reason": "x"}', '{"score": 3}', '{"score": 1.5}', '{"score": true}'])
def test_parse_judgement_rejects_bad_output(bad):
    with pytest.raises(JudgeParseError):
        parse_judgement(bad)


def test_prompt_contains_rubric_reply_and_scale():
    p = build_judge_prompt("TASKTEXT", "REPLYTEXT", CRITERIA)
    assert "TASKTEXT" in p and "REPLYTEXT" in p
    assert "1. Written in Hinglish" in p and "2. Never asks for an OTP" in p
    assert "2 =" in p and "0 =" in p and "JSON" in p


# ---------- judge + cache ----------
def judge_with(reply, tmp_path):
    a = FakeAdapter("judge-m", reply=reply)
    return Judge(a, ResponseCache(tmp_path / "c")), a


def test_judge_returns_score_and_reason(tmp_path):
    j, _ = judge_with(lambda p, s: '{"reason": "meets all", "score": 2}', tmp_path)
    s = score_rubric(j, TASK, "reply")
    assert s.score == 1.0 and s.raw == 2 and s.detail == "meets all"


def test_judgements_are_cached(tmp_path):
    j, a = judge_with(lambda p, s: '{"reason": "ok", "score": 1}', tmp_path)
    j.judge(TASK, "reply")
    j.judge(TASK, "reply")
    assert len(a.calls) == 1
    j.judge(TASK, "a different reply")
    assert len(a.calls) == 2


def test_malformed_judge_output_is_not_cached(tmp_path):
    outputs = iter(["garbage", '{"reason": "fine", "score": 2}'])
    j, a = judge_with(lambda p, s: next(outputs), tmp_path)
    with pytest.raises(JudgeParseError):
        j.judge(TASK, "reply")
    assert j.judge(TASK, "reply").score == 2
    assert len(a.calls) == 2


def test_judge_sees_the_judge_system_prompt(tmp_path):
    j, a = judge_with(lambda p, s: '{"reason": "", "score": 0}', tmp_path)
    j.judge(TASK, "reply")
    assert "grader" in a.calls[0][1]


# ---------- stats ----------
def test_bootstrap_is_deterministic_and_brackets_mean():
    vals = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    a, b = bootstrap_ci(vals, 2000, seed=1), bootstrap_ci(vals, 2000, seed=1)
    assert a == b
    mean, lo, hi = a
    assert mean == pytest.approx(0.7) and lo <= mean <= hi and 0 <= lo and hi <= 1


def test_bootstrap_constant_values_have_zero_width():
    assert bootstrap_ci([1.0] * 5, 500) == (1.0, 1.0, 1.0)


def test_bootstrap_wider_with_fewer_items():
    small = bootstrap_ci([1, 0] * 3, 2000)
    large = bootstrap_ci([1, 0] * 50, 2000)
    assert (small[2] - small[1]) > (large[2] - large[1])


def test_bootstrap_empty_raises():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_wilson_interval():
    lo, hi = wilson_interval(40, 50)
    assert lo < 0.8 < hi
    assert wilson_interval(0, 0) == (0.0, 0.0)
    assert wilson_interval(50, 50)[1] == pytest.approx(1.0)


def test_agreement_perfect_and_partial():
    perfect = agreement([0, 1, 2, 2], [0, 1, 2, 2])
    assert perfect["exact_agreement"] == 1.0 and perfect["quadratic_weighted_kappa"] == pytest.approx(1.0)
    partial = agreement([0, 1, 2, 2], [0, 1, 2, 1])
    assert partial["exact_agreement"] == 0.75 and partial["within_one"] == 1.0
    assert partial["confusion_human_rows_judge_cols"][2] == [0, 1, 1]


def test_agreement_total_disagreement_has_negative_kappa():
    r = agreement([0, 2, 0, 2], [2, 0, 2, 0])
    assert r["exact_agreement"] == 0.0 and r["quadratic_weighted_kappa"] < 0


def test_agreement_degenerate_kappa_is_none_and_length_checked():
    assert agreement([1, 1], [1, 1])["quadratic_weighted_kappa"] is None
    with pytest.raises(ValueError):
        agreement([1], [1, 2])


# ---------- calibration workflow ----------
def write_run(results, run_id, n_models=2, n_tasks=3):
    d = results / run_id
    d.mkdir(parents=True)
    tasks, rows = {}, []
    for t in range(n_tasks):
        tid = f"hin-0{16 + t}"
        tasks[tid] = {**TASK, "id": tid, "prompt": f"Reply to customer {t} (हिंदी)"}
    for m in range(n_models):
        for tid, task in tasks.items():
            rows.append({"run_id": run_id, "task_id": tid, "provider": "fake", "model": f"m{m}",
                         "prompt": task["prompt"], "response": f"reply {m} {tid} नमस्ते", "error": None})
    rows.append({"run_id": run_id, "task_id": "hin-099", "provider": "fake", "model": "m0",
                 "prompt": "p", "response": None, "error": "boom"})
    (d / "responses.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return tasks


def test_sample_items_counts_and_limits(tmp_path):
    tasks = write_run(tmp_path, "r1")
    items, available = sample_items(tmp_path, ["r1"], tasks, n=50)
    assert available == 6 and len(items) == 6          # fewer than requested: caller can warn
    items4, _ = sample_items(tmp_path, ["r1"], tasks, n=4)
    assert len(items4) == 4
    assert sample_items(tmp_path, ["r1"], tasks, 4, seed=3)[0] == sample_items(tmp_path, ["r1"], tasks, 4, seed=3)[0]


def test_sheet_is_blind_and_roundtrips(tmp_path):
    tasks = write_run(tmp_path, "r1")
    items, _ = sample_items(tmp_path, ["r1"], tasks, 6)
    sheet = tmp_path / "sheet.csv"
    write_sheet(items, sheet)
    header = next(csv.reader(sheet.open(encoding="utf-8-sig")))
    assert "human_score" in header and not any("judge" in h for h in header)
    with pytest.raises(ValueError, match="no graded rows"):
        read_grades(sheet)
    rows = list(csv.DictReader(sheet.open(encoding="utf-8-sig")))
    rows[0]["human_score"], rows[1]["human_score"] = "2", "0"
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    graded, blank = read_grades(sheet)
    assert len(graded) == 2 and blank == 4 and "नमस्ते" in graded[0]["response"]


def test_read_grades_rejects_bad_grade(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("item_id,task_id,model,prompt,response,rubric,human_score,notes\na,b,c,d,e,f,5,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="0, 1 or 2"):
        read_grades(p)


def graded_rows(grades):
    return [{"item_id": f"i{i}", "task_id": "hin-016", "model": "m", "response": f"reply {i}",
             "human_score": g, "notes": ""} for i, g in enumerate(grades)]


def judge_scoring(by_reply, tmp_path):
    def reply(prompt, system):
        for text, score in by_reply.items():
            if f"<<<\n{text}\n>>>" in prompt:
                return json.dumps({"reason": "r", "score": score})
        raise AssertionError("unexpected reply")
    return judge_with(reply, tmp_path)[0]


def test_agreement_passes_at_or_above_80_percent(tmp_path):
    human = [2, 1, 0, 2, 1]
    judge = judge_scoring({f"reply {i}": s for i, s in enumerate([2, 1, 0, 2, 0])}, tmp_path)  # 4/5 = 80%
    out = run_agreement(graded_rows(human), judge, {"hin-016": TASK})
    assert out["agreement"]["exact_agreement"] == 0.8 and out["passed"] is True
    assert len(out["disagreements"]) == 1 and out["disagreements"][0]["judge_reason"] == "r"


def test_agreement_below_80_percent_fails_and_says_so(tmp_path):
    human = [2, 1, 0, 2, 1]
    judge = judge_scoring({f"reply {i}": s for i, s in enumerate([2, 0, 0, 1, 0])}, tmp_path)  # 2/5
    out = run_agreement(graded_rows(human), judge, {"hin-016": TASK})
    assert out["passed"] is False and "fix the rubric" in out["verdict"]


def test_unjudgeable_items_block_a_pass(tmp_path):
    outputs = iter(['{"reason": "r", "score": 2}', "garbage", "garbage", "garbage"])
    j, _ = judge_with(lambda p, s: next(outputs), tmp_path)
    out = run_agreement(graded_rows([2, 2]), j, {"hin-016": TASK})
    assert out["passed"] is False and len(out["unjudged"]) == 1
