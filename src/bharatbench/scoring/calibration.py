"""Check the LLM judge against your own hand grades.

Flow: judge-sample writes a blind sheet (no judge scores shown) -> you fill in human_score
(0, 1 or 2) -> judge-agree runs the judge on the same replies and reports agreement.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from ..adapters.base import AdapterError
from .rubric import SCALE_TEXT, Judge
from .stats import agreement

THRESHOLD = 0.80
COLUMNS = ["item_id", "task_id", "model", "prompt", "response", "rubric", "human_score", "notes"]


def sample_items(results_dir: Path, run_ids: list[str], tasks_by_id: dict[str, dict], n: int, seed: int = 0):
    """Random sample of rubric replies. Returns (items, available_count)."""
    pool = []
    for run_id in run_ids:
        path = Path(results_dir) / run_id / "responses.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            task = tasks_by_id.get(r["task_id"])
            if task and task["answer_type"] == "rubric" and r.get("response") and not r.get("error"):
                pool.append({"item_id": f"{run_id}|{r['task_id']}|{r['provider']}/{r['model']}",
                             "task_id": r["task_id"], "model": f"{r['provider']}/{r['model']}",
                             "prompt": task["prompt"], "response": r["response"],
                             "rubric": "\n".join(f"- {c}" for c in task["reference_answer"])})
    pool.sort(key=lambda x: x["item_id"])
    random.Random(seed).shuffle(pool)
    return pool[:n], len(pool)


def write_sheet(items: list[dict], path: Path) -> None:
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel shows Hindi correctly
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for it in items:
            w.writerow({**it, "human_score": "", "notes": ""})


def read_grades(path: Path) -> tuple[list[dict], int]:
    """Graded rows and the number left blank. Raises on a grade that is not 0, 1 or 2."""
    graded, blank = [], 0
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            g = (row.get("human_score") or "").strip()
            if not g:
                blank += 1
                continue
            if g not in {"0", "1", "2"}:
                raise ValueError(f"row {i}: human_score must be 0, 1 or 2, got {g!r}")
            row["human_score"] = int(g)
            graded.append(row)
    if not graded:
        raise ValueError("no graded rows: fill in the human_score column first")
    return graded, blank


def run_agreement(graded: list[dict], judge: Judge, tasks_by_id: dict[str, dict]) -> dict:
    human, judged, items, failed = [], [], [], []
    for row in graded:
        task = tasks_by_id[row["task_id"]]
        try:
            j = judge.judge(task, row["response"])
        except AdapterError as e:
            failed.append({"item_id": row["item_id"], "error": str(e)})
            continue
        human.append(row["human_score"])
        judged.append(j.score)
        items.append({"item_id": row["item_id"], "task_id": row["task_id"], "model": row["model"],
                      "human": row["human_score"], "judge": j.score, "judge_reason": j.reason,
                      "notes": row.get("notes", "")})
    if not human:
        raise ValueError("the judge produced no usable grades")
    stats = agreement(human, judged)
    passed = stats["exact_agreement"] >= THRESHOLD and not failed
    if passed:
        verdict = (f"Judge agrees with your grades on {stats['exact_agreement']:.0%} of {stats['n']} items "
                   f"(threshold {THRESHOLD:.0%}).")
    else:
        verdict = (f"Judge agrees on only {stats['exact_agreement']:.0%} of {stats['n']} items "
                   f"(threshold {THRESHOLD:.0%})"
                   + (f"; {len(failed)} item(s) could not be judged" if failed else "")
                   + ". Do not trust the judge yet: review the disagreements and fix the rubric.")
    return {"judge": judge.name, "threshold": THRESHOLD, "passed": passed, "verdict": verdict,
            "agreement": stats, "unjudged": failed, "rubric_scale": SCALE_TEXT, "items": items,
            "disagreements": [i for i in items if i["human"] != i["judge"]]}
