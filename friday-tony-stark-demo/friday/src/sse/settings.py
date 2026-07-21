from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SseSettings:
    heartbeat_interval_seconds: int = 15
    queue_max_size: int = 100
