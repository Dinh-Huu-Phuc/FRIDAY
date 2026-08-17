from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def iou(self, other: BoundingBox) -> float:
        intersection_x1 = max(self.x1, other.x1)
        intersection_y1 = max(self.y1, other.y1)
        intersection_x2 = min(self.x2, other.x2)
        intersection_y2 = min(self.y2, other.y2)
        intersection = max(0, intersection_x2 - intersection_x1) * max(
            0, intersection_y2 - intersection_y1
        )
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0.0


@dataclass(frozen=True, slots=True)
class Detection:
    class_id: int
    label: str
    confidence: float
    box: BoundingBox


@dataclass(frozen=True, slots=True)
class TrackedObject:
    track_id: int
    class_id: int
    label: str
    confidence: float
    box: BoundingBox
    age_frames: int = 1


class TargetLockState(str, Enum):
    SEARCHING = "searching"
    ACQUIRING = "acquiring"
    LOCKED = "locked"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class TargetLock:
    state: TargetLockState = TargetLockState.SEARCHING
    target: TrackedObject | None = None
    stable_frames: int = 0


@dataclass(frozen=True, slots=True)
class SceneSnapshot:
    sequence: int = 0
    captured_at: float = 0.0
    frame_width: int = 0
    frame_height: int = 0
    objects: tuple[TrackedObject, ...] = ()
    target_lock: TargetLock = TargetLock()
    inference_ms: float | None = None
    detector_fps: float = 0.0
    status: str = "idle"
    model_name: str = ""
    error: str = ""

    @classmethod
    def idle(cls, *, status: str = "idle", error: str = "") -> SceneSnapshot:
        return cls(captured_at=time(), status=status, error=error)
