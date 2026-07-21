from __future__ import annotations

from collections.abc import Callable, Sequence


def neural_ode_step(
    h0: Sequence[float],
    dynamics_fn: Callable[[Sequence[float], float], Sequence[float]],
    *,
    t0: float = 0.0,
    t1: float = 1.0,
    steps: int = 50,
) -> list[float]:
    if steps <= 0 or t1 <= t0:
        return [float(v) for v in h0]
    dt = (t1 - t0) / steps
    state = [float(v) for v in h0]
    t = t0
    for _ in range(steps):
        delta = list(dynamics_fn(state, t))
        for i in range(min(len(state), len(delta))):
            state[i] += dt * float(delta[i])
        t += dt
    return state
