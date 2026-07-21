from __future__ import annotations

import math
from collections.abc import Sequence

from ..constants import DEFAULT_MARGIN


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    a_norm = math.sqrt(sum(float(a[i]) ** 2 for i in range(n)))
    b_norm = math.sqrt(sum(float(b[i]) ** 2 for i in range(n)))
    if a_norm == 0.0 or b_norm == 0.0:
        return 0.0
    return dot / (a_norm * b_norm)


def euclidean_distance(a: Sequence[float], b: Sequence[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(n)))


def contrastive_loss(
    a: Sequence[float],
    b: Sequence[float],
    y: int,
    *,
    margin: float = DEFAULT_MARGIN,
) -> float:
    d_ab = euclidean_distance(a, b)
    if int(y) == 1:
        return d_ab**2
    return max(0.0, margin - d_ab) ** 2


def triplet_loss(
    anchor: Sequence[float],
    positive: Sequence[float],
    negative: Sequence[float],
    *,
    margin: float = DEFAULT_MARGIN,
) -> float:
    d_ap = euclidean_distance(anchor, positive)
    d_an = euclidean_distance(anchor, negative)
    return max(0.0, d_ap - d_an + margin)
