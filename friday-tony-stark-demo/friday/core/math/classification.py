from __future__ import annotations

import math
from collections.abc import Mapping

from ..constants import DEFAULT_EPSILON


def sigmoid(logit: float) -> float:
    if logit >= 0:
        exp_term = math.exp(-logit)
        return 1.0 / (1.0 + exp_term)
    exp_term = math.exp(logit)
    return exp_term / (1.0 + exp_term)


def binary_cross_entropy(
    probabilities: Mapping[str, float],
    targets: Mapping[str, float],
    *,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    if not probabilities:
        return 0.0
    losses = []
    for key, probability in probabilities.items():
        p_i = min(1.0 - epsilon, max(epsilon, float(probability)))
        y_i = float(targets.get(key, 0.0))
        losses.append(-(y_i * math.log(p_i) + (1.0 - y_i) * math.log(1.0 - p_i)))
    return sum(losses) / len(losses)
