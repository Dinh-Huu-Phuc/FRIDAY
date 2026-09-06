from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING, Protocol

from friday.app.perception.detection.schemas import (
    BoundingBox,
    SceneSnapshot,
    TrackedObject,
)
from friday.app.perception.reasoning.schemas import VisionKeyframe
from friday.app.perception.segmentation.config import Sam2Config
from friday.app.perception.segmentation.mask_codec import build_segmentation_mask
from friday.app.perception.segmentation.sam2_adapter import (
    Sam2ImageSegmenter,
    Sam2ModelError,
    Sam2Prediction,
)
from friday.app.perception.segmentation.schemas import (
    SegmentationCapabilities,
    SegmentationMode,
    SegmentationResult,
    SegmentationStatus,
)

if TYPE_CHECKING:
    from friday.app.perception.service import PerceptionService


class Segmenter(Protocol):
    config: Sam2Config
    model: str
    device: str

    def capabilities(self) -> SegmentationCapabilities: ...

    def segment(
        self,
        keyframe: VisionKeyframe,
        box: BoundingBox,
    ) -> Sam2Prediction: ...

    def unload(self) -> None: ...


class SegmentationService:
    """Run SAM 2 on demand and refresh masks away from the live detector loop."""

    def __init__(
        self,
        perception_service: PerceptionService,
        *,
        segmenter: Segmenter | None = None,
        config: Sam2Config | None = None,
    ) -> None:
        self._perception = perception_service
        self._config = config or Sam2Config.from_environment()
        self._segmenter = segmenter or Sam2ImageSegmenter(self._config)
        self._state_lock = threading.RLock()
        self._inference_lock = threading.Lock()
        self._tracking_stop = threading.Event()
        self._tracking_thread: threading.Thread | None = None
        self._tracking_generation = 0
        self._last_result: SegmentationResult | None = None

    def capabilities(self) -> SegmentationCapabilities:
        return self._segmenter.capabilities()

    def current(self) -> SegmentationResult:
        with self._state_lock:
            result = self._last_result
        return result or SegmentationResult.idle()

    async def segment_current(
        self,
        target: str = "",
        *,
        precise_tracking: bool = False,
    ) -> SegmentationResult:
        return await asyncio.to_thread(
            self.segment_current_sync,
            target,
            precise_tracking=precise_tracking,
        )

    def segment_current_sync(
        self,
        target: str = "",
        *,
        precise_tracking: bool = False,
    ) -> SegmentationResult:
        snapshot = self._perception.snapshot()
        cleaned_target = _normalize_target(target)
        if snapshot.status != "ready":
            return self._publish(
                SegmentationResult(
                    status=SegmentationStatus.UNAVAILABLE,
                    target_label=cleaned_target,
                    answer="Open the Camera Window first so I can segment that object, Boss.",
                    error=f"camera scene status is {snapshot.status}",
                )
            )
        selected = _select_target(snapshot, cleaned_target)
        if selected is None:
            description = cleaned_target or "a tracked object"
            return self._publish(
                SegmentationResult(
                    status=SegmentationStatus.NOT_FOUND,
                    target_label=cleaned_target,
                    answer=f"I could not find {description} to segment in the camera view, Boss.",
                    error="no matching detector or target-lock box",
                )
            )
        label, track_id, source_box = selected
        result = self._segment_box_from_snapshot(
            snapshot,
            source_box,
            target_label=label,
            track_id=track_id,
            mode=(
                SegmentationMode.PRECISE_TRACKING
                if precise_tracking
                else SegmentationMode.SINGLE_FRAME
            ),
            tracking=precise_tracking and track_id is not None,
        )
        if precise_tracking and result.ok and track_id is not None:
            self._start_tracking(track_id, label, source_box)
        return result

    async def segment_box(
        self,
        box: BoundingBox,
        *,
        target_label: str = "selected region",
        precise_tracking: bool = False,
    ) -> SegmentationResult:
        return await asyncio.to_thread(
            self.segment_box_sync,
            box,
            target_label=target_label,
            precise_tracking=precise_tracking,
        )

    def segment_box_sync(
        self,
        box: BoundingBox,
        *,
        target_label: str = "selected region",
        precise_tracking: bool = False,
    ) -> SegmentationResult:
        snapshot = self._perception.snapshot()
        if snapshot.status != "ready":
            return self._publish(
                SegmentationResult(
                    status=SegmentationStatus.UNAVAILABLE,
                    target_label=_normalize_target(target_label),
                    answer="Open the Camera Window first so I can segment that region, Boss.",
                    error=f"camera scene status is {snapshot.status}",
                )
            )
        clipped = _clip_box(box, snapshot.frame_width, snapshot.frame_height)
        if clipped is None:
            return self._publish(
                SegmentationResult(
                    status=SegmentationStatus.ERROR,
                    target_label=_normalize_target(target_label),
                    answer="That segmentation box is outside the camera frame, Boss.",
                    error="invalid prompt box",
                )
            )
        track = _match_track(snapshot, clipped)
        result = self._segment_box_from_snapshot(
            snapshot,
            clipped,
            target_label=_normalize_target(target_label) or "selected region",
            track_id=track.track_id if track else None,
            mode=(
                SegmentationMode.PRECISE_TRACKING
                if precise_tracking
                else SegmentationMode.SINGLE_FRAME
            ),
            tracking=precise_tracking and track is not None,
        )
        if precise_tracking and result.ok and track is not None:
            self._start_tracking(track.track_id, track.label, clipped)
        return result

    def stop_tracking(self) -> SegmentationResult:
        self._tracking_stop.set()
        with self._state_lock:
            self._tracking_generation += 1
            thread = self._tracking_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.5)
        with self._state_lock:
            self._tracking_thread = None
            result = self._last_result
        if result is None:
            return SegmentationResult.idle("Precise mask tracking is already stopped, Boss.")
        stopped = result.model_copy(
            update={
                "tracking": False,
                "answer": "Precise mask tracking is stopped, Boss.",
                "completed_at": time.monotonic(),
            }
        )
        return self._publish(stopped)

    def clear(self, *, unload_model: bool = False) -> SegmentationResult:
        self.stop_tracking()
        with self._state_lock:
            self._last_result = None
        publisher = getattr(self._perception, "set_segmentation_result", None)
        if callable(publisher):
            publisher(None)
        if unload_model:
            self._segmenter.unload()
        return SegmentationResult.idle("The segmentation mask is cleared, Boss.")

    def _segment_box_from_snapshot(
        self,
        snapshot: SceneSnapshot,
        source_box: BoundingBox,
        *,
        target_label: str,
        track_id: int | None,
        mode: SegmentationMode,
        tracking: bool = False,
        publish: bool = True,
    ) -> SegmentationResult:
        keyframe = self._perception.capture_keyframe()
        if keyframe is None or not keyframe.jpeg_bytes:
            result = SegmentationResult(
                status=SegmentationStatus.UNAVAILABLE,
                target_label=target_label,
                track_id=track_id,
                prompt_box=source_box,
                mode=mode,
                answer="I could not capture a camera frame for segmentation, Boss.",
                error="no camera keyframe is available",
            )
            return self._publish(result) if publish else result
        prompt_box = _scale_box(
            source_box,
            source_width=snapshot.frame_width,
            source_height=snapshot.frame_height,
            target_width=keyframe.frame_width,
            target_height=keyframe.frame_height,
        )
        started_at = time.perf_counter()
        try:
            with self._inference_lock:
                prediction = self._segmenter.segment(keyframe, prompt_box)
            mask = build_segmentation_mask(prediction.mask)
        except (Sam2ModelError, ValueError) as exc:
            result = SegmentationResult(
                status=SegmentationStatus.UNAVAILABLE,
                target_label=target_label,
                track_id=track_id,
                prompt_box=source_box,
                mode=mode,
                answer=(
                    "I could not start local SAM 2 segmentation. "
                    "Its package or tiny checkpoint needs attention, Boss."
                ),
                model=self._segmenter.model,
                device=self._segmenter.device,
                keyframe_sequence=keyframe.sequence,
                latency_ms=(time.perf_counter() - started_at) * 1000,
                error=str(exc),
            )
            return self._publish(result) if publish else result
        tracking_text = (
            " and started precise mask tracking"
            if mode == SegmentationMode.PRECISE_TRACKING
            else ""
        )
        result = SegmentationResult(
            status=SegmentationStatus.READY,
            target_label=target_label,
            track_id=track_id,
            prompt_box=source_box,
            mask=mask,
            confidence=prediction.confidence,
            mode=mode,
            tracking=tracking,
            model=prediction.model,
            device=prediction.device,
            keyframe_sequence=keyframe.sequence,
            latency_ms=(time.perf_counter() - started_at) * 1000,
            answer=(
                f"I segmented {target_label}{tracking_text} with "
                f"{prediction.confidence:.0%} mask confidence, Boss."
            ),
        )
        return self._publish(result) if publish else result

    def _start_tracking(
        self,
        track_id: int,
        target_label: str,
        source_box: BoundingBox,
    ) -> None:
        self._tracking_stop.set()
        with self._state_lock:
            self._tracking_generation += 1
            generation = self._tracking_generation
            previous = self._tracking_thread
        if previous is not None and previous is not threading.current_thread():
            previous.join(timeout=0.5)
        with self._state_lock:
            self._tracking_stop.clear()
            thread = threading.Thread(
                target=self._tracking_loop,
                args=(track_id, target_label, source_box, generation),
                name="friday-sam2-mask-tracking",
                daemon=True,
            )
            self._tracking_thread = thread
        thread.start()

    def _tracking_loop(
        self,
        track_id: int,
        target_label: str,
        last_box: BoundingBox,
        generation: int,
    ) -> None:
        interval = 1.0 / self._config.tracking_fps
        misses = 0
        while not self._tracking_stop.wait(interval):
            snapshot = self._perception.snapshot()
            if snapshot.status != "ready":
                misses += 1
                if misses >= self._config.tracking_max_misses:
                    break
                continue
            target = next(
                (item for item in snapshot.objects if item.track_id == track_id),
                None,
            )
            if target is None:
                candidates = [
                    item
                    for item in snapshot.objects
                    if item.label.casefold() == target_label.casefold()
                    and item.box.iou(last_box) >= 0.1
                ]
                target = max(
                    candidates,
                    key=lambda item: item.box.iou(last_box),
                    default=None,
                )
            if target is None:
                misses += 1
                if misses >= self._config.tracking_max_misses:
                    break
                continue
            misses = 0
            track_id = target.track_id
            last_box = target.box
            result = self._segment_box_from_snapshot(
                snapshot,
                target.box,
                target_label=target.label,
                track_id=target.track_id,
                mode=SegmentationMode.PRECISE_TRACKING,
                tracking=True,
                publish=False,
            )
            with self._state_lock:
                current_generation = self._tracking_generation
            if self._tracking_stop.is_set() or generation != current_generation:
                break
            self._publish(result)
        with self._state_lock:
            result = self._last_result
            if generation == self._tracking_generation:
                self._tracking_thread = None
        if (
            result is not None
            and result.tracking
            and generation == self._tracking_generation
        ):
            self._publish(
                result.model_copy(
                    update={"tracking": False, "completed_at": time.monotonic()}
                )
            )

    def _publish(self, result: SegmentationResult) -> SegmentationResult:
        with self._state_lock:
            self._last_result = result
        publisher = getattr(self._perception, "set_segmentation_result", None)
        if callable(publisher):
            publisher(result)
        return result


def _normalize_target(value: str) -> str:
    target = " ".join(str(value or "").strip().split())[:100]
    lowered = target.casefold()
    for prefix in ("the ", "a ", "an ", "my "):
        if lowered.startswith(prefix):
            return target[len(prefix) :]
    return target


def _select_target(
    snapshot: SceneSnapshot,
    target: str,
) -> tuple[str, int | None, BoundingBox] | None:
    if target:
        normalized = target.casefold().removesuffix("s")
        matches = [
            item
            for item in snapshot.objects
            if normalized in {
                item.label.casefold(),
                item.label.casefold().removesuffix("s"),
            }
            or normalized in item.label.casefold()
            or item.label.casefold() in normalized
        ]
        if not matches:
            return None
        selected = max(matches, key=lambda item: (item.confidence, item.box.area))
        return selected.label, selected.track_id, selected.box
    locked = snapshot.target_lock.target
    if locked is not None:
        return locked.label, locked.track_id, locked.box
    if not snapshot.objects:
        return None
    selected = max(snapshot.objects, key=lambda item: (item.confidence, item.box.area))
    return selected.label, selected.track_id, selected.box


def _match_track(snapshot: SceneSnapshot, box: BoundingBox) -> TrackedObject | None:
    match = max(snapshot.objects, key=lambda item: item.box.iou(box), default=None)
    if match is None or match.box.iou(box) < 0.1:
        return None
    return match


def _clip_box(box: BoundingBox, width: int, height: int) -> BoundingBox | None:
    if width <= 0 or height <= 0:
        return None
    clipped = BoundingBox(
        x1=min(width - 1, max(0, int(box.x1))),
        y1=min(height - 1, max(0, int(box.y1))),
        x2=min(width, max(1, int(box.x2))),
        y2=min(height, max(1, int(box.y2))),
    )
    return clipped if clipped.width > 0 and clipped.height > 0 else None


def _scale_box(
    box: BoundingBox,
    *,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> BoundingBox:
    scale_x = target_width / max(1, source_width)
    scale_y = target_height / max(1, source_height)
    scaled = BoundingBox(
        x1=round(box.x1 * scale_x),
        y1=round(box.y1 * scale_y),
        x2=round(box.x2 * scale_x),
        y2=round(box.y2 * scale_y),
    )
    return _clip_box(scaled, target_width, target_height) or BoundingBox(
        0,
        0,
        max(1, target_width),
        max(1, target_height),
    )


_SERVICE_LOCK = threading.Lock()
_SEGMENTATION_SERVICE: SegmentationService | None = None


def get_segmentation_service() -> SegmentationService:
    global _SEGMENTATION_SERVICE
    with _SERVICE_LOCK:
        if _SEGMENTATION_SERVICE is None:
            from friday.app.perception.service import get_perception_service

            _SEGMENTATION_SERVICE = SegmentationService(get_perception_service())
        return _SEGMENTATION_SERVICE


def stop_segmentation_for_perception(perception_service: object) -> None:
    with _SERVICE_LOCK:
        service = _SEGMENTATION_SERVICE
    if service is not None and service._perception is perception_service:
        service.clear()


async def segment_camera_object(
    target: str = "",
    *,
    precise_tracking: bool = False,
) -> SegmentationResult:
    return await get_segmentation_service().segment_current(
        target,
        precise_tracking=precise_tracking,
    )
