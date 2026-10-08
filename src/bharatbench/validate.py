"""Validate data/*.jsonl task files against data/schema/task.schema.json.

Usage: uv run python -m bharatbench.validate [--data-dir data] [--expect-per-category 20]
Exits non-zero on any problem.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

CATEGORY_PREFIX = {
    "gst_tax": "gst",
    "hinglish_support": "hin",
    "documents": "doc",
    "law_policy": "law",
    "payments_banking": "pay",
}

ANSWER_TYPE_CHECKS = {
    "numeric": lambda a: isinstance(a, (int, float)) and not isinstance(a, bool),
    "exact": lambda a: isinstance(a, str),
    "extraction": lambda a: isinstance(a, dict),
    "rubric": lambda a: isinstance(a, list),
}


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "schema" / "task.schema.json"


def load_tasks(path: Path) -> tuple[list[tuple[int, dict]], list[str]]:
    """Return ([(line_no, task)], errors) for one JSONL file."""
    tasks, errors = [], []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}:{n}: invalid JSON ({e.msg})")
            continue
        if not isinstance(obj, dict):
            errors.append(f"{path.name}:{n}: task must be a JSON object")
            continue
        tasks.append((n, obj))
    return tasks, errors


def validate_dir(
    data_dir: Path,
    schema_path: Path | None = None,
    expect_per_category: int | None = None,
) -> list[str]:
    schema = json.loads((schema_path or default_schema_path()).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    seen: dict[str, str] = {}
    per_category: Counter[str] = Counter()

    files = sorted(data_dir.glob("*.jsonl"))
    if not files:
        errors.append(f"no .jsonl files found in {data_dir}")

    for path in files:
        tasks, load_errors = load_tasks(path)
        errors.extend(load_errors)
        for n, task in tasks:
            where = f"{path.name}:{n}"
            for err in sorted(validator.iter_errors(task), key=lambda e: list(e.path)):
                loc = ".".join(str(p) for p in err.path) or "(task)"
                errors.append(f"{where}: {loc}: {err.message}")

            tid = task.get("id")
            if isinstance(tid, str):
                if tid in seen:
                    errors.append(f"{where}: duplicate id {tid!r} (first in {seen[tid]})")
                else:
                    seen[tid] = where

            cat = task.get("category")
            if cat in CATEGORY_PREFIX:
                per_category[cat] += 1
                if isinstance(tid, str) and not tid.startswith(CATEGORY_PREFIX[cat] + "-"):
                    errors.append(f"{where}: id {tid!r} does not match category {cat!r}")
                if cat == "gst_tax" and not task.get("worked_solution"):
                    errors.append(f"{where}: gst_tax tasks need a worked_solution")
                if cat == "law_policy" and not task.get("source_url"):
                    errors.append(f"{where}: law_policy tasks need a source_url")

            at, ref = task.get("answer_type"), task.get("reference_answer")
            if at in ANSWER_TYPE_CHECKS and "reference_answer" in task:
                if not ANSWER_TYPE_CHECKS[at](ref):
                    errors.append(f"{where}: reference_answer type does not fit answer_type {at!r}")
            if "tolerance" in task and at != "numeric":
                errors.append(f"{where}: tolerance is only valid for numeric tasks")

    if expect_per_category is not None:
        for cat in CATEGORY_PREFIX:
            if per_category[cat] != expect_per_category:
                errors.append(
                    f"category {cat}: expected {expect_per_category} tasks, found {per_category[cat]}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data-dir", type=Path, default=default_schema_path().parents[1])
    p.add_argument("--expect-per-category", type=int, default=None)
    args = p.parse_args(argv)
    errors = validate_dir(args.data_dir, expect_per_category=args.expect_per_category)
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        print(f"FAILED: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print("OK: all tasks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
