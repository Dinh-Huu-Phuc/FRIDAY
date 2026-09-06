from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time

from friday.app.perception.detection import BoundingBox


class ObjectPresenceState(str, Enum):
    VISIBLE = "visible"
    OCCLUDED = "occluded"
    ABSENT = "absent"


class ObjectMotionState(str, Enum):
    UNKNOWN = "unknown"
    STATIONARY = "stationary"
    MOVING = "moving"


class ObjectDepthTrend(str, Enum):
    STABLE = "stable"
    APPROACHING = "approaching"
    MOVING_AWAY = "moving_away"


class SceneEventType(str, Enum):
    OBJECT_APPEARED = "object_appeared"
    OBJECT_REAPPEARED = "object_reappeared"
    OBJECT_DISAPPEARED = "object_disappeared"
    OBJECT_STARTED_MOVING = "object_started_moving"
    OBJECT_STOPPED_MOVING = "object_stopped_moving"
    OBJECT_APPROACHING = "object_approaching"
    OBJECT_MOVING_AWAY = "object_moving_away"
    PEOPLE_COUNT_CHANGED = "people_count_changed"
    OBJECT_HELD = "object_held"
    OBJECT_PLACED_DOWN = "object_placed_down"
    OBJECT_POINTED_AT = "object_pointed_at"


class ObjectRelationType(str, Enum):
    HELD_BY_HAND = "held_by_hand"
    POINTED_AT_BY_HAND = "pointed_at_by_hand"


@dataclass(frozen=True, slots=True)
class HandObservation:
    hand_id: str
    handedness: str
    confidence: float
    gesture: str
    is_pointing: bool
    is_gripping: bool
    palm_x: float
    palm_y: float
    interaction_x: float
    interaction_y: float
    index_base_x: float
    index_base_y: float
    index_tip_x: float
    index_tip_y: float


@dataclass(frozen=True, slots=True)
class ObjectRelation:
    relation_type: ObjectRelationType
    track_id: int
    label: str
    hand_id: str
    handedness: str
    confidence: float
    since: float
    origin_x: float
    origin_y: float


@dataclass(frozen=True, slots=True)
class TemporalObjectState:
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
    age_seconds: float

    @property
    def is_present(self) -> bool:
        return self.presence != ObjectPresenceState.ABSENT


@dataclass(frozen=True, slots=True)
class SceneEvent:
    event_id: str
    event_type: SceneEventType
    track_id: int
    label: str
    occurred_at: float
    description: str
    confidence: float


@dataclass(frozen=True, slots=True)
class TemporalSceneSnapshot:
    observed_at: float
    status: str = "idle"
    objects: tuple[TemporalObjectState, ...] = ()
    relations: tuple[ObjectRelation, ...] = ()
    recent_events: tuple[SceneEvent, ...] = ()
    last_significant_change_at: float = 0.0
    stable_for_seconds: float = 0.0

    @property
    def visible_objects(self) -> tuple[TemporalObjectState, ...]:
        return tuple(
            item
            for item in self.objects
            if item.presence == ObjectPresenceState.VISIBLE
        )

    @property
    def present_objects(self) -> tuple[TemporalObjectState, ...]:
        return tuple(item for item in self.objects if item.is_present)

    @classmethod
    def empty(
        cls,
        *,
        status: str = "idle",
        observed_at: float | None = None,
    ) -> TemporalSceneSnapshot:
        timestamp = time() if observed_at is None else observed_at
        return cls(
            observed_at=timestamp,
            status=status,
            last_significant_change_at=timestamp,
        )
