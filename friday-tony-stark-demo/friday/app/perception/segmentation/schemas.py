from __future__ import annotations

import time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from friday.app.perception.detection.schemas import BoundingBox


class SegmentationStatus(str, Enum):
    IDLE = "idle"
    READY = "ready"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class SegmentationMode(str, Enum):
    SINGLE_FRAME = "single_frame"
    PRECISE_TRACKING = "precise_tracking"


class MaskPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class MaskContour(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    points: tuple[MaskPoint, ...] = Field(min_length=3)


class MaskRle(BaseModel):
    """Compact row-major binary RLE beginning with a zero-value run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    counts: tuple[int, ...] = Field(min_length=1)


class SegmentationMask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    area_pixels: int = Field(ge=0)
    coverage: float = Field(ge=0.0, le=1.0)
    rle: MaskRle
    contours: tuple[MaskContour, ...] = ()


class SegmentationResult(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )

    status: SegmentationStatus
    answer: str
    target_label: str = ""
    track_id: int | None = None
    prompt_box: BoundingBox | None = None
    mask: SegmentationMask | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    mode: SegmentationMode = SegmentationMode.SINGLE_FRAME
    tracking: bool = False
    model: str = ""
    device: str = ""
    keyframe_sequence: int | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)
    error: str = ""
    completed_at: float = Field(
        default_factory=time.monotonic,
        exclude=True,
        repr=False,
    )

    @property
    def ok(self) -> bool:
        return self.status == SegmentationStatus.READY

    def is_fresh(self, ttl_seconds: float, *, now: float | None = None) -> bool:
        if self.completed_at <= 0 or ttl_seconds <= 0:
            return False
        current = time.monotonic() if now is None else now
        return current - self.completed_at <= ttl_seconds

    @classmethod
    def idle(cls, answer: str = "No segmentation mask is active, Boss.") -> SegmentationResult:
        return cls(status=SegmentationStatus.IDLE, answer=answer)


class SegmentationIntentAction(str, Enum):
    NONE = "none"
    SEGMENT = "segment"
    TRACK = "track"
    STOP = "stop"
    CLEAR = "clear"


class SegmentationIntentMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: SegmentationIntentAction = SegmentationIntentAction.NONE
    target: str = ""
    trigger_id: str = ""


class SegmentationCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool
    package_available: bool
    checkpoint_available: bool
    checkpoint_path: str
    sam2_model_config: str
    requested_device: str
    tracking_fps: float
    ready: bool
