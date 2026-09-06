from __future__ import annotations

import math
import os
from collections import deque
from dataclasses import dataclass

from friday.app.perception.detection import (
    BoundingBox,
    SceneSnapshot,
    TrackedObject,
    TrackingState,
)
from friday.app.perception.scene.schemas import (
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectPresenceState,
    SceneEvent,
    SceneEventType,
    TemporalObjectState,
    TemporalSceneSnapshot,
)


@dataclass(frozen=True, slots=True)
class SceneEventConfig:
    disappear_after_seconds: float = 0.75
    event_retention_seconds: float = 30.0
    object_retention_seconds: float = 60.0
    moving_enter_speed: float = 0.035
    moving_exit_speed: float = 0.015
    motion_confirmation_frames: int = 2
    depth_change_rate: float = 0.18
    depth_confirmation_frames: int = 2
    maximum_events: int = 64

    @classmethod
    def from_environment(cls) -> SceneEventConfig:
        return cls(
            disappear_after_seconds=_environment_float(
                "FRIDAY_VISION_SCENE_DISAPPEAR_SECONDS", 0.75, 0.1, 10.0
            ),
            event_retention_seconds=_environment_float(
                "FRIDAY_VISION_SCENE_EVENT_RETENTION_SECONDS", 30.0, 1.0, 600.0
            ),
            object_retention_seconds=_environment_float(
                "FRIDAY_VISION_SCENE_OBJECT_RETENTION_SECONDS", 60.0, 1.0, 3600.0
            ),
            moving_enter_speed=_environment_float(
                "FRIDAY_VISION_SCENE_MOVING_ENTER_SPEED", 0.035, 0.001, 2.0
            ),
            moving_exit_speed=_environment_float(
                "FRIDAY_VISION_SCENE_MOVING_EXIT_SPEED", 0.015, 0.0, 2.0
            ),
            motion_confirmation_frames=_environment_int(
                "FRIDAY_VISION_SCENE_MOTION_CONFIRM_FRAMES", 2, 1, 30
            ),
            depth_change_rate=_environment_float(
                "FRIDAY_VISION_SCENE_DEPTH_CHANGE_RATE", 0.18, 0.01, 5.0
            ),
            depth_confirmation_frames=_environment_int(
                "FRIDAY_VISION_SCENE_DEPTH_CONFIRM_FRAMES", 2, 1, 30
            ),
            maximum_events=_environment_int(
                "FRIDAY_VISION_SCENE_MAX_EVENTS", 64, 8, 512
            ),
        )


@dataclass(slots=True)
class _ObjectHistory:
    track_id: int
    class_id: int
    label: str
    confidence: float
    box: BoundingBox
    presence: ObjectPresenceState
    motion: ObjectMotionState
    depth_trend: ObjectDepthTrend
    position: str
    movement_direction: str
    normalized_speed: float
    first_seen_at: float
    last_seen_at: float
    visible_since: float
    unseen_since: float | None
    area_ratio: float
    motion_candidate: ObjectMotionState | None = None
    motion_candidate_frames: int = 0
    depth_candidate: ObjectDepthTrend | None = None
    depth_candidate_frames: int = 0


class SceneEventDetector:
    """Aggregate detector samples into short-term object state and events."""

    def __init__(self, config: SceneEventConfig | None = None) -> None:
        self._config = config or SceneEventConfig.from_environment()
        if self._config.moving_exit_speed > self._config.moving_enter_speed:
            raise ValueError("moving_exit_speed must not exceed moving_enter_speed")
        self._objects: dict[int, _ObjectHistory] = {}
        self._events: deque[SceneEvent] = deque(maxlen=self._config.maximum_events)
        self._last_change_at = 0.0
        self._event_sequence = 0
        self._status = "idle"

    def update(self, snapshot: SceneSnapshot) -> TemporalSceneSnapshot:
        observed_at = snapshot.captured_at
        if observed_at <= 0:
            observed_at = 0.0

        if snapshot.status != "ready":
            self.reset(status=snapshot.status, observed_at=observed_at)
            return self.snapshot(observed_at=observed_at)

        if self._status != "ready":
            self._status = "ready"
            self._last_change_at = observed_at

        if not snapshot.detector_sampled:
            self._apply_prediction(snapshot)
            return self.snapshot(observed_at=observed_at)

        visible = {
            item.track_id: item
            for item in snapshot.objects
            if item.tracking_state != TrackingState.LOST
        }
        for tracked in visible.values():
            self._observe(
                tracked,
                observed_at=observed_at,
                frame_width=snapshot.frame_width,
                frame_height=snapshot.frame_height,
            )

        for track_id in tuple(self._objects):
            if track_id not in visible:
                self._mark_missing(track_id, observed_at)

        self._prune(observed_at)
        return self.snapshot(observed_at=observed_at)

    def snapshot(self, *, observed_at: float) -> TemporalSceneSnapshot:
        self._prune_events(observed_at)
        objects = tuple(
            self._to_temporal_object(item, observed_at)
            for item in sorted(
                self._objects.values(),
                key=lambda value: (
                    value.presence == ObjectPresenceState.ABSENT,
                    value.track_id,
                ),
            )
        )
        last_change = self._last_change_at or observed_at
        return TemporalSceneSnapshot(
            observed_at=observed_at,
            status=self._status,
            objects=objects,
            recent_events=tuple(self._events),
            last_significant_change_at=last_change,
            stable_for_seconds=max(0.0, observed_at - last_change),
        )

    def reset(self, *, status: str = "idle", observed_at: float = 0.0) -> None:
        self._objects.clear()
        self._events.clear()
        self._last_change_at = observed_at
        self._event_sequence = 0
        self._status = status

    def _observe(
        self,
        tracked: TrackedObject,
        *,
        observed_at: float,
        frame_width: int,
        frame_height: int,
    ) -> None:
        position = _position_name(tracked, frame_width, frame_height)
        area_ratio = _area_ratio(tracked, frame_width, frame_height)
        normalized_speed = _normalized_speed(tracked, frame_width, frame_height)
        direction = _movement_direction(tracked)
        history = self._objects.get(tracked.track_id)
        if history is None:
            history = _ObjectHistory(
                track_id=tracked.track_id,
                class_id=tracked.class_id,
                label=tracked.label,
                confidence=tracked.confidence,
                box=tracked.box,
                presence=ObjectPresenceState.VISIBLE,
                motion=ObjectMotionState.UNKNOWN,
                depth_trend=ObjectDepthTrend.STABLE,
                position=position,
                movement_direction=direction,
                normalized_speed=normalized_speed,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                visible_since=observed_at,
                unseen_since=None,
                area_ratio=area_ratio,
            )
            self._objects[tracked.track_id] = history
            self._emit(
                SceneEventType.OBJECT_APPEARED,
                history,
                observed_at,
                f"{tracked.label} ID {tracked.track_id} appeared in {position}.",
            )
            return

        previous_presence = history.presence
        elapsed = max(1e-6, observed_at - history.last_seen_at)
        previous_area_ratio = history.area_ratio
        history.class_id = tracked.class_id
        history.label = tracked.label
        history.confidence = tracked.confidence
        history.box = tracked.box
        history.presence = ObjectPresenceState.VISIBLE
        history.position = position
        history.normalized_speed = normalized_speed
        history.movement_direction = direction
        history.unseen_since = None
        history.area_ratio = area_ratio

        if previous_presence == ObjectPresenceState.ABSENT:
            history.visible_since = observed_at
            self._emit(
                SceneEventType.OBJECT_REAPPEARED,
                history,
                observed_at,
                f"{tracked.label} ID {tracked.track_id} reappeared in {position}.",
            )

        self._update_motion(history, observed_at)
        self._update_depth(
            history,
            previous_area_ratio=previous_area_ratio,
            elapsed=elapsed,
            observed_at=observed_at,
        )
        history.last_seen_at = observed_at

    def _mark_missing(self, track_id: int, observed_at: float) -> None:
        history = self._objects[track_id]
        if history.presence == ObjectPresenceState.ABSENT:
            return
        if history.unseen_since is None:
            history.unseen_since = observed_at
        missing_for = observed_at - history.unseen_since
        if missing_for < self._config.disappear_after_seconds:
            history.presence = ObjectPresenceState.OCCLUDED
            return
        history.presence = ObjectPresenceState.ABSENT
        history.motion = ObjectMotionState.UNKNOWN
        history.depth_trend = ObjectDepthTrend.STABLE
        history.motion_candidate = None
        history.motion_candidate_frames = 0
        history.depth_candidate = None
        history.depth_candidate_frames = 0
        self._emit(
            SceneEventType.OBJECT_DISAPPEARED,
            history,
            observed_at,
            f"{history.label} ID {history.track_id} disappeared from {history.position}.",
        )

    def _update_motion(self, history: _ObjectHistory, observed_at: float) -> None:
        if history.normalized_speed >= self._config.moving_enter_speed:
            candidate = ObjectMotionState.MOVING
        elif history.normalized_speed <= self._config.moving_exit_speed:
            candidate = ObjectMotionState.STATIONARY
        else:
            candidate = history.motion

        if candidate == history.motion or candidate == ObjectMotionState.UNKNOWN:
            history.motion_candidate = None
            history.motion_candidate_frames = 0
            return
        if candidate == history.motion_candidate:
            history.motion_candidate_frames += 1
        else:
            history.motion_candidate = candidate
            history.motion_candidate_frames = 1
        if history.motion_candidate_frames < self._config.motion_confirmation_frames:
            return

        previous = history.motion
        history.motion = candidate
        history.motion_candidate = None
        history.motion_candidate_frames = 0
        if candidate == ObjectMotionState.MOVING:
            self._emit(
                SceneEventType.OBJECT_STARTED_MOVING,
                history,
                observed_at,
                f"{history.label} ID {history.track_id} started moving {history.movement_direction}.",
            )
        elif previous == ObjectMotionState.MOVING:
            self._emit(
                SceneEventType.OBJECT_STOPPED_MOVING,
                history,
                observed_at,
                f"{history.label} ID {history.track_id} stopped moving.",
            )

    def _update_depth(
        self,
        history: _ObjectHistory,
        *,
        previous_area_ratio: float,
        elapsed: float,
        observed_at: float,
    ) -> None:
        if previous_area_ratio <= 0:
            return
        relative_rate = (history.area_ratio - previous_area_ratio) / (
            previous_area_ratio * elapsed
        )
        if relative_rate >= self._config.depth_change_rate:
            candidate = ObjectDepthTrend.APPROACHING
        elif relative_rate <= -self._config.depth_change_rate:
            candidate = ObjectDepthTrend.MOVING_AWAY
        else:
            candidate = ObjectDepthTrend.STABLE

        if candidate == history.depth_trend:
            history.depth_candidate = None
            history.depth_candidate_frames = 0
            return
        if candidate == history.depth_candidate:
            history.depth_candidate_frames += 1
        else:
            history.depth_candidate = candidate
            history.depth_candidate_frames = 1
        if history.depth_candidate_frames < self._config.depth_confirmation_frames:
            return

        history.depth_trend = candidate
        history.depth_candidate = None
        history.depth_candidate_frames = 0
        if candidate == ObjectDepthTrend.APPROACHING:
            self._emit(
                SceneEventType.OBJECT_APPROACHING,
                history,
                observed_at,
                f"{history.label} ID {history.track_id} is approaching the camera.",
            )
        elif candidate == ObjectDepthTrend.MOVING_AWAY:
            self._emit(
                SceneEventType.OBJECT_MOVING_AWAY,
                history,
                observed_at,
                f"{history.label} ID {history.track_id} is moving away from the camera.",
            )

    def _apply_prediction(self, snapshot: SceneSnapshot) -> None:
        for tracked in snapshot.objects:
            history = self._objects.get(tracked.track_id)
            if history is None:
                continue
            history.box = tracked.box
            history.confidence = tracked.confidence
            history.position = _position_name(
                tracked,
                snapshot.frame_width,
                snapshot.frame_height,
            )

    def _emit(
        self,
        event_type: SceneEventType,
        history: _ObjectHistory,
        observed_at: float,
        description: str,
    ) -> None:
        self._event_sequence += 1
        self._events.append(
            SceneEvent(
                event_id=f"scene-{self._event_sequence:06d}",
                event_type=event_type,
                track_id=history.track_id,
                label=history.label,
                occurred_at=observed_at,
                description=description,
                confidence=history.confidence,
            )
        )
        self._last_change_at = observed_at

    def _prune(self, observed_at: float) -> None:
        expired = (
            track_id
            for track_id, history in self._objects.items()
            if history.presence == ObjectPresenceState.ABSENT
            and observed_at - history.last_seen_at
            > self._config.object_retention_seconds
        )
        for track_id in tuple(expired):
            del self._objects[track_id]
        self._prune_events(observed_at)

    def _prune_events(self, observed_at: float) -> None:
        while (
            self._events
            and observed_at - self._events[0].occurred_at
            > self._config.event_retention_seconds
        ):
            self._events.popleft()

    @staticmethod
    def _to_temporal_object(
        history: _ObjectHistory,
        observed_at: float,
    ) -> TemporalObjectState:
        return TemporalObjectState(
            track_id=history.track_id,
            class_id=history.class_id,
            label=history.label,
            confidence=history.confidence,
            box=history.box,
            presence=history.presence,
            motion=history.motion,
            depth_trend=history.depth_trend,
            position=history.position,
            movement_direction=history.movement_direction,
            normalized_speed=history.normalized_speed,
            first_seen_at=history.first_seen_at,
            last_seen_at=history.last_seen_at,
            visible_since=history.visible_since,
            unseen_since=history.unseen_since,
            age_seconds=max(0.0, observed_at - history.first_seen_at),
        )


def _position_name(tracked: TrackedObject, width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "unknown area"
    center_x, center_y = tracked.box.center
    horizontal = (
        "left"
        if center_x < width / 3
        else "right"
        if center_x > width * 2 / 3
        else "center"
    )
    vertical = (
        "upper"
        if center_y < height / 3
        else "lower"
        if center_y > height * 2 / 3
        else "middle"
    )
    if horizontal == "center" and vertical == "middle":
        return "the center"
    if vertical == "middle":
        return f"the {horizontal}"
    if horizontal == "center":
        return f"the {vertical} center"
    return f"the {vertical} {horizontal}"


def _area_ratio(tracked: TrackedObject, width: int, height: int) -> float:
    frame_area = width * height
    return tracked.box.area / frame_area if frame_area > 0 else 0.0


def _normalized_speed(tracked: TrackedObject, width: int, height: int) -> float:
    diagonal = math.hypot(width, height)
    if diagonal <= 0:
        return 0.0
    return math.hypot(tracked.velocity_x, tracked.velocity_y) / diagonal


def _movement_direction(tracked: TrackedObject) -> str:
    velocity_x = tracked.velocity_x
    velocity_y = tracked.velocity_y
    if abs(velocity_x) < 1e-6 and abs(velocity_y) < 1e-6:
        return "none"
    horizontal = "right" if velocity_x > 0 else "left"
    vertical = "down" if velocity_y > 0 else "up"
    if abs(velocity_x) > abs(velocity_y) * 1.5:
        return horizontal
    if abs(velocity_y) > abs(velocity_x) * 1.5:
        return vertical
    return f"{vertical}-{horizontal}"


def _environment_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.getenv(name, str(default)).strip())
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
        value = int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))
