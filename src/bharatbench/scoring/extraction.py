"""Field-by-field scoring of a JSON reply against a reference object."""
from __future__ import annotations

from .base import Score, extract_json_object
from .exact import normalize
from .numeric import parse_final_number


def _field_ok(got, want) -> bool:
    if isinstance(want, bool):
        return got is want
    if isinstance(want, (int, float)):
        if isinstance(got, bool):
            return False
        value = float(got) if isinstance(got, (int, float)) else parse_final_number(str(got))
        return value is not None and abs(value - float(want)) < 0.005  # exact to the paisa
    return got is not None and normalize(str(got)) == normalize(str(want))


def _lookup(obj: dict, key: str):
    if key in obj:
        return obj[key]
    folded = {str(k).casefold(): v for k, v in obj.items()}
    return folded.get(key.casefold())


def score_extraction(response: str, reference: dict) -> Score:
    obj = extract_json_object(response)
    if obj is None:
        return Score(0.0, "no JSON object found in reply")
    wrong = [k for k, want in reference.items() if not _field_ok(_lookup(obj, k), want)]
    right = len(reference) - len(wrong)
    detail = f"{right}/{len(reference)} fields correct" + (f"; wrong: {', '.join(wrong)}" if wrong else "")
    return Score(right / len(reference), detail)
