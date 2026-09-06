from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from friday.app.perception.detection import BoundingBox, SceneSnapshot, TrackedObject
from friday.app.perception.reasoning import (
    GemmaVisionClient,
    KeyframeReason,
    VisionKeyframe,
    VisionReasoningStatus,
    VisionRouter,
)
from friday.app.perception.relation import RelationEngineConfig, SceneRelationEngine
from friday.app.perception.scene import (
    HandObservation,
    SceneEvent,
    SceneEventConfig,
    SceneEventDetector,
    SceneEventType,
    SceneStateStore,
)
from friday.app.perception.service import PerceptionService
from friday.app.perception.window.intents import match_camera_window_intent
from friday.app.perception.window.schemas import CameraWindowAction
from friday.app.perception.world import (
    WorldEventType,
    WorldModel,
    WorldModelConfig,
    WorldPresence,
)


def tracked(
    track_id=7,
    *,
    x=40,
    y=120,
    width=40,
    height=80,
    confidence=0.9,
    label="bottle",
    class_id=39,
):
    return TrackedObject(
        track_id, class_id, label, confidence, BoundingBox(x, y, x + width, y + height)
    )


class Rig:
    def __init__(self, **config):
        self.now = 10.0
        self.sequence = 0
        self.store = SceneStateStore(
            SceneEventDetector(SceneEventConfig(disappear_after_seconds=0.5)),
            SceneRelationEngine(
                RelationEngineConfig(
                    hold_confirmation_frames=2, release_confirmation_frames=2
                )
            ),
        )
        self.world = WorldModel(WorldModelConfig(**config), clock=lambda: self.now)

    def sample(
        self, objects=(), *, at=None, detector_sampled=True, hands=None, status="ready"
    ):
        self.now = self.now + 0.1 if at is None else at
        self.sequence += 1
        scene = SceneSnapshot(
            sequence=self.sequence,
            captured_at=self.now,
            frame_width=400,
            frame_height=300,
            objects=tuple(objects),
            status=status,
            detector_sampled=detector_sampled,
        )
        self.store.update(scene, hand_observations=hands)
        self.world.update(scene, self.store.temporal_snapshot())
        return self.world.snapshot()

    def events(self, kind):
        return [e for e in self.world.snapshot().recent_events if e.event_type == kind]


def hand(*, gripping=False, pointing=False, x=0.15):
    return HandObservation(
        hand_id="right-1",
        handedness="right",
        confidence=0.94,
        gesture="grab" if gripping else "idle",
        is_pointing=pointing,
        is_gripping=gripping,
        palm_x=x,
        palm_y=0.5,
        interaction_x=x,
        interaction_y=0.5,
        index_base_x=0.01,
        index_base_y=0.5,
        index_tip_x=0.05,
        index_tip_y=0.5,
    )


def test_active_track_retains_identity_even_after_large_motion():
    rig = Rig()
    entity = rig.sample([tracked()]).entities[0]
    for x in (80, 160, 260):
        snapshot = rig.sample([tracked(x=x)])
        assert snapshot.entities[0].entity_id == entity.entity_id
    assert len(rig.events(WorldEventType.ENTITY_APPEARED)) == 1
    assert entity.entity_id != "7"


def test_occlusion_keeps_identity_without_prediction_as_new_evidence():
    rig = Rig()
    first = rig.sample([tracked()]).entities[0]
    occluded = rig.sample().entities[0]
    assert occluded.presence == WorldPresence.OCCLUDED
    predicted = rig.sample([tracked(x=300)], detector_sampled=False).entities[0]
    assert predicted.last_seen_at == first.last_seen_at
    assert predicted.last_known_position == first.last_known_position
    assert predicted.presence == WorldPresence.OCCLUDED
    returned = rig.sample([tracked()]).entities[0]
    assert returned.entity_id == first.entity_id


@pytest.mark.parametrize("return_x", [45, 80])
def test_new_track_plausibly_reuses_disappeared_entity(return_x):
    rig = Rig()
    original = rig.sample([tracked()], at=10).entities[0]
    rig.sample(at=10.2)
    absent = rig.sample(at=11)
    assert absent.entities[0].presence == WorldPresence.ABSENT
    returned = rig.sample([tracked(14, x=return_x)], at=11.1)
    assert len(returned.entities) == 1
    assert returned.entities[0].entity_id == original.entity_id
    assert returned.entities[0].active_track_id == 14
    # A delayed old-track disappearance cannot hide the reacquired entity.
    rig.sample([tracked(14, x=50)], at=12)
    assert rig.world.snapshot().entities[0].presence == WorldPresence.VISIBLE
    assert len(rig.events(WorldEventType.ENTITY_REAPPEARED)) == 1


@pytest.mark.parametrize(
    "changes,delay",
    [
        ({"x": 300}, 1),
        ({"width": 100}, 1),
        ({"confidence": 0.3}, 1),
        ({"label": "cup", "class_id": 41}, 1),
        ({}, 12),
    ],
)
def test_implausible_or_uncertain_match_creates_new_entity(changes, delay):
    rig = Rig()
    original = rig.sample([tracked()], at=10).entities[0]
    rig.sample(at=10.1)
    snapshot = rig.sample([tracked(14, **changes)], at=10 + delay)
    visible = [e for e in snapshot.entities if e.presence == WorldPresence.VISIBLE]
    assert len(visible) == 1
    assert visible[0].entity_id != original.entity_id


def test_same_class_objects_and_ambiguous_reappearance_never_collapse():
    rig = Rig()
    first = rig.sample([tracked(7, x=40), tracked(8, x=60)], at=10)
    ids = {e.entity_id for e in first.entities}
    assert len(ids) == 2
    rig.sample(at=10.1)
    ambiguous = rig.sample([tracked(14, x=50)], at=10.3)
    visible = [e for e in ambiguous.entities if e.presence == WorldPresence.VISIBLE]
    assert visible[0].entity_id not in ids
    assert len(ambiguous.entities) == 3


def test_competing_new_tracks_do_not_claim_one_old_entity():
    rig = Rig()
    old = rig.sample([tracked(x=50)], at=10).entities[0].entity_id
    rig.sample(at=10.1)
    result = rig.sample([tracked(14, x=45), tracked(15, x=55)], at=10.3)
    visible = [
        e.entity_id for e in result.entities if e.presence == WorldPresence.VISIBLE
    ]
    assert len(set(visible)) == 2
    assert old not in visible


def test_existing_active_track_is_reserved_before_new_track_matching():
    rig = Rig()
    old = rig.sample([tracked(99)]).entities[0].entity_id
    snapshot = rig.sample([tracked(1, x=42), tracked(99)])
    assert len(snapshot.entities) == 2
    assert (
        next(e for e in snapshot.entities if e.active_track_id == 99).entity_id == old
    )


def test_acceptance_pickup_occlusion_new_track_place_right_and_remember():
    rig = Rig()
    entity_id = rig.sample([tracked()], hands=()).entities[0].entity_id
    rig.sample([tracked()], hands=(hand(gripping=True),))
    held = rig.sample([tracked()], hands=(hand(gripping=True),))
    assert held.relations[0].subject_entity_id == entity_id
    assert len(rig.events(WorldEventType.OBJECT_PICKED_UP)) == 1
    rig.sample(hands=(hand(gripping=True),))
    reacquired = rig.sample([tracked(14, x=50)], hands=(hand(gripping=True),))
    assert len(reacquired.entities) == 1
    assert reacquired.entities[0].entity_id == entity_id
    # The real relation engine continues to use old track 7 throughout holding.
    assert rig.store.temporal_snapshot().relations[0].track_id == 7
    rig.sample([tracked(14, x=280)], hands=(hand(gripping=True, x=0.75),))
    rig.sample([tracked(14, x=280)], hands=(hand(x=0.75),))
    placed = rig.sample([tracked(14, x=280)], hands=(hand(x=0.75),))
    assert not placed.relations
    assert len(rig.events(WorldEventType.OBJECT_PICKED_UP)) == 1
    assert len(rig.events(WorldEventType.OBJECT_PLACED_DOWN)) == 1
    assert placed.entities[0].attributes["last_placed_position"] == "the right"
    rig.sample(hands=())
    absent = rig.sample(at=rig.now + 1, hands=())
    assert absent.entities[0].presence == WorldPresence.ABSENT
    assert absent.entities[0].last_known_position == "the right"
    # Short-term pruning cannot erase the world history.
    rig.sample(at=rig.now + 65)
    assert rig.store.temporal_snapshot().objects == ()
    summary = rig.world.describe(question="Where did I leave the bottle?")
    assert entity_id in summary
    assert "was placed down at the right" in summary
    assert "not currently visible" in summary
    assert "desk" not in summary


def test_absent_then_reacquired_held_entity_does_not_duplicate_pickup():
    rig = Rig()
    entity_id = rig.sample([tracked()], hands=()).entities[0].entity_id
    rig.sample([tracked()], hands=(hand(gripping=True),))
    rig.sample([tracked()], hands=(hand(gripping=True),))
    rig.sample(hands=(hand(gripping=True),))
    absent = rig.sample(at=rig.now + 1, hands=(hand(gripping=True),))
    assert absent.entities[0].presence == WorldPresence.ABSENT
    assert not absent.relations
    returned = rig.sample([tracked(14, x=45)], hands=(hand(gripping=True),))
    assert len(returned.entities) == 1
    assert returned.entities[0].entity_id == entity_id
    assert returned.relations[0].subject_entity_id == entity_id
    assert len(rig.events(WorldEventType.OBJECT_PICKED_UP)) == 1


def test_held_relation_alias_survives_old_track_pruning_until_release():
    rig = Rig()
    entity_id = rig.sample([tracked()], hands=()).entities[0].entity_id
    rig.sample([tracked()], hands=(hand(gripping=True),))
    rig.sample([tracked()], hands=(hand(gripping=True),))
    rig.sample(hands=(hand(gripping=True),))
    rig.sample([tracked(14)], hands=(hand(gripping=True),))
    snap = rig.sample([tracked(14)], at=rig.now + 65, hands=(hand(gripping=True),))
    assert all(obj.track_id != 7 for obj in rig.store.temporal_snapshot().objects)
    assert snap.relations[0].subject_entity_id == entity_id
    rig.sample([tracked(14, x=280)], hands=(hand(x=0.75),))
    rig.sample([tracked(14, x=280)], hands=(hand(x=0.75),))
    assert len(rig.events(WorldEventType.OBJECT_PICKED_UP)) == 1
    assert len(rig.events(WorldEventType.OBJECT_PLACED_DOWN)) == 1
    assert (
        rig.world.snapshot().entities[0].attributes["last_placed_position"]
        == "the right"
    )


def test_confirmed_pointing_and_motion_events_are_journaled_once():
    rig = Rig()
    rig.sample([tracked()], hands=(hand(pointing=True),))
    rig.sample([tracked()], hands=(hand(pointing=True),))
    assert len(rig.events(WorldEventType.OBJECT_POINTED_AT)) == 1
    moving = replace(tracked(), velocity_x=30)
    rig.sample([moving])
    rig.sample([moving])
    assert len(rig.events(WorldEventType.ENTITY_STARTED_MOVING)) == 1
    for _ in range(8):
        rig.sample([moving], detector_sampled=False)
    rig.sample([moving])
    assert len(rig.events(WorldEventType.ENTITY_STARTED_MOVING)) == 1


def test_interruption_preserves_knowledge_but_not_active_visibility_or_track_alias():
    rig = Rig()
    original = rig.sample([tracked()], at=10).entities[0].entity_id
    before_events = rig.world.recent_events()
    offline = rig.sample(status="error", at=10.1)
    assert offline.entities[0].presence == WorldPresence.UNKNOWN
    assert offline.entities[0].active_track_id is None
    assert offline.recent_events == before_events
    assert "visibility unknown" in rig.world.describe()
    restarted = rig.sample([tracked(14, x=45)], at=10.4)
    assert restarted.entities[0].entity_id == original
    rig.sample(status="idle", at=10.5)
    reused_id = rig.sample([tracked(14, x=300)], at=11)
    assert len(reused_id.entities) == 2


def test_restart_in_the_same_clock_tick_accepts_the_new_tracking_epoch():
    rig = Rig()
    original = rig.sample([tracked()], at=10).entities[0].entity_id
    rig.sample(status="idle", at=10)
    restarted = rig.sample([tracked(14)], at=10)
    assert len(restarted.entities) == 1
    assert restarted.entities[0].entity_id == original
    assert restarted.entities[0].presence == WorldPresence.VISIBLE
    assert restarted.entities[0].active_track_id == 14


def test_stale_frame_cannot_restore_visibility_after_interruption():
    rig = Rig()
    rig.sample([tracked()], at=10)
    scene = replace(rig.store.snapshot(), captured_at=10.1)
    temporal = replace(rig.store.temporal_snapshot(), observed_at=10.1)
    rig.world.interrupt(observed_at=11)
    rig.world.update(scene, temporal)
    assert rig.world.snapshot().entities[0].presence == WorldPresence.UNKNOWN


def test_full_reset_clears_world_and_old_event_window_is_not_replayed():
    rig = Rig()
    rig.sample([tracked()], hands=(hand(gripping=True),))
    rig.sample([tracked()], hands=(hand(gripping=True),))
    old_id = rig.world.snapshot().entities[0].entity_id
    rig.world.reset()
    reset = rig.world.snapshot()
    assert reset.entities == reset.relations == reset.recent_events == ()
    assert reset.last_updated_at == 0
    rebuilt = rig.sample([tracked()], hands=())
    assert rebuilt.entities[0].entity_id != old_id


def test_reset_does_not_replay_motion_events_from_the_short_term_store():
    rig = Rig()
    rig.sample([tracked()])
    moving = replace(tracked(), velocity_x=30)
    rig.sample([moving])
    rig.sample([moving])
    assert rig.events(WorldEventType.ENTITY_STARTED_MOVING)
    rig.world.reset()
    rig.sample([moving])
    assert not rig.events(WorldEventType.ENTITY_STARTED_MOVING)


def test_upstream_place_event_updates_position_and_preserves_source_id():
    rig = Rig()
    rig.sample([tracked()])
    rig.sample([tracked(x=280)])
    scene = replace(rig.store.snapshot(), captured_at=rig.now + 0.1)
    temporal = replace(
        rig.store.temporal_snapshot(),
        observed_at=scene.captured_at,
        recent_events=(
            SceneEvent(
                "relation-9",
                SceneEventType.OBJECT_PLACED_DOWN,
                7,
                "bottle",
                scene.captured_at,
                "placed",
                0.9,
            ),
        ),
    )
    rig.world.update(scene, temporal)
    event = rig.events(WorldEventType.OBJECT_PLACED_DOWN)[0]
    assert event.source_event_id == "relation-9"
    assert "right" in event.description
    assert (
        rig.world.snapshot().entities[0].attributes["last_placed_position"]
        == "the right"
    )


def test_identity_matching_uses_normalized_geometry_after_resolution_change():
    rig = Rig()
    original = rig.sample([tracked()]).entities[0].entity_id
    rig.sample()
    rig.now += 0.1
    scene = SceneSnapshot(
        status="ready",
        captured_at=rig.now,
        frame_width=800,
        frame_height=600,
        objects=(tracked(14, x=80, y=240, width=80, height=160),),
    )
    rig.store.update(scene)
    rig.world.update(scene, rig.store.temporal_snapshot())
    assert rig.world.snapshot().entities[0].entity_id == original
    assert len(rig.world.snapshot().entities) == 1


def test_duplicate_samples_and_old_events_remain_deduplicated_after_eviction():
    rig = Rig(maximum_events=1)
    rig.sample([tracked()], at=10)
    moving = replace(tracked(), velocity_x=30)
    rig.sample([moving], at=10.1)
    rig.sample([moving], at=10.2)
    snapshot = rig.world.snapshot()
    for _ in range(3):
        rig.world.update(rig.store.snapshot(), rig.store.temporal_snapshot())
    assert rig.world.snapshot() == snapshot
    rig.sample([tracked(14, x=300)], at=10.3)
    last = rig.world.recent_events()
    rig.sample([tracked(14, x=300)], at=10.4)
    assert rig.world.recent_events() == last


def test_entity_alias_relation_and_journal_memory_is_bounded():
    rig = Rig(maximum_entities=4, maximum_events=6)
    for i in range(100):
        rig.sample([tracked(i, label=f"object{i}")])
        snap = rig.world.snapshot()
        assert len(snap.entities) <= 4
        assert len(snap.recent_events) <= 6
        assert len(rig.world._registry._aliases) <= 16
        assert all(
            r.subject_entity_id in {e.entity_id for e in snap.entities}
            for r in snap.relations
        )
    assert len(rig.world.snapshot().entities) == 4


def test_entity_limit_preserves_visible_entities_when_new_objects_arrive():
    rig = Rig(maximum_entities=1)
    entity_id = rig.sample([tracked(99)]).entities[0].entity_id
    snap = rig.sample([tracked(1, x=300), tracked(99)])
    assert [e.entity_id for e in snap.entities] == [entity_id]


def test_event_retention_ages_out_without_requiring_more_camera_frames():
    rig = Rig(event_retention_seconds=5)
    rig.sample([tracked()], at=10)
    assert rig.world.recent_events()
    rig.now = 16
    assert not rig.world.recent_events()
    assert rig.world.snapshot().entities


def test_summary_is_bounded_and_prioritizes_queried_absent_object():
    rig = Rig()
    bottle = rig.sample([tracked()]).entities[0].entity_id
    rig.sample([tracked(i, label=f"object{i}", x=300) for i in range(20, 50)])
    summary = rig.world.describe(question="Where did I leave the bottle?")
    assert bottle in summary
    assert len(summary) <= 2400
    assert len(rig.world.describe(max_chars=30)) <= 30
    assert rig.world.describe(max_chars=0) == ""


def test_snapshots_are_detached_and_serialize_without_frames():
    rig = Rig()
    snap = rig.sample([tracked()])
    snap.entities[0].attributes["motion"] = "corrupted"
    assert rig.world.snapshot().entities[0].attributes["motion"] != "corrupted"
    encoded = json.dumps(rig.world.snapshot().to_dict())
    assert '"presence": "visible"' in encoded
    assert "jpeg" not in encoded


def test_concurrent_reads_updates_interruptions_and_resets_are_safe():
    rig = Rig()

    def writer():
        for i in range(100):
            rig.sample([tracked()], at=10 + i)

    def reader():
        for _ in range(100):
            snap = rig.world.snapshot()
            assert len({e.entity_id for e in snap.entities}) == len(snap.entities)
            assert all(
                r.subject_entity_id in {e.entity_id for e in snap.entities}
                for r in snap.relations
            )
            assert len(rig.world.describe()) <= 2400
            rig.world.recent_events()

    def resetter():
        for _ in range(20):
            rig.world.interrupt()
            rig.world.reset()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(writer),
            pool.submit(reader),
            pool.submit(reader),
            pool.submit(resetter),
        ]
        for future in futures:
            future.result(timeout=15)


def test_config_handles_blank_invalid_and_nonfinite_environment(monkeypatch):
    monkeypatch.setenv("FRIDAY_VISION_WORLD_ENTITY_MATCH_TIMEOUT", "nan")
    monkeypatch.setenv("FRIDAY_VISION_WORLD_MAXIMUM_ENTITIES", "")
    monkeypatch.setenv("FRIDAY_VISION_WORLD_SPATIAL_MATCH_THRESHOLD", "broken")
    assert WorldModelConfig.from_environment() == WorldModelConfig()
    monkeypatch.setenv("FRIDAY_VISION_WORLD_ENTITY_MATCH_TIMEOUT", "3")
    assert WorldModelConfig.from_environment().entity_match_timeout == 3
    with pytest.raises(ValueError):
        WorldModelConfig(maximum_entities=0)
    with pytest.raises(ValueError):
        WorldModelConfig(spatial_match_threshold=float("nan"))


def test_perception_publish_stop_and_reset_use_world_lifecycle():
    manager = SimpleNamespace(release=Mock())
    service = PerceptionService(manager=manager)
    scene = SceneSnapshot(
        status="ready",
        captured_at=10,
        objects=(tracked(),),
        frame_width=400,
        frame_height=300,
    )
    service._publish_scene(scene)
    entity_id = service.world_snapshot().entities[0].entity_id
    assert "bottle" in service.describe_world()
    assert service.recent_world_events(limit=0) == ()
    service.stop()
    assert service.world_snapshot().entities[0].entity_id == entity_id
    assert service.world_snapshot().entities[0].presence == WorldPresence.UNKNOWN
    # A late worker result cannot overwrite the stopped state.
    service._publish_scene(replace(scene, captured_at=9999999999))
    assert service.world_snapshot().camera_status == "idle"
    service.reset_world()
    assert service.world_snapshot().entities == ()


def test_service_start_stop_restart_preserves_entity_without_reusing_track_ids():
    published = threading.Event()
    manager = SimpleNamespace(acquire=Mock(), release=Mock())
    service = PerceptionService(manager=manager)
    runtime_track_id = 7

    def worker():
        service._publish_scene(
            SceneSnapshot(
                status="ready",
                captured_at=time.time(),
                frame_width=400,
                frame_height=300,
                objects=(tracked(runtime_track_id),),
            )
        )
        published.set()
        service._stop_event.wait(3)

    try:
        with (
            patch.object(service, "_run", worker),
            patch(
                "friday.app.perception.service.perception_service.detection_enabled",
                return_value=True,
            ),
        ):
            assert service.start(0)
            assert published.wait(3)
            entity_id = service.world_snapshot().entities[0].entity_id
            service.stop()
            published.clear()
            runtime_track_id = 14
            assert service.start(0)
            assert published.wait(3)
            snap = service.world_snapshot()
            assert len(snap.entities) == 1
            assert snap.entities[0].entity_id == entity_id
            assert snap.entities[0].active_track_id == 14
    finally:
        service.stop()


def test_slow_worker_cannot_overlap_a_restart():
    service = PerceptionService(manager=SimpleNamespace(release=Mock(), acquire=Mock()))
    old_worker = Mock()
    old_worker.is_alive.return_value = True
    service._thread = old_worker
    service._camera_index = 0
    service.stop()
    with patch(
        "friday.app.perception.service.perception_service.detection_enabled",
        return_value=True,
    ):
        assert not service.start(0)
    service._manager.acquire.assert_not_called()


def test_restart_is_blocked_until_stop_finishes_releasing_camera():
    manager = SimpleNamespace(release=Mock(), acquire=Mock())
    service = PerceptionService(manager=manager)
    attempts = []
    manager.release.side_effect = lambda owner: attempts.append(service.start(0))
    with patch(
        "friday.app.perception.service.perception_service.detection_enabled",
        return_value=True,
    ):
        service.stop()
    assert attempts == [False]
    manager.acquire.assert_not_called()


def test_vision_fallback_includes_remembered_world_when_camera_is_offline():
    service = PerceptionService(manager=SimpleNamespace(release=Mock()))
    service._publish_scene(
        SceneSnapshot(
            status="ready",
            captured_at=10,
            objects=(tracked(),),
            frame_width=400,
            frame_height=300,
        )
    )
    service.stop()
    client = Mock()
    result = VisionRouter(service, client=client).analyze_sync(
        "Where did I leave the bottle?"
    )
    assert result.status == VisionReasoningStatus.FALLBACK
    assert "bottle" in result.answer and "visibility unknown" in result.answer
    client.analyze.assert_not_called()


def test_world_context_reaches_gemma_and_invalidates_cached_answer():
    captured = []

    def request(url, payload, timeout):
        captured.append(payload["messages"][0]["content"])
        return {
            "message": {
                "content": '{"answer":"Last seen on the right.","confidence":0.8}'
            }
        }

    frame = VisionKeyframe(
        1, 10, 400, 300, KeyframeReason.USER_REQUEST, "scene", (), jpeg_bytes=b"test"
    )
    service = Mock()
    service.describe_scene.return_value = "scene"
    service.describe_world.return_value = "bottle_01 was placed on the left."
    service.snapshot.return_value = SceneSnapshot(status="ready")
    service.capture_keyframe.return_value = frame
    router = VisionRouter(
        service, client=GemmaVisionClient(requester=request), enabled=True
    )
    question = "Where did I leave the bottle?"
    router.analyze_sync(question)
    assert router.analyze_sync(question).used_cache
    service.describe_world.return_value = (
        "bottle_01 was placed on the right; not currently visible."
    )
    assert not router.analyze_sync(question).used_cache
    assert len(captured) == 2
    assert "on the right; not currently visible" in captured[-1]
    assert "not proof of current" in captured[-1]
    assert frame.world_summary == ""


@pytest.mark.parametrize("mode", ["disabled", "no_keyframe", "provider_error"])
def test_all_reasoning_fallback_paths_keep_world_evidence(mode):
    service = Mock()
    service.describe_scene.return_value = "scene fallback"
    service.describe_world.return_value = (
        "Bottle last seen on the right, not currently visible."
    )
    service.snapshot.return_value = SceneSnapshot(status="ready")
    service.capture_keyframe.return_value = (
        None
        if mode == "no_keyframe"
        else VisionKeyframe(
            1,
            10,
            400,
            300,
            KeyframeReason.USER_REQUEST,
            "scene",
            (),
            jpeg_bytes=b"test",
        )
    )

    def unavailable(*args):
        raise OSError("offline")

    router = VisionRouter(
        service,
        client=GemmaVisionClient(requester=unavailable),
        enabled=mode != "disabled",
    )
    answer = router.analyze_sync("Where did I leave the bottle?")
    assert answer.ok
    assert "scene fallback" in answer.answer
    assert "last seen on the right" in answer.answer


@pytest.mark.parametrize(
    "question",
    [
        "Where did I leave the bottle?",
        "FRIDAY, where did I put my cup?",
        "Friday, please where did I place that laptop?",
    ],
)
def test_world_history_questions_reach_camera_reasoning(question):
    assert match_camera_window_intent(question).action == CameraWindowAction.ANALYZE
