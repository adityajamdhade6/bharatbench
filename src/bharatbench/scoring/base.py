"""Shared types and helpers for scorers."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    score: float          # 0.0 .. 1.0
    detail: str = ""      # why (parsed value, judge reason, ...)
    raw: int | None = None  # rubric only: the judge's 0/1/2


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)


def extract_json_object(text: str) -> dict | None:
    """First JSON object in `text` (handles ```json fences and surrounding prose)."""
    if not isinstance(text, str):
        return None
    candidates = [text.strip()] + [m.strip() for m in _FENCE.findall(text)]
    decoder = json.JSONDecoder()
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        for i, ch in enumerate(cand):
            if ch == "{":
                try:
                    obj, _ = decoder.raw_decode(cand[i:])
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    return obj
    return None
