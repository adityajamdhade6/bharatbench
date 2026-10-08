"""Load tasks from data/*.jsonl, keeping only hand-verified ones."""
from __future__ import annotations

import json
from pathlib import Path

from .validate import CATEGORY_PREFIX

CATEGORY_ALIASES = {
    "gst": "gst_tax", "tax": "gst_tax", "gst_tax": "gst_tax",
    "hinglish": "hinglish_support", "support": "hinglish_support", "hinglish_support": "hinglish_support",
    "docs": "documents", "documents": "documents",
    "law": "law_policy", "policy": "law_policy", "law_policy": "law_policy",
    "payments": "payments_banking", "banking": "payments_banking", "payments_banking": "payments_banking",
}


def resolve_categories(names: list[str] | None) -> list[str]:
    if not names:
        return list(CATEGORY_PREFIX)
    out = []
    for n in names:
        key = n.strip().lower()
        if key not in CATEGORY_ALIASES:
            raise ValueError(f"unknown category {n!r}. Valid: {', '.join(sorted(CATEGORY_ALIASES))}")
        if CATEGORY_ALIASES[key] not in out:
            out.append(CATEGORY_ALIASES[key])
    return out


def load_tasks(data_dir: Path, categories: list[str] | None = None, *,
               limit_per_category: int | None = None, verified_only: bool = True) -> list[dict]:
    """Return tasks sorted by id. Unverified tasks are dropped unless verified_only=False."""
    wanted = resolve_categories(categories)
    tasks = []
    for path in sorted(Path(data_dir).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tasks.append(json.loads(line))
    tasks = [t for t in tasks if t["category"] in wanted and (t["verified"] is True or not verified_only)]
    tasks.sort(key=lambda t: t["id"])
    if limit_per_category is not None:
        counts: dict[str, int] = {}
        kept = []
        for t in tasks:
            counts[t["category"]] = counts.get(t["category"], 0) + 1
            if counts[t["category"]] <= limit_per_category:
                kept.append(t)
        tasks = kept
    return tasks
