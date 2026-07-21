from __future__ import annotations

from collections.abc import Callable, Sequence


def monte_carlo_integral(samples: Sequence[float], f: Callable[[float], float]) -> float:
    if not samples:
        return 0.0
    return sum(f(float(x_i)) for x_i in samples) / len(samples)
