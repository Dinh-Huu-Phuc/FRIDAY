from __future__ import annotations

from dataclasses import replace
from threading import RLock
from typing import TYPE_CHECKING

from friday.app.perception.detection import SceneSnapshot
from friday.app.perception.scene.event_detector import SceneEventDetector
from friday.app.perception.scene.schemas import (
    HandObservation,
    SceneEvent,
    TemporalSceneSnapshot,
)
from friday.app.perception.scene.summarizer import summarize_scene

if TYPE_CHECKING:
    from friday.app.perception.relation.engine import SceneRelationEngine


class SceneStateStore:
    def __init__(
        self,
        event_detector: SceneEventDetector | None = None,
        relation_engine: SceneRelationEngine | None = None,
    ) -> None:
        self._lock = RLock()
        self._snapshot = SceneSnapshot.idle()
        self._event_detector = event_detector or SceneEventDetector()
        if relation_engine is None:
            from friday.app.perception.relation.engine import SceneRelationEngine

            relation_engine = SceneRelationEngine()
        self._relation_engine = relation_engine
        self._temporal = TemporalSceneSnapshot.empty()

    def update(
        self,
        snapshot: SceneSnapshot,
        *,
        hand_observations: tuple[HandObservation, ...] | None = None,
    ) -> None:
        with self._lock:
            self._snapshot = snapshot
            temporal = self._event_detector.update(snapshot)
            if snapshot.status != "ready":
                self._relation_engine.reset()
                self._temporal = temporal
                return
            if snapshot.detector_sampled:
                relations, relation_events = self._relation_engine.update(
                    temporal,
                    hand_observations=hand_observations,
                    frame_width=snapshot.frame_width,
                    frame_height=snapshot.frame_height,
                )
            else:
                relations, relation_events = self._relation_engine.snapshot(
                    observed_at=temporal.observed_at
                )
            events = tuple(
                sorted(
                    (*temporal.recent_events, *relation_events),
                    key=lambda item: (item.occurred_at, item.event_id),
                )
            )
            last_change = max(
                temporal.last_significant_change_at,
                self._relation_engine.last_change_at,
            )
            self._temporal = replace(
                temporal,
                relations=relations,
                recent_events=events,
                last_significant_change_at=last_change,
                stable_for_seconds=max(0.0, temporal.observed_at - last_change),
            )

    def snapshot(self) -> SceneSnapshot:
        with self._lock:
            return self._snapshot

    def temporal_snapshot(self) -> TemporalSceneSnapshot:
        with self._lock:
            return self._temporal

    def recent_events(self) -> tuple[SceneEvent, ...]:
        with self._lock:
            return self._temporal.recent_events

    def describe(self) -> str:
        with self._lock:
            return summarize_scene(self._snapshot, self._temporal)
