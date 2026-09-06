from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from friday.app.perception.detection.schemas import BoundingBox


class GroundingStatus(str, Enum):
    READY = "ready"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class GroundingMatch:
    label: str
    confidence: float
    box: BoundingBox


@dataclass(frozen=True, slots=True)
class GroundingResult:
    status: GroundingStatus
    query: str
    answer: str
    matches: tuple[GroundingMatch, ...] = ()
    model: str = ""
    provider: str = ""
    device: str = ""
    keyframe_sequence: int | None = None
    frame_width: int = 0
    frame_height: int = 0
    latency_ms: float | None = None
    completed_at: float = 0.0
    used_cache: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {GroundingStatus.READY, GroundingStatus.NOT_FOUND}

    def is_fresh(self, ttl_seconds: float, *, now: float | None = None) -> bool:
        if self.completed_at <= 0 or ttl_seconds <= 0:
            return False
        current = time.monotonic() if now is None else now
        return current - self.completed_at <= ttl_seconds


@dataclass(frozen=True, slots=True)
class GroundingIntentMatch:
    matched: bool = False
    query: str = ""
    trigger_id: str = ""
