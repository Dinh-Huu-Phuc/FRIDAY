from __future__ import annotations

from threading import RLock

from friday.core.hardware import (
    VisionRuntimeDecision,
    decide_vision_runtime,
    probe_hardware,
)

_LOCK = RLock()
_DECISION: VisionRuntimeDecision | None = None


def get_vision_runtime_decision(*, refresh: bool = False) -> VisionRuntimeDecision:
    global _DECISION
    with _LOCK:
        if refresh or _DECISION is None:
            _DECISION = decide_vision_runtime(probe_hardware())
        return _DECISION
