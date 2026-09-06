from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass

from friday.app.perception.detection import SceneSnapshot
from friday.app.perception.reasoning.schemas import KeyframeReason, VisionKeyframe
from friday.app.perception.scene import TemporalSceneSnapshot


@dataclass(frozen=True, slots=True)
class KeyframePolicyConfig:
    minimum_interval_seconds: float = 1.0
    maximum_interval_seconds: float = 8.0
    low_confidence_threshold: float = 0.5
    maximum_image_edge: int = 896
    jpeg_quality: int = 82

    @classmethod
    def from_environment(cls) -> KeyframePolicyConfig:
        return cls(
            minimum_interval_seconds=_environment_float(
                "FRIDAY_VISION_KEYFRAME_MIN_SECONDS", 1.0, 0.1, 30.0
            ),
            maximum_interval_seconds=_environment_float(
                "FRIDAY_VISION_KEYFRAME_MAX_SECONDS", 8.0, 1.0, 120.0
            ),
            low_confidence_threshold=_environment_float(
                "FRIDAY_VISION_REASONING_LOW_CONFIDENCE", 0.5, 0.0, 1.0
            ),
            maximum_image_edge=_environment_int(
                "FRIDAY_VISION_KEYFRAME_MAX_EDGE", 896, 320, 1920
            ),
            jpeg_quality=_environment_int(
                "FRIDAY_VISION_KEYFRAME_JPEG_QUALITY", 82, 50, 95
            ),
        )


class KeyframePolicy:
    """Choose sparse frames for later reasoning without invoking a VLM."""

    def __init__(self, config: KeyframePolicyConfig | None = None) -> None:
        self.config = config or KeyframePolicyConfig.from_environment()

    def select_reason(
        self,
        snapshot: SceneSnapshot,
        temporal: TemporalSceneSnapshot,
        previous: VisionKeyframe | None,
        *,
        force: bool = False,
    ) -> KeyframeReason | None:
        if snapshot.status != "ready":
            return None
        if force:
            return KeyframeReason.USER_REQUEST
        if previous is None:
            return KeyframeReason.INITIAL

        elapsed = max(0.0, snapshot.captured_at - previous.captured_at)
        if elapsed < self.config.minimum_interval_seconds:
            return None

        latest_event_id = latest_scene_event_id(temporal)
        if latest_event_id and latest_event_id != previous.latest_event_id:
            return KeyframeReason.SCENE_EVENT
        if scene_signature(temporal) != previous.scene_signature:
            return KeyframeReason.COMPOSITION_CHANGE
        if any(
            item.confidence < self.config.low_confidence_threshold
            for item in temporal.visible_objects
        ):
            return KeyframeReason.LOW_CONFIDENCE
        if elapsed >= self.config.maximum_interval_seconds:
            return KeyframeReason.PERIODIC
        return None


def scene_signature(
    temporal: TemporalSceneSnapshot,
) -> tuple[tuple[str, int], ...]:
    counts = Counter(item.label.lower() for item in temporal.visible_objects)
    return tuple(sorted(counts.items()))


def latest_scene_event_id(temporal: TemporalSceneSnapshot) -> str:
    return temporal.recent_events[-1].event_id if temporal.recent_events else ""


def _environment_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _environment_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))
