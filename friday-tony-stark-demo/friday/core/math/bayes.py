from __future__ import annotations

from collections.abc import Sequence


def bayesian_evidence_integral(likelihood: Sequence[float], prior: Sequence[float]) -> float:
    n = min(len(likelihood), len(prior))
    if n == 0:
        return 0.0
    return sum(float(likelihood[i]) * float(prior[i]) for i in range(n))
