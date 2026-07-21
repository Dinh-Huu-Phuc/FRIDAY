from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..constants import DEFAULT_ALPHA, DEFAULT_USER_STYLE_LAMBDA, DEFAULT_W1, DEFAULT_W2, DEFAULT_W3


def smooth_session_mood(
    previous_mood: Mapping[str, float] | None,
    current_emotion: Mapping[str, float],
    *,
    alpha: float = DEFAULT_ALPHA,
) -> dict[str, float]:
    if not previous_mood:
        return {k: float(v) for k, v in current_emotion.items()}
    keys = sorted(set(previous_mood) | set(current_emotion))
    return {
        key: alpha * float(previous_mood.get(key, 0.0)) + (1.0 - alpha) * float(current_emotion.get(key, 0.0))
        for key in keys
    }


def update_user_style(
    previous: Sequence[float] | None,
    current: Sequence[float],
    *,
    retention_lambda: float = DEFAULT_USER_STYLE_LAMBDA,
) -> list[float]:
    if not previous:
        return [float(v) for v in current]
    max_size = max(len(previous), len(current))
    out: list[float] = []
    for idx in range(max_size):
        old_v = float(previous[idx]) if idx < len(previous) else 0.0
        cur_v = float(current[idx]) if idx < len(current) else 0.0
        out.append(retention_lambda * old_v + (1.0 - retention_lambda) * cur_v)
    return out


def fuse_state(
    e_t: Mapping[str, float],
    m_t: Mapping[str, float],
    u_t_projected: Mapping[str, float],
    *,
    w1: float = DEFAULT_W1,
    w2: float = DEFAULT_W2,
    w3: float = DEFAULT_W3,
) -> dict[str, float]:
    keys = sorted(set(e_t) | set(m_t) | set(u_t_projected))
    total = w1 + w2 + w3
    if total <= 0:
        w1, w2, w3, total = DEFAULT_W1, DEFAULT_W2, DEFAULT_W3, 1.0
    return {
        key: (w1 * float(e_t.get(key, 0.0)) + w2 * float(m_t.get(key, 0.0)) + w3 * float(u_t_projected.get(key, 0.0)))
        / total
        for key in keys
    }
