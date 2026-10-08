"""Bootstrap confidence intervals and judge-vs-human agreement."""
from __future__ import annotations

import math
import random


def bootstrap_ci(values: list[float], iterations: int = 10_000, seed: int = 0,
                 level: float = 0.95) -> tuple[float, float, float]:
    """(mean, low, high): percentile bootstrap over items, resampled with replacement."""
    n = len(values)
    if n == 0:
        raise ValueError("no values to bootstrap")
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(iterations))
    lo = means[int((1 - level) / 2 * iterations)]
    hi = means[min(iterations - 1, math.ceil((1 + level) / 2 * iterations) - 1)]
    return sum(values) / n, lo, hi


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def agreement(human: list[int], judge: list[int], classes: tuple[int, ...] = (0, 1, 2)) -> dict:
    """Exact agreement, within-one agreement, confusion matrix and quadratic-weighted kappa."""
    if len(human) != len(judge) or not human:
        raise ValueError("need two equal-length, non-empty grade lists")
    n, k = len(human), len(classes)
    idx = {c: i for i, c in enumerate(classes)}
    conf = [[0] * k for _ in range(k)]  # rows = human, cols = judge
    for h, j in zip(human, judge):
        conf[idx[h]][idx[j]] += 1
    exact = sum(conf[i][i] for i in range(k))
    within1 = sum(1 for h, j in zip(human, judge) if abs(h - j) <= 1)
    lo, hi = wilson_interval(exact, n)

    rows = [sum(r) for r in conf]
    cols = [sum(conf[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * conf[i][j]
            den += w * rows[i] * cols[j] / n
    kappa = None if den == 0 else 1 - num / den
    return {
        "n": n, "exact_agreement": exact / n, "exact_ci95": [lo, hi], "within_one": within1 / n,
        "confusion_human_rows_judge_cols": conf, "quadratic_weighted_kappa": kappa,
    }
