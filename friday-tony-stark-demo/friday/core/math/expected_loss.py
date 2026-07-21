from __future__ import annotations

from collections.abc import Callable, Sequence


def expected_loss(losses: Sequence[float], probabilities: Sequence[float]) -> float:
    n = min(len(losses), len(probabilities))
    if n == 0:
        return 0.0
    return sum(float(losses[i]) * float(probabilities[i]) for i in range(n))


def expected_loss_from_distribution(
    loss_fn: Callable[[float], float],
    x_samples: Sequence[float],
    p_samples: Sequence[float],
) -> float:
    n = min(len(x_samples), len(p_samples))
    if n == 0:
        return 0.0
    return sum(loss_fn(float(x_samples[i])) * float(p_samples[i]) for i in range(n))
