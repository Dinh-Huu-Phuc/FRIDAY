from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass, field
from enum import Enum


class WorldPresence(str, Enum):
    VISIBLE = "visible"
    OCCLUDED = "occluded"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class WorldEventType(str, Enum):
    ENTITY_APPEARED = "entity_appeared"
    ENTITY_DISAPPEARED = "entity_disappeared"
    ENTITY_REAPPEARED = "entity_reappeared"
    ENTITY_STARTED_MOVING = "entity_started_moving"
    ENTITY_STOPPED_MOVING = "entity_stopped_moving"
    ENTITY_APPROACHED = "entity_approached"
    ENTITY_MOVED_AWAY = "entity_moved_away"
    OBJECT_PICKED_UP = "object_picked_up"
    OBJECT_PLACED_DOWN = "object_placed_down"
    OBJECT_POINTED_AT = "object_pointed_at"


@dataclass(frozen=True, slots=True)
class WorldEntity:
    entity_id: str
    label: str
    class_id: int | None
    active_track_id: int | None
    first_seen_at: float
    last_seen_at: float
    last_known_position: str
    presence: WorldPresence
    confidence: float
    attributes: dict[str, str | float] = field(default_factory=dict)
    last_relation_summary: str | None = None


@dataclass(frozen=True, slots=True)
class WorldRelation:
    relation_type: str
    subject_entity_id: str
    confidence: float
    since: float
    last_updated_at: float
    object_entity_id: str | None = None
    hand_reference: str | None = None


@dataclass(frozen=True, slots=True)
class WorldEvent:
    event_id: str
    event_type: WorldEventType
    occurred_at: float
    entity_id: str
    description: str
    confidence: float
    related_entity_id: str | None = None
    source_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class WorldSnapshot:
    entities: tuple[WorldEntity, ...] = ()
    relations: tuple[WorldRelation, ...] = ()
    recent_events: tuple[WorldEvent, ...] = ()
    last_updated_at: float = 0.0
    camera_status: str = "idle"

    def to_dict(self) -> dict:
        """Return detached JSON-compatible data (enums are string enums)."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WorldModelConfig:
    entity_match_timeout: float = 8.0
    spatial_match_threshold: float = 0.12
    size_similarity_threshold: float = 0.65
    minimum_match_confidence: float = 0.6
    ambiguity_margin: float = 0.15
    event_retention_seconds: float = 1800.0
    maximum_entities: int = 128
    maximum_events: int = 256

    def __post_init__(self) -> None:
        for name in ("entity_match_timeout", "event_retention_seconds"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in (
            "spatial_match_threshold",
            "size_similarity_threshold",
            "minimum_match_confidence",
            "ambiguity_margin",
        ):
            if not 0 < getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        for name in ("maximum_entities", "maximum_events"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")

    @classmethod
    def from_environment(cls) -> WorldModelConfig:
        defaults = cls()
        values = {}
        for name, lower, upper in (
            ("entity_match_timeout", 0.1, 120.0),
            ("spatial_match_threshold", 0.01, 0.5),
            ("size_similarity_threshold", 0.1, 1.0),
            ("minimum_match_confidence", 0.1, 1.0),
            ("ambiguity_margin", 0.01, 1.0),
            ("event_retention_seconds", 1.0, 86400.0),
            ("maximum_entities", 1, 512),
            ("maximum_events", 1, 2048),
        ):
            default = getattr(defaults, name)
            raw = os.getenv(f"FRIDAY_VISION_WORLD_{name.upper()}", "")
            try:
                value = type(default)(raw)
                if not math.isfinite(value):
                    value = default
            except ValueError:
                value = default
            values[name] = min(upper, max(lower, value))
        return cls(**values)
