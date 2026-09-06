from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import numpy as np

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.perception.detection import (
    BoundingBox,
    SceneSnapshot,
    TargetLock,
    TargetLockState,
    TrackedObject,
)
from friday.app.perception.reasoning import KeyframeReason, VisionKeyframe
from friday.app.perception.segmentation import (
    Sam2Config,
    Sam2ImageSegmenter,
    Sam2Prediction,
    SegmentationCapabilities,
    SegmentationIntentAction,
    SegmentationMode,
    SegmentationResult,
    SegmentationService,
    SegmentationStatus,
    decode_binary_mask,
    encode_binary_mask,
    match_segmentation_intent,
)
from friday.src.router.api_router import api_router
from friday.src.services.agent.service import chat


def _config(tmp_path: Path, *, tracking_fps: float = 1.0) -> Sam2Config:
    return Sam2Config(
        enabled=True,
        checkpoint_path=tmp_path / "sam2.1_hiera_tiny.pt",
        model_config="configs/sam2.1/sam2.1_hiera_t.yaml",
        device="auto",
        minimum_cuda_vram_mb=3584,
        multimask_output=True,
        tracking_fps=tracking_fps,
        tracking_max_misses=2,
        result_ttl_seconds=30.0,
    )


def _keyframe() -> VisionKeyframe:
    return VisionKeyframe(
        sequence=22,
        captured_at=2.0,
        frame_width=320,
        frame_height=180,
        reason=KeyframeReason.USER_REQUEST,
        scene_summary="A person is centered.",
        scene_signature=(("person", 1),),
        jpeg_bytes=b"encoded-frame",
    )


def _snapshot() -> SceneSnapshot:
    person = TrackedObject(
        track_id=7,
        class_id=0,
        label="person",
        confidence=0.94,
        box=BoundingBox(160, 40, 480, 340),
        age_frames=12,
    )
    return SceneSnapshot(
        sequence=22,
        frame_width=640,
        frame_height=360,
        objects=(person,),
        target_lock=TargetLock(
            state=TargetLockState.LOCKED,
            target=person,
            stable_frames=8,
        ),
        status="ready",
        model_name="yolo26n",
    )


class _FakePerception:
    def __init__(self, *, snapshot: SceneSnapshot | None = None) -> None:
        self.scene = snapshot or _snapshot()
        self.published: SegmentationResult | None = None

    def snapshot(self) -> SceneSnapshot:
        return self.scene

    @staticmethod
    def capture_keyframe() -> VisionKeyframe:
        return _keyframe()

    def set_segmentation_result(self, result: SegmentationResult | None) -> None:
        self.published = result


class _FakeSegmenter:
    model = "sam2-test"
    device = "cpu"

    def __init__(self, config: Sam2Config) -> None:
        self.config = config
        self.calls: list[BoundingBox] = []
        self.unloaded = False

    def capabilities(self) -> SegmentationCapabilities:
        return SegmentationCapabilities(
            enabled=True,
            package_available=True,
            checkpoint_available=True,
            checkpoint_path=str(self.config.checkpoint_path),
            sam2_model_config=self.config.model_config,
            requested_device=self.config.device,
            tracking_fps=self.config.tracking_fps,
            ready=True,
        )

    def segment(
        self,
        keyframe: VisionKeyframe,
        box: BoundingBox,
    ) -> Sam2Prediction:
        self.calls.append(box)
        mask = np.zeros((keyframe.frame_height, keyframe.frame_width), dtype=np.uint8)
        mask[box.y1 : box.y2, box.x1 : box.x2] = 1
        return Sam2Prediction(
            mask=mask,
            confidence=0.93,
            model=self.model,
            device=self.device,
        )

    def unload(self) -> None:
        self.unloaded = True


class _FakeBackend:
    model_name = "sam2-backend-test"
    device = "cpu"

    def __init__(self) -> None:
        self.calls: list[BoundingBox] = []

    def predict(self, _jpeg_bytes: bytes, box: BoundingBox) -> Sam2Prediction:
        self.calls.append(box)
        return Sam2Prediction(
            mask=np.ones((180, 320), dtype=np.uint8),
            confidence=0.9,
            model=self.model_name,
            device=self.device,
        )


def test_binary_mask_rle_round_trip_preserves_every_pixel() -> None:
    mask = np.asarray(
        [
            [0, 0, 1, 1],
            [0, 1, 1, 0],
            [1, 1, 0, 0],
        ],
        dtype=np.uint8,
    )

    encoded = encode_binary_mask(mask)
    decoded = decode_binary_mask(encoded)

    assert encoded.counts[0] == 2
    assert np.array_equal(decoded, mask)


def test_segment_current_uses_target_lock_and_scales_box_to_keyframe(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    perception = _FakePerception()
    segmenter = _FakeSegmenter(config)
    service = SegmentationService(
        perception,
        segmenter=segmenter,
        config=config,
    )

    result = service.segment_current_sync("person")

    assert result.status == SegmentationStatus.READY
    assert result.mode == SegmentationMode.SINGLE_FRAME
    assert result.track_id == 7
    assert result.prompt_box == BoundingBox(160, 40, 480, 340)
    assert segmenter.calls == [BoundingBox(80, 20, 240, 170)]
    assert result.mask is not None
    assert result.mask.area_pixels == 160 * 150
    assert result.mask.contours
    assert perception.published == result


def test_precise_tracking_is_explicit_and_can_be_stopped(tmp_path: Path) -> None:
    config = _config(tmp_path, tracking_fps=0.1)
    perception = _FakePerception()
    segmenter = _FakeSegmenter(config)
    service = SegmentationService(
        perception,
        segmenter=segmenter,
        config=config,
    )

    result = service.segment_current_sync("person", precise_tracking=True)
    stopped = service.stop_tracking()

    assert result.status == SegmentationStatus.READY
    assert result.mode == SegmentationMode.PRECISE_TRACKING
    assert result.tracking is True
    assert stopped.tracking is False
    assert "stopped" in stopped.answer


def test_missing_target_does_not_load_sam2(tmp_path: Path) -> None:
    config = _config(tmp_path)
    segmenter = _FakeSegmenter(config)
    service = SegmentationService(
        _FakePerception(),
        segmenter=segmenter,
        config=config,
    )

    result = service.segment_current_sync("spaceship")

    assert result.status == SegmentationStatus.NOT_FOUND
    assert segmenter.calls == []


def test_sam2_adapter_lazily_loads_backend_once(tmp_path: Path) -> None:
    config = _config(tmp_path)
    loads = 0
    backend = _FakeBackend()

    def load_backend(_config: Sam2Config):
        nonlocal loads
        loads += 1
        return backend

    adapter = Sam2ImageSegmenter(config, backend_loader=load_backend)
    adapter.segment(_keyframe(), BoundingBox(5, 5, 50, 50))
    adapter.segment(_keyframe(), BoundingBox(10, 10, 60, 60))

    assert loads == 1
    assert len(backend.calls) == 2


def test_segmentation_voice_intents_are_specific() -> None:
    segment = match_segmentation_intent("FRIDAY, segment the person in the camera.")
    track = match_segmentation_intent("FRIDAY, precisely track the person.")
    stop = match_segmentation_intent("FRIDAY, stop mask tracking.")
    clear = match_segmentation_intent("FRIDAY, clear the segmentation mask.")

    assert segment.action == SegmentationIntentAction.SEGMENT
    assert segment.target == "person"
    assert track.action == SegmentationIntentAction.TRACK
    assert track.target == "person"
    assert stop.action == SegmentationIntentAction.STOP
    assert clear.action == SegmentationIntentAction.CLEAR
    assert match_segmentation_intent("Tell me about image masks.").action == SegmentationIntentAction.NONE


def test_segmentation_routes_are_registered() -> None:
    paths = {route.path for route in api_router.routes}

    assert "/vision-segmentation/capabilities" in paths
    assert "/vision-segmentation/current" in paths
    assert "/vision-segmentation/box" in paths
    assert "/vision-segmentation/tracking/stop" in paths


def test_agent_routes_segmentation_before_general_llm() -> None:
    console = Mock()
    console.send_assistant_reply.return_value = {"ok": True}
    segmentation = SegmentationResult(
        status=SegmentationStatus.READY,
        answer="I segmented person with 93% mask confidence, Boss.",
        target_label="person",
        confidence=0.93,
    )
    with (
        patch(
            "friday.src.services.agent.service.get_agent_console_service",
            return_value=console,
        ),
        patch(
            "friday.src.services.agent.service.segment_camera_object",
            new=AsyncMock(return_value=segmentation),
        ) as segment,
        patch("friday.src.services.agent.service._build_llm_client") as build_llm,
    ):
        result = asyncio.run(
            chat(ConsoleChatRequest(message="FRIDAY, segment the person in the camera."))
        )

    assert result == {"ok": True}
    segment.assert_awaited_once_with("person", precise_tracking=False)
    build_llm.assert_not_called()
    content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
    assert content == segmentation.answer
