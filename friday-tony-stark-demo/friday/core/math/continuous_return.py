from __future__ import annotations

import math
from collections.abc import Callable


def continuous_discounted_return(
    reward_fn: Callable[[float], float],
    *,
    t_start: float = 0.0,
    t_end: float = 20.0,
    gamma: float = 0.1,
    steps: int = 200,
) -> float:
    if steps <= 1 or t_end <= t_start:
        return 0.0
    dt = (t_end - t_start) / (steps - 1)
    total = 0.0
    for idx in range(steps):
        tau = t_start + idx * dt
        weight = math.exp(-gamma * (tau - t_start))
        total += weight * float(reward_fn(tau))
    return total * dt
