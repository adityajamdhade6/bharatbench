"""Score a finished run and write results/<run_id>/scores.json."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.base import AdapterError
from . import score_response
from .rubric import Judge
from .stats import bootstrap_ci


def load_task_map(data_dir: Path) -> dict[str, dict]:
    tasks = {}
    for path in sorted(Path(data_dir).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                t = json.loads(line)
                tasks[t["id"]] = t
    return tasks


def _stat(values: list[float], iterations: int, seed: int) -> dict:
    mean, lo, hi = bootstrap_ci(values, iterations=iterations, seed=seed)
    return {"n": len(values), "mean": mean, "ci95": [lo, hi]}


def score_run(run_dir: Path, tasks_by_id: dict[str, dict], *, judge: Judge | None = None,
              skip_rubric: bool = False, iterations: int = 10_000, seed: int = 0,
              judge_validation: dict | None = None) -> dict:
    run_dir = Path(run_dir)
    rows = [json.loads(l) for l in (run_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    if judge is None and not skip_rubric and any(
            tasks_by_id[r["task_id"]]["answer_type"] == "rubric" for r in rows if r["task_id"] in tasks_by_id):
        raise ValueError("this run has rubric tasks: pass a judge model, or skip them with skip_rubric")

    items, per_model = [], defaultdict(
        lambda: {"all": [], "cat": defaultdict(list), "lang": defaultdict(list), "errors": 0, "unscored": 0})
    for r in rows:
        task = tasks_by_id.get(r["task_id"])
        if task is None:
            raise ValueError(f"task {r['task_id']} is in the run but not in the dataset")
        if task["prompt"] != r["prompt"]:
            raise ValueError(f"task {r['task_id']} was edited after this run; scores would be meaningless")
        model = f"{r['provider']}/{r['model']}"
        m = per_model[model]
        if r.get("error") or r.get("response") is None:
            m["errors"] += 1  # an API failure is not a wrong answer: excluded and counted
            continue
        if task["answer_type"] == "rubric" and skip_rubric:
            m["unscored"] += 1
            continue
        try:
            s = score_response(task, r["response"], judge)
        except AdapterError as e:  # judge failed / unparseable
            m["unscored"] += 1
            items.append({"task_id": task["id"], "model": model, "category": task["category"],
                          "answer_type": task["answer_type"], "score": None, "detail": f"unscored: {e}"})
            continue
        m["all"].append(s.score)
        m["cat"][task["category"]].append(s.score)
        m["lang"][task["language"]].append(s.score)
        items.append({"task_id": task["id"], "model": model, "category": task["category"],
                      "answer_type": task["answer_type"], "score": s.score, "rubric_score": s.raw,
                      "detail": s.detail})

    models = {}
    for name, m in sorted(per_model.items()):
        models[name] = {
            "overall": _stat(m["all"], iterations, seed) if m["all"] else None,
            "categories": {c: _stat(v, iterations, seed) for c, v in sorted(m["cat"].items())},
            "languages": {l: _stat(v, iterations, seed) for l, v in sorted(m["lang"].items())},
            "api_errors_excluded": m["errors"],
            "unscored": m["unscored"],
        }
    report = {
        "run_id": run_dir.name,
        "generated": datetime.now(timezone.utc).isoformat(),
        "metric": "mean item score in [0,1]: exact/numeric 0 or 1, extraction share of fields, rubric judge score / 2",
        "bootstrap": {"method": "percentile, resampling tasks with replacement", "iterations": iterations,
                      "level": 0.95, "seed": seed},
        "rubric_skipped": skip_rubric,
        "judge": None if judge is None else {"model": judge.name, "validation": judge_validation},
        "models": models,
    }
    (run_dir / "scores.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (run_dir / "item_scores.jsonl").open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return report
