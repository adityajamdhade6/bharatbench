import json

import pytest

from bharatbench.report import build_analysis, compute_facts, fmt_distinct, pick_failures
from bharatbench.scoring.run import score_run
from test_score_run import TASKS, fake_judge, make_run


def scored(tmp_path):
    d = make_run(tmp_path / "results")
    score_run(d, TASKS, judge=fake_judge(tmp_path), iterations=100)
    data = tmp_path / "data"
    data.mkdir()
    (data / "t.jsonl").write_text("\n".join(json.dumps(t) for t in TASKS.values()), encoding="utf-8")
    return d, data


def test_fmt_distinct_never_hides_a_difference():
    assert fmt_distinct([0.81, 0.72]) == ["81.0%", "72.0%"]
    a, b = fmt_distinct([0.7234, 0.7231])
    assert a != b
    assert fmt_distinct([0.5, 0.5]) == ["50.0%", "50.0%"]


def test_facts_come_from_scores_json(tmp_path):
    d, _ = scored(tmp_path)
    scores = json.loads((d / "scores.json").read_text(encoding="utf-8"))
    f = compute_facts(scores)
    assert [r["label"] for r in f["ranking"]] == ["good", "bad"]
    assert f["top"]["mean"] == scores["models"]["fake/good"]["overall"]["mean"] == 1.0
    assert f["bottom"]["mean"] == scores["models"]["fake/bad"]["overall"]["mean"]
    assert f["hardest"] in f["categories"] and f["cat_avg"][f["hardest"]] == min(f["cat_avg"].values())
    assert f["lowest_cell"]["value"] == min(v["mean"] for m in scores["models"].values() for v in m["categories"].values())


def test_language_gap_is_english_minus_hinglish():
    scores = {"run_id": "r", "generated": "2026-01-01T00:00:00", "bootstrap": {"iterations": 10},
              "models": {"p/a": {"overall": {"mean": 0.8, "ci95": [0.7, 0.9], "n": 10}, "api_errors_excluded": 0,
                                 "categories": {"gst_tax": {"mean": 0.8, "ci95": [0.7, 0.9], "n": 10}},
                                 "languages": {"en": {"mean": 0.9, "ci95": [0.8, 1.0], "n": 6},
                                               "hinglish": {"mean": 0.6, "ci95": [0.4, 0.8], "n": 4}}}}}
    f = compute_facts(scores)
    assert f["gaps"]["p/a"] == pytest.approx(0.3) and f["hinglish_lower_count"] == 1
    assert f["mean_en"] == 0.9 and f["mean_hinglish"] == 0.6


def test_pick_failures_is_varied_deterministic_and_capped():
    tasks = {f"t{i}": {"id": f"t{i}", "category": c} for i, c in enumerate(["gst_tax", "gst_tax", "documents", "law_policy"])}
    items = [{"task_id": t, "model": m, "score": 0.0, "detail": "x"} for t in tasks for m in ("m1", "m2")]
    a = pick_failures(items, {}, tasks, n=3)
    assert a == pick_failures(items, {}, tasks, n=3)
    assert len(a) == 3 and len({i["task_id"] for i in a}) == 3
    assert {tasks[i["task_id"]]["category"] for i in a} == {"gst_tax", "documents", "law_policy"}
    assert pick_failures([{"task_id": "t0", "model": "m", "score": 1.0, "detail": ""}], {}, tasks) == []


def test_analysis_markdown_has_all_sections_and_the_numbers(tmp_path):
    d, data = scored(tmp_path)
    md = build_analysis(d, data)
    for heading in ("## Overall leaderboard", "## Per category", "## English, Hindi and Hinglish", "## Ten example failures"):
        assert heading in md
    scores = json.loads((d / "scores.json").read_text(encoding="utf-8"))
    assert f"{scores['models']['fake/bad']['overall']['mean'] * 100:.1f}%" in md
    assert "Model answer" in md and "Correct answer" in md


def facts_for(tmp_path):
    d, _ = scored(tmp_path)
    return compute_facts(json.loads((d / "scores.json").read_text(encoding="utf-8")))


def test_headline_numbers_are_in_scores_json(tmp_path):
    import re
    from bharatbench.report import headline_points
    d, _ = scored(tmp_path)
    scores = json.loads((d / "scores.json").read_text(encoding="utf-8"))
    f = compute_facts(scores)
    text = " ".join(headline_points(f))
    allowed = set()
    for m in scores["models"].values():
        allowed.add(f"{m['overall']['mean'] * 100:.1f}")
        for v in list(m["categories"].values()) + list(m["languages"].values()):
            allowed.add(f"{v['mean'] * 100:.1f}")
    for c, avg in f["cat_avg"].items():
        allowed.add(f"{avg * 100:.1f}")
    allowed.add("%.1f" % ((f["top"]["mean"] - f["bottom"]["mean"]) * 100))
    allowed |= {f"{v * 100:.1f}" for v in (f["mean_en"], f["mean_hinglish"]) if v is not None}
    for n in re.findall(r"\d+\.\d+(?=%|-point)", text):
        assert n in allowed, n


def test_x_thread_fits_and_linkedin_names_the_caveats(tmp_path):
    from bharatbench.report import linkedin_post, x_thread
    f = facts_for(tmp_path)
    assert all(len(t) <= 280 for t in x_thread(f))
    post = linkedin_post(f)
    assert "AI assistance" in post and "private" in post and "human spot-check" in post


def test_readme_block_is_replaced_in_place(tmp_path):
    from bharatbench.report import README_END, README_START, update_readme
    f = facts_for(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(f"# T\n{README_START}\nOLDCONTENT\n{README_END}\nafter\n", encoding="utf-8")
    update_readme(readme, f)
    out = readme.read_text(encoding="utf-8")
    assert "OLDCONTENT" not in out and out.startswith("# T\n") and out.endswith("after\n") and f"{f['top']['mean'] * 100:.1f}%" in out
    readme.write_text("no markers", encoding="utf-8")
    with pytest.raises(ValueError):
        update_readme(readme, f)


def test_rule_heavy_framing_only_when_the_data_supports_it():
    from bharatbench.report import headline_points, rule_heavy_is_hardest, x_thread

    def facts(avgs):
        return {"cat_avg": avgs, "n_models": 2, "ranking": [{"label": "a", "mean": 0.9, "n": 5}, {"label": "b", "mean": 0.5, "n": 5}],
                "top": {"label": "a", "mean": 0.9, "n": 5}, "bottom": {"label": "b", "mean": 0.5, "n": 5}, "overlapping_top": [], "gap_models": 0,
                "cat_n": {c: 5 for c in avgs},
                "lowest_cell": {"model": "b", "category": "gst_tax", "value": 0.4}, "hinglish_lower_count": 0, "mean_en": None, "mean_hinglish": None}

    rules = facts({"gst_tax": 0.5, "law_policy": 0.6, "payments_banking": 0.7, "documents": 0.9, "hinglish_support": 0.95})
    other = facts({"gst_tax": 0.9, "law_policy": 0.6, "payments_banking": 0.7, "documents": 0.5, "hinglish_support": 0.55})
    assert rule_heavy_is_hardest(rules) and not rule_heavy_is_hardest(other)
    assert "rule-heavy" in " ".join(headline_points(rules)) and "rule-heavy" not in " ".join(headline_points(other))
    assert "rules, not language" in " ".join(x_thread(rules)) and "rules, not language" not in " ".join(x_thread(other))
