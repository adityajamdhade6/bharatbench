"""Exact match after normalising case, spaces and punctuation."""
from __future__ import annotations

import unicodedata

from .base import Score


def normalize(text: str) -> str:
    """NFKC, case-fold, then drop whitespace, punctuation, symbols and control chars.

    Combining marks (category M) are kept so Devanagari vowel signs survive.
    """
    t = unicodedata.normalize("NFKC", str(text)).casefold()
    return "".join(c for c in t if unicodedata.category(c)[0] not in "ZPSC")


def score_exact(response: str, reference: str) -> Score:
    got, want = normalize(response), normalize(reference)
    ok = got == want
    return Score(1.0 if ok else 0.0, f"normalised reply {got[:60]!r} vs reference {want!r}")
