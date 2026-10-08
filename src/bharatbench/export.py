"""Export results/<run_id>/scores.json + the task files to one JSON file for the website.

The website reads only this file, so every number it shows traces back to scores.json.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .runner import TEMPERATURE
from .scoring.calibration import THRESHOLD
from .scoring.numeric import REL_TOLERANCE
from .scoring.rubric import SCALE_TEXT
from .scoring.run import load_task_map
from .validate import CATEGORY_PREFIX

SCHEMA_VERSION = 1
CATEGORY_INFO = {
    "gst_tax": ("GST & tax math", "GST slabs, invoices, TDS and simple income tax."),
    "hinglish_support": ("Hinglish & Hindi support", "Understanding and replying to customer messages in Hinglish and Hindi."),
    "documents": ("Indian documents", "Extracting fields from synthetic invoices, rent agreements and bank statements."),
    "law_policy": ("Indian law & policy", "Consumer rights, RTI and labour basics, each tied to an official source."),
    "payments_banking": ("Payments & banking", "UPI failures, refunds, liability and KYC rules."),
}
LANGUAGE_LABELS = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"}
EXAMPLES_PER_CATEGORY = 3


def _slug(category: str) -> str:
    return category.replace("_", "-")


def _pick_examples(tasks: list[dict], n: int) -> list[dict]:
    """Deterministic spread over difficulty, then by id; only tasks that were scored."""
    by_diff: dict[str, list[dict]] = {"easy": [], "medium": [], "hard": []}
    for t in sorted(tasks, key=lambda t: t["id"]):
        by_diff[t["difficulty"]].append(t)
    picked: list[dict] = []
    while len(picked) < n and any(by_diff.values()):
        for d in ("easy", "medium", "hard"):
            if by_diff[d] and len(picked) < n:
                picked.append(by_diff[d].pop(0))
    return sorted(picked, key=lambda t: t["id"])


def _plain(text: str) -> str:
    return re.sub(r"[`*]", "", text).strip()


def parse_verification(path: Path) -> dict:
    """Read data/VERIFICATION.md (the single place the verification story is written down)."""
    empty = {"statement": "No verification record found.", "rows": [], "held_back": ""}
    path = Path(path)
    if not path.exists():
        return empty
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = []
    for line in lines:
        if line.startswith("|") and not line.startswith("|---") and not line.lower().startswith("| tasks"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                rows.append({"tasks": _plain(cells[0]), "method": _plain(cells[1])})
    intro, held, mode = [], [], None
    for line in lines:
        if line.startswith("## "):
            mode = "held" if "held back" in line.lower() else "other"
        elif line.startswith("#") or line.startswith("|") or not line.strip():
            continue
        elif mode is None:
            intro.append(line.strip())
        elif mode == "held":
            held.append(line.strip())
    return {"statement": _plain(" ".join(intro)), "rows": rows, "held_back": _plain(" ".join(held))}


def run_notes(run_dir: Path) -> dict:
    """What the reader should know about how this run's replies were obtained."""
    run_dir = Path(run_dir)
    meta_path = run_dir / "meta.json"
    note = json.loads(meta_path.read_text(encoding="utf-8")).get("note", "") if meta_path.exists() else ""
    rows = [json.loads(l) for l in (run_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"note": note,
            "repaired_replies": sum(1 for r in rows if r.get("repaired_with_max_output_tokens")),
            "excluded_replies": sum(1 for r in rows if r.get("error") or r.get("response") is None),
            "total_replies": len(rows)}


def build_export(run_dir: Path, data_dir: Path) -> dict:
    run_dir = Path(run_dir)
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
    tasks = load_task_map(data_dir)
    scored_ids = {json.loads(l)["task_id"] for l in (run_dir / "item_scores.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    scored = [tasks[i] for i in scored_ids]

    models = []
    for name, m in scores["models"].items():
        provider, _, model = name.partition("/")
        models.append({"id": name, "provider": provider, "model": model, "label": model.split("/")[-1],
                       "overall": m["overall"], "categories": m["categories"], "languages": m.get("languages", {}),
                       "api_errors_excluded": m["api_errors_excluded"], "unscored": m["unscored"]})

    present = [c for c in CATEGORY_PREFIX if any(t["category"] == c for t in scored)]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": scores["run_id"],
        "last_updated": scores["generated"],
        "exported": datetime.now(timezone.utc).isoformat(),
        "metric": scores["metric"],
        "run_notes": run_notes(run_dir),
        "bootstrap": scores["bootstrap"],
        "rubric_skipped": scores["rubric_skipped"],
        "judge": scores["judge"],
        "totals": {
            "dataset_tasks": len(tasks),
            "verified_tasks": sum(1 for t in tasks.values() if t["verified"]),
            "scored_tasks": len(scored),
            "models": len(models),
            "scored_by_category": dict(Counter(t["category"] for t in scored)),
            "scored_by_language": dict(Counter(t["language"] for t in scored)),
            "scored_by_answer_type": dict(Counter(t["answer_type"] for t in scored)),
            "dataset_by_answer_type": dict(Counter(t["answer_type"] for t in tasks.values())),
        },
        "params": {"numeric_relative_tolerance": REL_TOLERANCE, "judge_agreement_threshold": THRESHOLD,
                   "rubric_scale": SCALE_TEXT, "temperature": TEMPERATURE},
        "verification": parse_verification(Path(data_dir) / "VERIFICATION.md"),
        "language_labels": LANGUAGE_LABELS,
        "categories": [{"id": c, "slug": _slug(c), "title": CATEGORY_INFO[c][0], "description": CATEGORY_INFO[c][1]}
                       for c in present],
        "models": models,
        "examples": {c: [{k: t[k] for k in ("id", "prompt", "language", "answer_type", "difficulty",
                                              "reference_answer", "worked_solution", "source_url") if k in t}
                         for t in _pick_examples([t for t in scored if t["category"] == c], EXAMPLES_PER_CATEGORY)]
                     for c in present},
    }


def write_export(run_dir: Path, data_dir: Path, out: Path) -> dict:
    payload = build_export(run_dir, data_dir)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
