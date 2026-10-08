"""Numeric scoring: parse the final number in a reply and compare within tolerance."""
from __future__ import annotations

import re
from decimal import Decimal

from .base import Score

REL_TOLERANCE = 0.005  # ±0.5%

_MULTIPLIERS = {
    "thousand": Decimal(10) ** 3,
    "lakh": Decimal(10) ** 5, "lakhs": Decimal(10) ** 5, "lac": Decimal(10) ** 5, "lacs": Decimal(10) ** 5,
    "crore": Decimal(10) ** 7, "crores": Decimal(10) ** 7, "cr": Decimal(10) ** 7,
}
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER = re.compile(
    r"(?<!\w)(-?\d[\d,]*(?:\.\d+)?)(?:\s*(lakhs?|lacs?|crores?|cr|thousand)\b)?", re.I)
_ANSWER_MARKER = re.compile(r"(final answer|answer|उत्तर)\s*[:：=\-–]?", re.I)


def parse_final_number(text: str) -> float | None:
    """The final number in the reply: the one right after the last 'Answer:' marker if the
    reply has one, otherwise the last number in the text.

    Understands ₹ / Rs, Indian and Western commas, Devanagari digits and
    lakh / crore / thousand suffixes ('1.2 crore' -> 12000000).
    """
    if not isinstance(text, str):
        return None
    text = text.translate(_DEVANAGARI_DIGITS).replace("*", "")
    markers = list(_ANSWER_MARKER.finditer(text))
    after_marker = _NUMBER.search(text[markers[-1].end():]) if markers else None
    if after_marker:
        match = after_marker  # 'Answer: 4050 (half of 8,100)' -> the number right after the marker
    else:
        matches = list(_NUMBER.finditer(text))
        if not matches:
            return None
        match = matches[-1]
    raw, unit = match.groups()
    value = Decimal(raw.replace(",", "").rstrip("."))
    if unit:
        value *= _MULTIPLIERS[unit.lower()]
    return float(value)


def within_tolerance(got: float, want: float, abs_tol: float = 0.0) -> bool:
    allowed = max(REL_TOLERANCE * abs(want), abs_tol)
    return abs(got - want) <= allowed + 1e-9


def score_numeric(response: str, reference: float, abs_tol: float = 0.0) -> Score:
    got = parse_final_number(response)
    if got is None:
        return Score(0.0, "no number found in reply")
    ok = within_tolerance(got, float(reference), abs_tol)
    return Score(1.0 if ok else 0.0, f"parsed {got:g}, expected {reference:g}")
