from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from time import perf_counter
from typing import Any

from friday.app.perception.detection import SceneSnapshot
from friday.app.perception.reasoning.confidence_policy import (
    KeyframePolicy,
    latest_scene_event_id,
    scene_signature,
)
from friday.app.perception.reasoning.schemas import VisionKeyframe
from friday.app.perception.scene import TemporalSceneSnapshot
from friday.app.perception.scene.summarizer import summarize_scene

FrameEncoder = Callable[[Any, int, int], tuple[bytes, int, int]]


class KeyframeStore:
    """Keep one compressed reasoning frame in memory, never on disk."""

    def __init__(
        self,
        policy: KeyframePolicy | None = None,
        *,
        encoder: FrameEncoder | None = None,
    ) -> None:
        self._policy = policy or KeyframePolicy()
        self._encoder = encoder or _encode_jpeg
        self._lock = RLock()
        self._latest: VisionKeyframe | None = None

    def consider(
        self,
        frame: Any,
        snapshot: SceneSnapshot,
        temporal: TemporalSceneSnapshot,
        *,
        force: bool = False,
        timings: dict[str, float] | None = None,
    ) -> VisionKeyframe | None:
        with self._lock:
            reason = self._policy.select_reason(
                snapshot,
                temporal,
                self._latest,
                force=force,
            )
            if reason is None:
                return None
            started = perf_counter()
            jpeg_bytes, width, height = self._encoder(
                frame,
                self._policy.config.maximum_image_edge,
                self._policy.config.jpeg_quality,
            )
            if timings is not None:
                timings["jpeg_encoding_ms"] = (perf_counter() - started) * 1000
            started = perf_counter()
            self._latest = VisionKeyframe(
                sequence=snapshot.sequence,
                captured_at=snapshot.captured_at,
                frame_width=width,
                frame_height=height,
                reason=reason,
                scene_summary=summarize_scene(snapshot, temporal),
                scene_signature=scene_signature(temporal),
                latest_event_id=latest_scene_event_id(temporal),
                jpeg_bytes=jpeg_bytes,
            )
            if timings is not None:
                timings["context_build_ms"] = (
                    timings.get("context_build_ms", 0.0)
                    + (perf_counter() - started) * 1000
                )
            return self._latest

    def latest(self) -> VisionKeyframe | None:
        with self._lock:
            return self._latest

    def reset(self) -> None:
        with self._lock:
            self._latest = None


def _encode_jpeg(
    frame: Any,
    maximum_edge: int,
    quality: int,
) -> tuple[bytes, int, int]:
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("opencv-python is required for camera keyframes") from exc

    if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 2:
        raise ValueError("Camera keyframe is not a valid image")
    height, width = (int(value) for value in frame.shape[:2])
    if width <= 0 or height <= 0:
        raise ValueError("Camera keyframe dimensions must be positive")

    scale = min(1.0, maximum_edge / max(width, height))
    encoded_frame = frame
    if scale < 1.0:
        width = max(1, round(width * scale))
        height = max(1, round(height * scale))
        encoded_frame = cv2.resize(
            frame,
            (width, height),
            interpolation=cv2.INTER_AREA,
        )
    ok, buffer = cv2.imencode(
        ".jpg",
        encoded_frame,
        [cv2.IMWRITE_JPEG_QUALITY, quality],
    )
    if not ok:
        raise RuntimeError("OpenCV could not encode the camera keyframe")
    return bytes(buffer), width, height
