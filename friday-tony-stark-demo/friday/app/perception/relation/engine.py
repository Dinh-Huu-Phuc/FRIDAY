from __future__ import annotations

import math
import os
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from friday.app.perception.scene.schemas import (
    HandObservation,
    ObjectMotionState,
    ObjectPresenceState,
    ObjectRelation,
    ObjectRelationType,
    SceneEvent,
    SceneEventType,
    TemporalObjectState,
    TemporalSceneSnapshot,
)


@dataclass(frozen=True, slots=True)
class RelationEngineConfig:
    hold_confirmation_frames: int = 2
    release_confirmation_frames: int = 2
    point_confirmation_frames: int = 2
    grip_target_radius: float = 0.12
    point_tolerance: float = 0.07
    event_retention_seconds: float = 30.0
    maximum_events: int = 64

    @classmethod
    def from_environment(cls) -> RelationEngineConfig:
        return cls(
            hold_confirmation_frames=_environment_int(
                "FRIDAY_VISION_RELATION_HOLD_FRAMES", 2, 1, 30
            ),
            release_confirmation_frames=_environment_int(
                "FRIDAY_VISION_RELATION_RELEASE_FRAMES", 2, 1, 30
            ),
            point_confirmation_frames=_environment_int(
                "FRIDAY_VISION_RELATION_POINT_FRAMES", 2, 1, 30
            ),
            grip_target_radius=_environment_float(
                "FRIDAY_VISION_RELATION_GRIP_RADIUS", 0.12, 0.01, 0.5
            ),
            point_tolerance=_environment_float(
                "FRIDAY_VISION_RELATION_POINT_TOLERANCE", 0.07, 0.01, 0.5
            ),
            event_retention_seconds=_environment_float(
                "FRIDAY_VISION_RELATION_EVENT_RETENTION_SECONDS",
                30.0,
                1.0,
                600.0,
            ),
            maximum_events=_environment_int(
                "FRIDAY_VISION_RELATION_MAX_EVENTS", 64, 8, 512
            ),
        )


@dataclass(slots=True)
class _Candidate:
    track_id: int
    frames: int
    confidence: float


@dataclass(slots=True)
class _ActiveRelation:
    track_id: int
    label: str
    hand_id: str
    handedness: str
    confidence: float
    since: float
    origin_x: float
    origin_y: float
    release_frames: int = 0


class SceneRelationEngine:
    """Infer stable hand-object and scene-count relations from temporal state."""

    def __init__(self, config: RelationEngineConfig | None = None) -> None:
        self._config = config or RelationEngineConfig.from_environment()
        self._hold_candidates: dict[str, _Candidate] = {}
        self._point_candidates: dict[str, _Candidate] = {}
        self._held: dict[str, _ActiveRelation] = {}
        self._pointing: dict[str, _ActiveRelation] = {}
        self._events: deque[SceneEvent] = deque(maxlen=self._config.maximum_events)
        self._people_count: int | None = None
        self._event_sequence = 0
        self._last_change_at = 0.0

    def update(
        self,
        scene: TemporalSceneSnapshot,
        *,
        hand_observations: tuple[HandObservation, ...] | None,
        frame_width: int,
        frame_height: int,
    ) -> tuple[tuple[ObjectRelation, ...], tuple[SceneEvent, ...]]:
        observed_at = scene.observed_at
        self._update_people_count(scene, observed_at)
        if hand_observations is not None:
            self._update_hands(
                scene,
                hand_observations,
                observed_at=observed_at,
                frame_width=frame_width,
                frame_height=frame_height,
            )
        self._prune_events(observed_at)
        return self.relations(), tuple(self._events)

    def snapshot(
        self,
        *,
        observed_at: float,
    ) -> tuple[tuple[ObjectRelation, ...], tuple[SceneEvent, ...]]:
        self._prune_events(observed_at)
        return self.relations(), tuple(self._events)

    def relations(self) -> tuple[ObjectRelation, ...]:
        relations = [
            self._to_relation(item, ObjectRelationType.HELD_BY_HAND)
            for item in self._held.values()
        ]
        relations.extend(
            self._to_relation(item, ObjectRelationType.POINTED_AT_BY_HAND)
            for item in self._pointing.values()
        )
        return tuple(
            sorted(
                relations,
                key=lambda item: (item.relation_type.value, item.hand_id),
            )
        )

    def reset(self) -> None:
        self._hold_candidates.clear()
        self._point_candidates.clear()
        self._held.clear()
        self._pointing.clear()
        self._events.clear()
        self._people_count = None
        self._event_sequence = 0
        self._last_change_at = 0.0

    @property
    def last_change_at(self) -> float:
        return self._last_change_at

    def _update_people_count(
        self,
        scene: TemporalSceneSnapshot,
        observed_at: float,
    ) -> None:
        count = sum(
            1
            for item in scene.visible_objects
            if item.label.lower() == "person"
        )
        if self._people_count is None:
            self._people_count = count
            return
        if count == self._people_count:
            return
        previous = self._people_count
        self._people_count = count
        description = f"People count changed from {previous} to {count}."
        self._emit(
            SceneEventType.PEOPLE_COUNT_CHANGED,
            track_id=0,
            label="person",
            confidence=1.0,
            observed_at=observed_at,
            description=description,
        )

    def _update_hands(
        self,
        scene: TemporalSceneSnapshot,
        hands: tuple[HandObservation, ...],
        *,
        observed_at: float,
        frame_width: int,
        frame_height: int,
    ) -> None:
        objects = {
            item.track_id: item
            for item in scene.objects
            if item.label.lower() != "person"
        }
        observed_hand_ids = {hand.hand_id for hand in hands}
        for hand in hands:
            self._update_pointing(
                hand,
                objects,
                observed_at=observed_at,
                frame_width=frame_width,
                frame_height=frame_height,
            )
            self._update_holding(
                hand,
                objects,
                observed_at=observed_at,
                frame_width=frame_width,
                frame_height=frame_height,
            )

        for hand_id in set(self._point_candidates) - observed_hand_ids:
            del self._point_candidates[hand_id]
        for hand_id in set(self._pointing) - observed_hand_ids:
            del self._pointing[hand_id]
        for hand_id in set(self._hold_candidates) - observed_hand_ids:
            del self._hold_candidates[hand_id]
        for hand_id in set(self._held) - observed_hand_ids:
            self._advance_release(hand_id, objects, observed_at)

    def _update_pointing(
        self,
        hand: HandObservation,
        objects: dict[int, TemporalObjectState],
        *,
        observed_at: float,
        frame_width: int,
        frame_height: int,
    ) -> None:
        if not hand.is_pointing:
            self._point_candidates.pop(hand.hand_id, None)
            self._pointing.pop(hand.hand_id, None)
            return
        target, confidence = self._pointed_target(
            hand,
            objects.values(),
            frame_width,
            frame_height,
        )
        if target is None:
            self._point_candidates.pop(hand.hand_id, None)
            self._pointing.pop(hand.hand_id, None)
            return
        candidate = self._advance_candidate(
            self._point_candidates,
            hand.hand_id,
            target.track_id,
            confidence,
        )
        if candidate.frames < self._config.point_confirmation_frames:
            return
        active = self._pointing.get(hand.hand_id)
        if active is None or active.track_id != target.track_id:
            active = self._active_relation(
                hand,
                target,
                confidence,
                observed_at,
                origin=(hand.index_tip_x, hand.index_tip_y),
            )
            self._pointing[hand.hand_id] = active
            self._emit(
                SceneEventType.OBJECT_POINTED_AT,
                track_id=target.track_id,
                label=target.label,
                confidence=confidence,
                observed_at=observed_at,
                description=(
                    f"The {hand.handedness} hand pointed at "
                    f"{target.label} ID {target.track_id}."
                ),
            )
        else:
            self._refresh_active(
                active,
                hand,
                confidence,
                origin=(hand.index_tip_x, hand.index_tip_y),
            )

    def _update_holding(
        self,
        hand: HandObservation,
        objects: dict[int, TemporalObjectState],
        *,
        observed_at: float,
        frame_width: int,
        frame_height: int,
    ) -> None:
        active = self._held.get(hand.hand_id)
        if active is not None:
            if hand.is_gripping:
                active.release_frames = 0
                self._refresh_active(
                    active,
                    hand,
                    active.confidence,
                    origin=(hand.interaction_x, hand.interaction_y),
                )
            else:
                self._advance_release(hand.hand_id, objects, observed_at)
            return

        if not hand.is_gripping:
            self._hold_candidates.pop(hand.hand_id, None)
            return
        target, confidence = self._grip_target(
            hand,
            objects.values(),
            frame_width,
            frame_height,
        )
        if target is None:
            self._hold_candidates.pop(hand.hand_id, None)
            return
        candidate = self._advance_candidate(
            self._hold_candidates,
            hand.hand_id,
            target.track_id,
            confidence,
        )
        if candidate.frames < self._config.hold_confirmation_frames:
            return
        self._held[hand.hand_id] = self._active_relation(
            hand,
            target,
            confidence,
            observed_at,
            origin=(hand.interaction_x, hand.interaction_y),
        )
        self._hold_candidates.pop(hand.hand_id, None)
        self._emit(
            SceneEventType.OBJECT_HELD,
            track_id=target.track_id,
            label=target.label,
            confidence=confidence,
            observed_at=observed_at,
            description=(
                f"The {hand.handedness} hand is holding "
                f"{target.label} ID {target.track_id}."
            ),
        )

    def _advance_release(
        self,
        hand_id: str,
        objects: dict[int, TemporalObjectState],
        observed_at: float,
    ) -> None:
        active = self._held.get(hand_id)
        if active is None:
            return
        active.release_frames += 1
        if active.release_frames < self._config.release_confirmation_frames:
            return
        target = objects.get(active.track_id)
        del self._held[hand_id]
        if (
            target is None
            or target.presence != ObjectPresenceState.VISIBLE
            or target.motion == ObjectMotionState.MOVING
        ):
            return
        self._emit(
            SceneEventType.OBJECT_PLACED_DOWN,
            track_id=target.track_id,
            label=target.label,
            confidence=min(active.confidence, target.confidence),
            observed_at=observed_at,
            description=(
                f"{target.label} ID {target.track_id} was placed down "
                f"in {target.position}."
            ),
        )

    def _pointed_target(
        self,
        hand: HandObservation,
        objects: Iterable[TemporalObjectState],
        frame_width: int,
        frame_height: int,
    ) -> tuple[TemporalObjectState | None, float]:
        candidates: list[tuple[float, TemporalObjectState, float]] = []
        ray_x = hand.index_tip_x - hand.index_base_x
        ray_y = hand.index_tip_y - hand.index_base_y
        ray_length = math.hypot(ray_x, ray_y)
        if ray_length < 0.02:
            return None, 0.0
        unit_x = ray_x / ray_length
        unit_y = ray_y / ray_length
        for target in objects:
            if target.presence != ObjectPresenceState.VISIBLE:
                continue
            bounds = _normalized_bounds(target, frame_width, frame_height)
            center_x = (bounds[0] + bounds[2]) / 2
            center_y = (bounds[1] + bounds[3]) / 2
            offset_x = center_x - hand.index_base_x
            offset_y = center_y - hand.index_base_y
            projection = offset_x * unit_x + offset_y * unit_y
            if projection < ray_length * 0.65 or projection > 1.25:
                continue
            perpendicular = abs(offset_x * unit_y - offset_y * unit_x)
            target_radius = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / 2
            allowance = target_radius + self._config.point_tolerance
            if perpendicular > allowance:
                continue
            score = perpendicular / max(allowance, 1e-6) + projection * 0.08
            confidence = _combined_confidence(
                hand.confidence,
                target.confidence,
                1.0 - perpendicular / max(allowance, 1e-6),
            )
            candidates.append((score, target, confidence))
        if not candidates:
            return None, 0.0
        _, target, confidence = min(candidates, key=lambda item: item[0])
        return target, confidence

    def _grip_target(
        self,
        hand: HandObservation,
        objects: Iterable[TemporalObjectState],
        frame_width: int,
        frame_height: int,
    ) -> tuple[TemporalObjectState | None, float]:
        candidates: list[tuple[float, TemporalObjectState, float]] = []
        for target in objects:
            if target.presence != ObjectPresenceState.VISIBLE:
                continue
            bounds = _normalized_bounds(target, frame_width, frame_height)
            distance = _point_to_rectangle_distance(
                hand.interaction_x,
                hand.interaction_y,
                bounds,
            )
            if distance > self._config.grip_target_radius:
                continue
            proximity = 1.0 - distance / self._config.grip_target_radius
            confidence = _combined_confidence(
                hand.confidence,
                target.confidence,
                proximity,
            )
            candidates.append((distance, target, confidence))
        if not candidates:
            return None, 0.0
        _, target, confidence = min(candidates, key=lambda item: item[0])
        return target, confidence

    @staticmethod
    def _advance_candidate(
        candidates: dict[str, _Candidate],
        hand_id: str,
        track_id: int,
        confidence: float,
    ) -> _Candidate:
        candidate = candidates.get(hand_id)
        if candidate is None or candidate.track_id != track_id:
            candidate = _Candidate(track_id=track_id, frames=1, confidence=confidence)
            candidates[hand_id] = candidate
            return candidate
        candidate.frames += 1
        candidate.confidence = candidate.confidence * 0.4 + confidence * 0.6
        return candidate

    @staticmethod
    def _active_relation(
        hand: HandObservation,
        target: TemporalObjectState,
        confidence: float,
        observed_at: float,
        *,
        origin: tuple[float, float],
    ) -> _ActiveRelation:
        return _ActiveRelation(
            track_id=target.track_id,
            label=target.label,
            hand_id=hand.hand_id,
            handedness=hand.handedness,
            confidence=confidence,
            since=observed_at,
            origin_x=origin[0],
            origin_y=origin[1],
        )

    @staticmethod
    def _refresh_active(
        active: _ActiveRelation,
        hand: HandObservation,
        confidence: float,
        *,
        origin: tuple[float, float],
    ) -> None:
        active.confidence = active.confidence * 0.6 + confidence * 0.4
        active.handedness = hand.handedness
        active.origin_x = origin[0]
        active.origin_y = origin[1]

    def _emit(
        self,
        event_type: SceneEventType,
        *,
        track_id: int,
        label: str,
        confidence: float,
        observed_at: float,
        description: str,
    ) -> None:
        self._event_sequence += 1
        self._events.append(
            SceneEvent(
                event_id=f"relation-{self._event_sequence:06d}",
                event_type=event_type,
                track_id=track_id,
                label=label,
                occurred_at=observed_at,
                description=description,
                confidence=confidence,
            )
        )
        self._last_change_at = observed_at

    def _prune_events(self, observed_at: float) -> None:
        while (
            self._events
            and observed_at - self._events[0].occurred_at
            > self._config.event_retention_seconds
        ):
            self._events.popleft()

    @staticmethod
    def _to_relation(
        active: _ActiveRelation,
        relation_type: ObjectRelationType,
    ) -> ObjectRelation:
        return ObjectRelation(
            relation_type=relation_type,
            track_id=active.track_id,
            label=active.label,
            hand_id=active.hand_id,
            handedness=active.handedness,
            confidence=active.confidence,
            since=active.since,
            origin_x=active.origin_x,
            origin_y=active.origin_y,
        )


def _normalized_bounds(
    target: TemporalObjectState,
    frame_width: int,
    frame_height: int,
) -> tuple[float, float, float, float]:
    if frame_width <= 0 or frame_height <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        target.box.x1 / frame_width,
        target.box.y1 / frame_height,
        target.box.x2 / frame_width,
        target.box.y2 / frame_height,
    )


def _point_to_rectangle_distance(
    x: float,
    y: float,
    bounds: tuple[float, float, float, float],
) -> float:
    x1, y1, x2, y2 = bounds
    nearest_x = min(max(x, x1), x2)
    nearest_y = min(max(y, y1), y2)
    return math.hypot(x - nearest_x, y - nearest_y)


def _combined_confidence(
    hand_confidence: float,
    object_confidence: float,
    geometry_confidence: float,
) -> float:
    value = hand_confidence * 0.35 + object_confidence * 0.35 + geometry_confidence * 0.3
    return min(1.0, max(0.0, value))


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
