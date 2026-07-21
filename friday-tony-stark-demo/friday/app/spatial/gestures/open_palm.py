from __future__ import annotations


def _is_extended(points: dict[int, tuple[float, float, float]], tip: int, pip: int) -> bool:
    tip_point = points.get(tip)
    pip_point = points.get(pip)
    if tip_point is None or pip_point is None:
        return False
    return tip_point[1] < pip_point[1]


def detect_open_palm(points: dict[int, tuple[float, float, float]]) -> tuple[bool, float]:
    extended = [
        _is_extended(points, 8, 6),
        _is_extended(points, 12, 10),
        _is_extended(points, 16, 14),
        _is_extended(points, 20, 18),
    ]
    score = sum(1 for value in extended if value) / 4
    return score >= 0.75, score
