from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import replace
from threading import RLock

from friday.app.perception.detection import SceneSnapshot
from friday.app.perception.scene.schemas import (
    ObjectRelationType,
    SceneEvent,
    SceneEventType,
    TemporalSceneSnapshot,
)
from friday.app.perception.world.entity_registry import EntityRegistry
from friday.app.perception.world.event_journal import WorldEventJournal
from friday.app.perception.world.schemas import (
    WorldEvent,
    WorldEventType,
    WorldModelConfig,
    WorldPresence,
    WorldRelation,
    WorldSnapshot,
)
from friday.app.perception.world.world_state import WorldState, summarize_world

_MOTION_EVENTS = {
    SceneEventType.OBJECT_STARTED_MOVING: (
        WorldEventType.ENTITY_STARTED_MOVING,
        "started moving",
    ),
    SceneEventType.OBJECT_STOPPED_MOVING: (
        WorldEventType.ENTITY_STOPPED_MOVING,
        "stopped moving",
    ),
    SceneEventType.OBJECT_APPROACHING: (
        WorldEventType.ENTITY_APPROACHED,
        "approached the camera",
    ),
    SceneEventType.OBJECT_MOVING_AWAY: (
        WorldEventType.ENTITY_MOVED_AWAY,
        "moved away from the camera",
    ),
}
_PRESENCE_TEXT = {
    WorldEventType.ENTITY_APPEARED: "appeared",
    WorldEventType.ENTITY_REAPPEARED: "reappeared",
    WorldEventType.ENTITY_DISAPPEARED: "is no longer visible; last seen",
}


class WorldModel:
    """Session-persistent visual knowledge, independent of short-term trackers.

    Only real detector samples advance evidence. A camera interruption clears
    runtime aliases/relations and marks visibility unknown, but retains entities
    and the bounded journal. Restarting this object/process or reset() forgets
    everything. All shared state is protected by one lock; no frames, inference,
    network, or disk work is performed here.
    """

    def __init__(
        self,
        config: WorldModelConfig | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._config = config or WorldModelConfig.from_environment()
        self._clock = clock
        self._lock = RLock()
        self._registry = EntityRegistry(self._config)
        self._journal = WorldEventJournal(self._config)
        self._state = WorldState()
        self._last_sample_at = float("-inf")
        self._event_watermark = float("-inf")

    def update(self, snapshot: SceneSnapshot, temporal: TemporalSceneSnapshot) -> None:
        now = snapshot.captured_at
        if not math.isfinite(now):
            return
        with self._lock:
            if snapshot.status != "ready":
                self.interrupt(status=snapshot.status, observed_at=now)
                return
            if (
                not snapshot.detector_sampled
                or temporal.status != "ready"
                or temporal.observed_at != now
                or now <= self._last_sample_at
                or now < self._state.last_updated_at
            ):
                return
            changes = self._registry.update(
                temporal, snapshot.frame_width, snapshot.frame_height
            )
            for entity_id, event_type in changes:
                entity = self._registry.records[entity_id].entity
                self._journal.append(
                    event_type,
                    entity_id=entity_id,
                    occurred_at=now,
                    description=f"{entity_id} {_PRESENCE_TEXT[event_type]} at {entity.last_known_position}.",
                    confidence=entity.confidence,
                )
            # Upstream journals replay a sliding window and reset their IDs after
            # restart. A sample-time watermark deduplicates even after eviction.
            fresh_events = tuple(
                event
                for event in temporal.recent_events
                if self._event_watermark < event.occurred_at <= now
            )
            self._update_relations(temporal, fresh_events)
            for event in fresh_events:
                mapping = _MOTION_EVENTS.get(event.event_type)
                entity_id = self._registry.resolve_track(event.track_id)
                if mapping is None or entity_id is None:
                    continue
                entity = self._registry.records[entity_id].entity
                if (
                    entity.active_track_id != event.track_id
                    or entity.presence != WorldPresence.VISIBLE
                ):
                    continue
                event_type, verb = mapping
                self._journal.append(
                    event_type,
                    entity_id=entity_id,
                    occurred_at=now,
                    description=f"{entity_id} {verb} at {entity.last_known_position}.",
                    confidence=event.confidence,
                    source_event_id=event.event_id,
                )
            self._last_sample_at = now
            self._event_watermark = max(self._event_watermark, now)
            self._state.last_updated_at = now
            self._state.camera_status = "ready"
            self._journal.prune(now)

    def _update_relations(
        self, temporal: TemporalSceneSnapshot, fresh_events: tuple[SceneEvent, ...]
    ) -> None:
        previous = self._state.relations
        current: dict[tuple[str, str, str], WorldRelation] = {}
        for relation in temporal.relations[: self._config.maximum_entities * 2]:
            entity_id = self._registry.resolve_track(relation.track_id)
            if entity_id is None:
                continue
            entity = self._registry.records[entity_id].entity
            if entity.presence not in (WorldPresence.VISIBLE, WorldPresence.OCCLUDED):
                continue
            kind = relation.relation_type.value
            hand = relation.hand_id[:80]
            key = (entity_id, kind, hand)
            old = previous.get(key)
            current[key] = WorldRelation(
                relation_type=kind,
                subject_entity_id=entity_id,
                hand_reference=hand,
                confidence=relation.confidence,
                since=old.since if old else relation.since,
                last_updated_at=temporal.observed_at,
            )
        for key, relation in current.items():
            if key in previous:
                continue
            entity_id, kind, hand = key
            record = self._registry.records[entity_id]
            episode = (hand, relation.since)
            if record.relation_episodes.get(kind) == episode:
                continue
            record.relation_episodes[kind] = episode
            held = kind == ObjectRelationType.HELD_BY_HAND.value
            event_type = (
                WorldEventType.OBJECT_PICKED_UP
                if held
                else WorldEventType.OBJECT_POINTED_AT
            )
            source_type = (
                SceneEventType.OBJECT_HELD if held else SceneEventType.OBJECT_POINTED_AT
            )
            verb = "was picked up by" if held else "was pointed at by"
            self._record_relation_event(
                entity_id,
                event_type,
                f"{entity_id} {verb} hand {hand}.",
                relation.confidence,
                temporal.observed_at,
                self._source_id(fresh_events, entity_id, source_type),
            )

        # The relation engine may still reference the old tracker after a hand
        # occludes an object. Its confirmed release applies to the resolved
        # entity, using the reacquired position rather than the stale old box.
        placed: set[str] = set()
        held_entities = {
            eid
            for eid, kind, _ in current
            if kind == ObjectRelationType.HELD_BY_HAND.value
        }
        for key, relation in previous.items():
            entity_id, kind, _ = key
            record = self._registry.records.get(entity_id)
            if (
                kind != ObjectRelationType.HELD_BY_HAND.value
                or entity_id in held_entities
                or entity_id in placed
                or record is None
                or record.entity.presence != WorldPresence.VISIBLE
                or record.entity.attributes.get("motion") != "stationary"
            ):
                continue
            self._place(
                entity_id,
                temporal.observed_at,
                relation.confidence,
                self._source_id(
                    fresh_events, entity_id, SceneEventType.OBJECT_PLACED_DOWN
                ),
            )
            placed.add(entity_id)
        for event in fresh_events:
            if event.event_type != SceneEventType.OBJECT_PLACED_DOWN:
                continue
            entity_id = self._registry.resolve_track(event.track_id)
            if entity_id is None or entity_id in placed or entity_id in held_entities:
                continue
            if (
                self._registry.records[entity_id].entity.presence
                == WorldPresence.VISIBLE
            ):
                self._place(
                    entity_id, temporal.observed_at, event.confidence, event.event_id
                )
                placed.add(entity_id)
        self._state.relations = current

    def _source_id(
        self, events: tuple[SceneEvent, ...], entity_id: str, event_type: SceneEventType
    ) -> str | None:
        return next(
            (
                event.event_id
                for event in events
                if event.event_type == event_type
                and self._registry.resolve_track(event.track_id) == entity_id
            ),
            None,
        )

    def _place(
        self, entity_id: str, now: float, confidence: float, source_id: str | None
    ) -> None:
        record = self._registry.records[entity_id]
        position = record.entity.last_known_position
        record.relation_episodes.pop(ObjectRelationType.HELD_BY_HAND.value, None)
        record.entity = replace(
            record.entity,
            attributes={
                **record.entity.attributes,
                "last_placed_at": now,
                "last_placed_position": position,
            },
        )
        self._record_relation_event(
            entity_id,
            WorldEventType.OBJECT_PLACED_DOWN,
            f"{entity_id} was placed down at {position}.",
            min(confidence, record.entity.confidence),
            now,
            source_id,
        )

    def _record_relation_event(
        self,
        entity_id: str,
        event_type: WorldEventType,
        description: str,
        confidence: float,
        now: float,
        source_id: str | None,
    ) -> None:
        record = self._registry.records[entity_id]
        record.entity = replace(record.entity, last_relation_summary=description[:240])
        self._journal.append(
            event_type,
            entity_id=entity_id,
            occurred_at=now,
            description=description,
            confidence=confidence,
            source_event_id=source_id,
        )

    def interrupt(
        self, *, status: str = "idle", observed_at: float | None = None
    ) -> None:
        """End a tracking epoch without forgetting knowledge or inferring absence."""
        with self._lock:
            now = self._clock() if observed_at is None else observed_at
            if now < self._state.last_updated_at:
                return
            self._registry.interrupt()
            self._state.relations.clear()
            self._state.camera_status = status
            self._state.last_updated_at = now
            # A fresh tracking epoch may publish within the same clock tick as
            # the last epoch. The lifecycle timestamp still rejects stale data.
            self._last_sample_at = float("-inf")
            self._event_watermark = max(self._event_watermark, now)

    def reset(self) -> None:
        """Erase knowledge and ignore any pre-reset upstream event window."""
        with self._lock:
            self._registry.reset()
            self._journal.reset()
            self._state = WorldState()
            self._last_sample_at = float("-inf")
            self._event_watermark = self._clock()

    def snapshot(self) -> WorldSnapshot:
        with self._lock:
            return WorldSnapshot(
                entities=tuple(
                    replace(record.entity, attributes=dict(record.entity.attributes))
                    for record in self._registry.records.values()
                ),
                relations=tuple(self._state.relations.values()),
                recent_events=self._journal.recent(now=self._now()),
                last_updated_at=self._state.last_updated_at,
                camera_status=self._state.camera_status,
            )

    def recent_events(self, *, limit: int = 20) -> tuple[WorldEvent, ...]:
        with self._lock:
            return self._journal.recent(now=self._now(), limit=limit)

    def describe(self, *, question: str = "", max_chars: int = 2400) -> str:
        with self._lock:
            snapshot = self.snapshot()
            now = self._now()
        return summarize_world(
            snapshot, now=now, question=question, max_chars=max_chars
        )

    def _now(self) -> float:
        return max(self._clock(), self._state.last_updated_at)
