from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from unittest.mock import Mock, patch

import pytest

from friday.app.perception.detection import BoundingBox, SceneSnapshot
from friday.app.perception.reasoning import (
    GemmaVisionClient,
    GemmaVisionOutput,
    KeyframeReason,
    VisionKeyframe,
    VisionModelError,
    VisionRouter,
)
from friday.app.perception.reasoning.question_policy import (
    QuestionKind,
    classify_camera_question,
)
from friday.app.perception.reasoning.telemetry import OllamaTimings
from friday.app.perception.scene.schemas import (
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectPresenceState,
    ObjectRelation,
    ObjectRelationType,
    TemporalObjectState,
    TemporalSceneSnapshot,
)
from friday.app.perception.window.intents import match_camera_window_intent
from friday.app.perception.window.schemas import CameraWindowAction
from friday.app.perception.world import (
    WorldEntity,
    WorldEvent,
    WorldEventType,
    WorldPresence,
    WorldSnapshot,
)


def obj(track_id=1, label="person", **changes):
    state = TemporalObjectState(
        track_id=track_id,
        class_id=0 if label == "person" else 39,
        label=label,
        confidence=0.95,
        box=BoundingBox(20, 20, 150, 300),
        presence=ObjectPresenceState.VISIBLE,
        motion=ObjectMotionState.MOVING,
        depth_trend=ObjectDepthTrend.APPROACHING,
        position="the right",
        movement_direction="right",
        normalized_speed=0.1,
        first_seen_at=95,
        last_seen_at=100,
        visible_since=95,
        unseen_since=None,
        age_seconds=5,
    )
    return replace(state, **changes)


def scene(objects=None, relations=None):
    return TemporalSceneSnapshot(
        observed_at=100,
        status="ready",
        objects=tuple(objects if objects is not None else [obj(), obj(7, "bottle")]),
        relations=tuple(
            relations
            if relations is not None
            else [
                ObjectRelation(
                    ObjectRelationType.HELD_BY_HAND,
                    7,
                    "bottle",
                    "hand-1",
                    "right",
                    0.95,
                    98,
                    0.2,
                    0.3,
                )
            ]
        ),
    )


def perception(state=None, world=None):
    fake = Mock()
    fake.snapshot.return_value = SceneSnapshot(status="ready", captured_at=100)
    fake.temporal_snapshot.return_value = state or scene()
    fake.world_snapshot.return_value = world or WorldSnapshot()
    fake.describe_scene.return_value = "Scene fallback."
    fake.describe_world.return_value = "HISTORY MUST NOT LEAK"
    fake.capture_keyframe.return_value = VisionKeyframe(
        1,
        100,
        896,
        504,
        KeyframeReason.USER_REQUEST,
        "OLD HISTORY MUST NOT LEAK",
        (),
        jpeg_bytes=b"private-image",
    )
    return fake


def client():
    fake = Mock(model="gemma3:test")
    fake.analyze.return_value = GemmaVisionOutput(
        "The person appears to be reading.", confidence=0.8
    )
    return fake


@pytest.mark.parametrize(
    "question",
    [
        "What am I holding?",
        "Is the person holding something?",
        "Is the person moving?",
        "What objects can you see?",
        "Where is the bottle?",
        "Is someone approaching the camera?",
    ],
)
def test_fast_questions_skip_gemma_and_image_encoding(question):
    camera, gemma = perception(), client()
    result = VisionRouter(camera, client=gemma, clock=lambda: 100).analyze_sync(
        question
    )
    assert result.timings.route == "structured"
    assert not result.timings.gemma_invoked
    assert result.timings.jpeg_encoding_ms == 0
    assert result.latency_ms == result.timings.total_ms
    assert result.answer
    gemma.analyze.assert_not_called()
    camera.capture_keyframe.assert_not_called()
    camera.describe_world.assert_not_called()
    assert match_camera_window_intent(question).action == CameraWindowAction.ANALYZE


@pytest.mark.parametrize(
    "question,state",
    [
        ("What is the person on camera doing?", scene()),
        ("What is the person doing right now?", scene()),
        ("Is the person moving?", scene([obj(motion=ObjectMotionState.UNKNOWN)])),
        ("Is the person moving?", scene([obj(), obj(2)])),
        ("What am I holding?", scene(relations=[])),
        ("What am I holding?", scene([obj(), obj(2), obj(7, "bottle")])),
        (
            "Where is the bottle?",
            scene([obj(7, "bottle"), obj(8, "bottle", confidence=0.4)]),
        ),
        ("Where is the bottle?", scene([obj(7, "bottle", confidence=0.4)])),
        ("What objects can you see?", scene([obj(last_seen_at=95)])),
        (
            "Is someone approaching the camera?",
            scene([obj(depth_trend=ObjectDepthTrend.STABLE)]),
        ),
    ],
)
def test_ambiguous_or_stale_evidence_still_uses_gemma(question, state):
    camera, gemma = perception(state), client()
    result = VisionRouter(camera, client=gemma, clock=lambda: 100).analyze_sync(
        question
    )
    gemma.analyze.assert_called_once()
    assert result.timings.gemma_invoked
    frame = gemma.analyze.call_args.args[1]
    assert frame.world_summary == ""
    assert len(frame.scene_summary) <= 800
    assert "HISTORY" not in frame.scene_summary
    assert frame.frame_width == 896
    camera.describe_world.assert_not_called()


def test_historical_context_includes_only_the_named_object():
    entities = tuple(
        WorldEntity(
            entity_id=label + "_1",
            label=label,
            class_id=39,
            active_track_id=None,
            first_seen_at=50,
            last_seen_at=90,
            last_known_position="the right",
            presence=WorldPresence.ABSENT,
            confidence=0.95,
        )
        for label in ("bottle", "laptop")
    )
    events = tuple(
        WorldEvent(
            event_id=label,
            event_type=WorldEventType.OBJECT_PLACED_DOWN,
            occurred_at=90,
            entity_id=label + "_1",
            description=f"{label} was placed at the right",
            confidence=0.95,
        )
        for label in ("bottle", "laptop")
    )
    camera, gemma = (
        perception(world=WorldSnapshot(entities=entities, recent_events=events)),
        client(),
    )
    result = VisionRouter(camera, client=gemma, clock=lambda: 100).analyze_sync(
        "Where did I leave the bottle?"
    )
    frame = gemma.analyze.call_args.args[1]
    assert "bottle was placed" in frame.world_summary
    assert "laptop" not in frame.world_summary
    assert "not currently visible" in frame.world_summary
    assert len(frame.world_summary) <= 2400
    assert result.timings.question_kind == "historical"


def test_fast_path_remains_available_while_a_semantic_request_is_busy():
    gemma = client()
    router = VisionRouter(perception(), client=gemma, clock=lambda: 100)
    with router._inference_lock:
        fast = router.analyze_sync("What objects can you see?")
        busy = router.analyze_sync("What is the person doing?")
    assert fast.timings.route == "structured"
    assert busy.timings.route == "busy"
    assert "still analyzing" in busy.answer
    gemma.analyze.assert_not_called()


def test_cached_request_does_not_reuse_previous_ollama_timing_metadata():
    gemma = client()
    router = VisionRouter(perception(), client=gemma, clock=lambda: 100)
    first = router.analyze_sync("What is the person doing?")
    second = router.analyze_sync("What is the person doing?")
    assert first.timings.gemma_invoked
    assert second.used_cache and second.timings.route == "cache"
    assert not second.timings.gemma_invoked
    assert second.timings.ollama == OllamaTimings()
    assert gemma.analyze.call_count == 1


def test_ollama_timings_parse_nanoseconds_and_reject_invalid_numbers():
    timings = OllamaTimings.from_response(
        {
            "total_duration": 6_000_000_000,
            "load_duration": 1_000_000_000,
            "prompt_eval_duration": 2_000_000_000,
            "eval_duration": 3_000_000_000,
            "prompt_eval_count": 500,
            "eval_count": 100,
        }
    )
    assert timings == OllamaTimings(6000, 1000, 2000, 3000, 500, 100)
    assert (
        OllamaTimings.from_response(
            {"load_duration": float("nan"), "eval_duration": -1, "eval_count": True}
        )
        == OllamaTimings()
    )


def test_request_defaults_and_configurable_output_budget(monkeypatch):
    monkeypatch.delenv("FRIDAY_VISION_REASONING_KEEP_ALIVE", raising=False)
    monkeypatch.delenv("FRIDAY_VISION_REASONING_NUM_PREDICT", raising=False)
    calls = []

    def request(endpoint, payload, timeout):
        calls.append(payload)
        return {
            "message": {"content": '{"answer":"A person is visible."}'},
            "load_duration": 7_000_000,
        }

    model = GemmaVisionClient(requester=request)
    output = model.analyze("Describe the scene", perception().capture_keyframe())
    assert calls[0]["keep_alive"] == "30m"
    assert calls[0]["options"]["num_predict"] == 128
    assert calls[0]["options"]["num_ctx"] == 2048
    assert output.timings.load_duration_ms == 7
    monkeypatch.setenv("FRIDAY_VISION_REASONING_KEEP_ALIVE", "45m")
    monkeypatch.setenv("FRIDAY_VISION_REASONING_NUM_PREDICT", "96")
    model = GemmaVisionClient(requester=request)
    model.analyze("Describe the scene", perception().capture_keyframe())
    assert calls[-1]["keep_alive"] == "45m"
    assert calls[-1]["options"]["num_predict"] == 96


def test_startup_preload_uses_runtime_keep_alive(monkeypatch):
    from friday.app.perception.reasoning.gemma_vision import preload_vision_model

    monkeypatch.setenv("FRIDAY_VISION_REASONING_KEEP_ALIVE", "45m")
    with patch("friday.app.perception.reasoning.gemma_vision._post_json") as post:
        preload_vision_model()
    payload = post.call_args.args[1]
    assert payload["keep_alive"] == GemmaVisionClient().keep_alive == "45m"
    assert payload["options"]["num_ctx"] == GemmaVisionClient().context_tokens


def test_truncated_json_is_a_failure_not_a_partial_answer():
    model = GemmaVisionClient(
        requester=lambda *args: {"message": {"content": '{"answer":"The person is'}}
    )
    with pytest.raises(VisionModelError, match="incomplete"):
        model.analyze("Describe", perception().capture_keyframe())


def test_latency_logs_never_include_question_image_or_answer(caplog):
    caplog.set_level(
        logging.INFO, logger="friday.app.perception.reasoning.vision_router"
    )
    result = VisionRouter(
        perception(), client=client(), clock=lambda: 100
    ).analyze_sync("private-question")
    assert "Vision latency:" in caplog.text
    assert "private-question" not in caplog.text
    assert "private-image" not in caplog.text
    assert result.answer not in caplog.text
    assert result.timings.total_ms >= result.timings.ollama_request_ms


def test_classification_does_not_confuse_semantic_actions_with_motion():
    assert (
        classify_camera_question("What is the person doing right now?").kind
        == QuestionKind.SEMANTIC
    )
    assert (
        classify_camera_question("Where did I leave the bottle?").kind
        == QuestionKind.HISTORY
    )
    assert (
        match_camera_window_intent("Where is Paris?").action == CameraWindowAction.NONE
    )
    assert (
        classify_camera_question("What changed in front of the camera?").kind
        == QuestionKind.HISTORY
    )


def test_timings_are_preserved_when_model_returns_truncated_json():
    model = GemmaVisionClient(
        requester=lambda *args: {
            "message": {"content": '{"answer":"cut off'},
            "eval_duration": 3_000_000,
        }
    )
    result = VisionRouter(perception(), client=model, clock=lambda: 100).analyze_sync(
        "What is the person doing?"
    )
    assert result.timings.route == "fallback"
    assert result.timings.ollama.eval_duration_ms == 3


def test_async_total_latency_includes_dispatch_and_fast_path_works_disabled():
    router = VisionRouter(
        perception(), client=client(), clock=lambda: 100, enabled=False
    )
    result = asyncio.run(router.analyze("What objects can you see?"))
    assert result.timings.route == "structured"
    assert result.timings.total_ms >= result.timings.dispatch_wait_ms


def test_benchmark_reports_unmeasured_vlm_without_inventing_timings():
    from friday.app.perception.reasoning.benchmark import run_benchmark

    report = run_benchmark(fast_samples=3)
    assert report["fast_path"]["samples"] == 3
    assert not report["fast_path"]["gemma_invoked"]
    assert report["semantic_requests"] == []


def test_real_keyframe_path_reports_acquisition_encoding_and_context():
    from types import SimpleNamespace

    from friday.app.perception.reasoning import KeyframeStore
    from friday.app.perception.scene import SceneStateStore
    from friday.app.perception.service import PerceptionService

    store = SceneStateStore()
    store.update(
        SceneSnapshot(
            status="ready", captured_at=100, frame_width=640, frame_height=360
        )
    )
    camera = SimpleNamespace(
        latest_frame=lambda **kwargs: SimpleNamespace(shape=(360, 640, 3)),
        status=lambda: SimpleNamespace(frame_sequence=2),
    )
    calls = []

    def encode(frame, edge, quality):
        calls.append((edge, quality))
        return b"jpeg", 640, 360

    service = PerceptionService(
        manager=camera, state_store=store, keyframe_store=KeyframeStore(encoder=encode)
    )
    stages = {}
    assert service.capture_keyframe(timings=stages).jpeg_bytes == b"jpeg"
    assert calls == [(896, 82)]
    assert stages["frame_acquisition_ms"] >= 0
    assert stages["jpeg_encoding_ms"] >= 0
    assert stages["context_build_ms"] >= 0
