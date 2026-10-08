"""Scoring of model outputs against task answers."""
from __future__ import annotations

from .base import Score
from .exact import normalize, score_exact
from .extraction import score_extraction
from .numeric import parse_final_number, score_numeric
from .rubric import Judge, JudgeParseError, Judgement, score_rubric


def score_response(task: dict, response: str, judge: Judge | None = None) -> Score:
    """Score one reply according to the task's answer_type."""
    kind, ref = task["answer_type"], task["reference_answer"]
    if kind == "exact":
        return score_exact(response, ref)
    if kind == "numeric":
        return score_numeric(response, ref, task.get("tolerance", 0.0))
    if kind == "extraction":
        return score_extraction(response, ref)
    if kind == "rubric":
        if judge is None:
            raise ValueError(f"{task['id']} is a rubric task; a judge is required")
        return score_rubric(judge, task, response)
    raise ValueError(f"unknown answer_type {kind!r}")


__all__ = ["Score", "Judge", "JudgeParseError", "Judgement", "score_response", "score_exact",
           "score_numeric", "score_extraction", "score_rubric", "normalize", "parse_final_number"]
