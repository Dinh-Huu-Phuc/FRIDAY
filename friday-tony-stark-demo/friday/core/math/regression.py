from __future__ import annotations

from collections.abc import Sequence


def mean_squared_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    n = min(len(y_true), len(y_pred))
    if n == 0:
        return 0.0
    return sum((float(y_true[i]) - float(y_pred[i])) ** 2 for i in range(n)) / n
