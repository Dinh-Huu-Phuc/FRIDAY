from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from uuid import uuid4

from friday.app.perception.scene.schemas import (
    ObjectPresenceState,
    TemporalObjectState,
    TemporalSceneSnapshot,
)
from friday.app.perception.world.schemas import (
    WorldEntity,
    WorldEventType,
    WorldModelConfig,
    WorldPresence,
)


@dataclass(slots=True)
class _Record:
    entity: WorldEntity
    geometry: tuple[float, float, float, float]
    relation_episodes: dict[str, tuple[str, float]] = field(default_factory=dict)


class EntityRegistry:
    """Bounded session identities; the owning WorldModel serializes all access.

    Track aliases are runtime hints, scoped by first_seen_at and cleared whenever
    tracking restarts. Neither the alias nor its integer ID is semantic identity.
    """

    def __init__(self, config: WorldModelConfig) -> None:
        self.config = config
        self.records: dict[str, _Record] = {}
        self._aliases: dict[int, tuple[str, float]] = {}

    def resolve_track(self, track_id: int) -> str | None:
        binding = self._aliases.get(track_id)
        return binding[0] if binding and binding[0] in self.records else None

    def update(
        self,
        scene: TemporalSceneSnapshot,
        width: int,
        height: int,
    ) -> tuple[tuple[str, WorldEventType], ...]:
        visible = sorted(scene.visible_objects, key=lambda item: item.track_id)
        temporal = {
            item.track_id: item
            for item in scene.objects
            if item.track_id in self._aliases
        }
        relation_tracks = {relation.track_id for relation in scene.relations}
        self._aliases = {
            track: binding
            for track, binding in self._aliases.items()
            if (
                track in temporal
                and temporal[track].first_seen_at == binding[1]
                or track not in temporal
                and track in relation_tracks
            )
            and binding[0] in self.records
        }
        assignments: dict[int, str] = {}
        reserved: set[str] = set()
        for item in visible:
            entity_id = self.resolve_track(item.track_id)
            if entity_id is None or entity_id in reserved:
                continue
            entity = self.records[entity_id].entity
            if (
                entity.active_track_id not in (None, item.track_id)
                or entity.label != item.label
                or entity.class_id != item.class_id
                or (
                    entity.presence in (WorldPresence.ABSENT, WorldPresence.UNKNOWN)
                    and scene.observed_at - entity.last_seen_at
                    > self.config.entity_match_timeout
                )
            ):
                continue
            assignments[item.track_id] = entity_id
            reserved.add(entity_id)

        # Match the whole sample in both directions to avoid order-dependent
        # merges when multiple same-class objects compete for the same identity.
        # Spatial buckets skip impossible pairs during bursts of tracker churn.
        cell_size = self.config.spatial_match_threshold
        nearby: dict[tuple[str, int | None, int, int], list[str]] = {}
        for entity_id, record in self.records.items():
            if entity_id in reserved:
                continue
            x, y, _, _ = record.geometry
            key = (
                record.entity.label,
                record.entity.class_id,
                math.floor(x / cell_size),
                math.floor(y / cell_size),
            )
            nearby.setdefault(key, []).append(entity_id)
        scores: dict[int, list[tuple[float, str]]] = {}
        reverse_scores: dict[str, list[tuple[float, int]]] = {}
        for item in visible:
            if item.track_id in assignments:
                continue
            candidates = []
            geometry = self._geometry(item, width, height)
            cell_x = math.floor(geometry[0] / cell_size)
            cell_y = math.floor(geometry[1] / cell_size)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    key = (item.label, item.class_id, cell_x + dx, cell_y + dy)
                    for entity_id in nearby.get(key, ()):
                        score = self._score(
                            item, self.records[entity_id], geometry, scene.observed_at
                        )
                        if score is not None:
                            candidates.append((score, entity_id))
                            reverse_scores.setdefault(entity_id, []).append(
                                (score, item.track_id)
                            )
            scores[item.track_id] = sorted(candidates)
        for contenders in reverse_scores.values():
            contenders.sort()
        for track_id, candidates in scores.items():
            if not candidates or self._ambiguous(candidates):
                continue
            _, entity_id = candidates[0]
            contenders = reverse_scores[entity_id]
            if contenders[0][1] != track_id or self._ambiguous(contenders):
                continue
            assignments[track_id] = entity_id
            reserved.add(entity_id)

        changes: list[tuple[str, WorldEventType]] = []
        for item in visible:
            entity_id = assignments.get(item.track_id)
            if entity_id is None:
                if not self._make_room(reserved):
                    continue
                label_slug = re.sub(r"[^a-z0-9]+", "_", item.label.lower())[:32]
                entity_id = f"{label_slug}_{uuid4().hex[:12]}"
                entity = WorldEntity(
                    entity_id=entity_id,
                    label=item.label[:80],
                    class_id=item.class_id,
                    active_track_id=item.track_id,
                    first_seen_at=scene.observed_at,
                    last_seen_at=item.last_seen_at,
                    last_known_position=item.position[:160],
                    presence=WorldPresence.VISIBLE,
                    confidence=item.confidence,
                )
                self.records[entity_id] = _Record(
                    entity, self._geometry(item, width, height)
                )
                changes.append((entity_id, WorldEventType.ENTITY_APPEARED))
            else:
                old = self.records[entity_id].entity
                if (
                    old.presence != WorldPresence.VISIBLE
                    or old.active_track_id != item.track_id
                ):
                    changes.append((entity_id, WorldEventType.ENTITY_REAPPEARED))
            reserved.add(entity_id)
            record = self.records[entity_id]
            record.entity = replace(
                record.entity,
                active_track_id=item.track_id,
                last_seen_at=item.last_seen_at,
                presence=WorldPresence.VISIBLE,
                last_known_position=item.position[:160],
                confidence=item.confidence,
                attributes={
                    **record.entity.attributes,
                    "motion": item.motion.value,
                    "depth_trend": item.depth_trend.value,
                },
            )
            record.geometry = self._geometry(item, width, height)
            self._aliases[item.track_id] = (entity_id, item.first_seen_at)

        for entity_id, record in self.records.items():
            if entity_id in reserved:
                continue
            old = record.entity
            item = temporal.get(old.active_track_id)
            presence = WorldPresence.ABSENT
            if (
                item is not None
                and self.resolve_track(item.track_id) == entity_id
                and item.presence == ObjectPresenceState.OCCLUDED
            ):
                presence = WorldPresence.OCCLUDED
            record.entity = replace(
                old,
                presence=presence,
                active_track_id=old.active_track_id
                if presence == WorldPresence.OCCLUDED
                else None,
            )
            if (
                old.presence != WorldPresence.ABSENT
                and presence == WorldPresence.ABSENT
            ):
                changes.append((entity_id, WorldEventType.ENTITY_DISAPPEARED))
        if len(self._aliases) > self.config.maximum_entities * 4:
            active = {r.entity.active_track_id for r in self.records.values()}
            ordered = sorted(
                self._aliases, key=lambda track: track in active, reverse=True
            )
            self._aliases = {
                track: self._aliases[track]
                for track in ordered[: self.config.maximum_entities * 4]
            }
        return tuple(changes)

    def interrupt(self) -> None:
        self._aliases.clear()
        for record in self.records.values():
            record.entity = replace(
                record.entity,
                active_track_id=None,
                presence=WorldPresence.UNKNOWN,
            )

    def reset(self) -> None:
        self.records.clear()
        self._aliases.clear()

    def _make_room(self, protected: set[str]) -> bool:
        if len(self.records) < self.config.maximum_entities:
            return True
        candidates = [
            r.entity for key, r in self.records.items() if key not in protected
        ]
        if not candidates:
            return False
        oldest = min(candidates, key=lambda entity: entity.last_seen_at)
        del self.records[oldest.entity_id]
        self._aliases = {
            track: binding
            for track, binding in self._aliases.items()
            if binding[0] != oldest.entity_id
        }
        return True

    def _ambiguous(self, candidates: list[tuple]) -> bool:
        return (
            len(candidates) > 1
            and candidates[1][0] - candidates[0][0] < self.config.ambiguity_margin
        )

    def _score(
        self,
        item: TemporalObjectState,
        record: _Record,
        geometry: tuple[float, float, float, float],
        now: float,
    ) -> float | None:
        old = record.entity
        elapsed = now - old.last_seen_at
        if (
            item.label != old.label
            or item.class_id != old.class_id
            or not 0 <= elapsed <= self.config.entity_match_timeout
            or min(item.confidence, old.confidence)
            < self.config.minimum_match_confidence
        ):
            return None
        x, y, w, h = geometry
        ox, oy, ow, oh = record.geometry
        if min(w, h, ow, oh) <= 0:
            return None
        distance = math.hypot(x - ox, y - oy)
        similarity = min(min(w, ow) / max(w, ow), min(h, oh) / max(h, oh))
        if (
            distance > self.config.spatial_match_threshold
            or similarity < self.config.size_similarity_threshold
        ):
            return None
        return (
            distance / self.config.spatial_match_threshold
            + (1 - similarity)
            + elapsed / self.config.entity_match_timeout * 0.1
        )

    @staticmethod
    def _geometry(
        item: TemporalObjectState, width: int, height: int
    ) -> tuple[float, float, float, float]:
        if width <= 0 or height <= 0:
            return (0.0, 0.0, 0.0, 0.0)
        x, y = item.box.center
        return (x / width, y / height, item.box.width / width, item.box.height / height)
