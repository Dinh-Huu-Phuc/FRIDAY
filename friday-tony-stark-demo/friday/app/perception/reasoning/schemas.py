from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from friday.app.perception.reasoning.telemetry import OllamaTimings, VisionLatency


class KeyframeReason(str, Enum):
    INITIAL = "initial"
    USER_REQUEST = "user_request"
    SCENE_EVENT = "scene_event"
    COMPOSITION_CHANGE = "composition_change"
    LOW_CONFIDENCE = "low_confidence"
    PERIODIC = "periodic"


class VisionReasoningStatus(str, Enum):
    READY = "ready"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class VisionKeyframe:
    sequence: int
    captured_at: float
    frame_width: int
    frame_height: int
    reason: KeyframeReason
    scene_summary: str
    scene_signature: tuple[tuple[str, int], ...]
    latest_event_id: str = ""
    jpeg_bytes: bytes = field(default=b"", repr=False)
    world_summary: str = ""

    @property
    def byte_size(self) -> int:
        return len(self.jpeg_bytes)


@dataclass(frozen=True, slots=True)
class GemmaVisionOutput:
    answer: str
    observations: tuple[str, ...] = ()
    confidence: float = 0.5
    uncertainty: str = ""
    timings: OllamaTimings = field(default_factory=OllamaTimings)


@dataclass(frozen=True, slots=True)
class VisionReasoningResult:
    status: VisionReasoningStatus
    answer: str
    model: str = ""
    keyframe_sequence: int | None = None
    keyframe_reason: KeyframeReason | None = None
    latency_ms: float | None = None
    confidence: float | None = None
    observations: tuple[str, ...] = ()
    uncertainty: str = ""
    used_cache: bool = False
    error: str = ""
    timings: VisionLatency | None = None

    @property
    def ok(self) -> bool:
        return self.status in {
            VisionReasoningStatus.READY,
            VisionReasoningStatus.FALLBACK,
        }
