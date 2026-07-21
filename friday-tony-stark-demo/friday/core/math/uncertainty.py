from __future__ import annotations

import math
from collections.abc import Mapping

from ..constants import DEFAULT_EPSILON


def entropy(probabilities: Mapping[str, float], *, epsilon: float = DEFAULT_EPSILON) -> float:
    if not probabilities:
        return 0.0
    return -sum(float(p_i) * math.log(float(p_i) + epsilon) for p_i in probabilities.values())
