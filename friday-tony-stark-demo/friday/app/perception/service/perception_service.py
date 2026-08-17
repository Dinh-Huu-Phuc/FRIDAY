from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path

from friday.app.perception.camera import (
    CameraManager,
    get_camera_manager,
    get_default_camera_index,
)
from friday.app.perception.detection import (
    DetectionModelError,
    OnnxObjectDetector,
    SceneSnapshot,
    TargetLock,
    detection_enabled,
    get_detection_confidence,
    get_detection_model_path,
    get_detection_target_fps,
    get_target_lock_minimum_frames,
    target_lock_enabled,
)
from friday.app.perception.scene import SceneStateStore
from friday.app.perception.tracking import IoUTracker, TargetLocker
from friday.app.spatial.exceptions import CameraUnavailableError, VisionDependencyError
from friday.runtime.vision_runtime import get_vision_runtime_decision

LOGGER = logging.getLogger(__name__)
DetectorFactory = Callable[..., OnnxObjectDetector]


class PerceptionService:
    """Build a low-rate semantic scene state from the shared camera stream."""

    def __init__(
        self,
        manager: CameraManager | None = None,
        *,
        detector_factory: DetectorFactory = OnnxObjectDetector,
        state_store: SceneStateStore | None = None,
    ) -> None:
        self._manager = manager or get_camera_manager()
        self._detector_factory = detector_factory
        self._state_store = state_store or SceneStateStore()
        self._owner = f"object-detection:{id(self)}"
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._camera_index: int | None = None

    def start(self, camera_index: int | None = None) -> bool:
        if not detection_enabled():
            self._state_store.update(SceneSnapshot.idle(status="disabled"))
            return False

        target_index = (
            get_default_camera_index() if camera_index is None else camera_index
        )
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self._camera_index == target_index
            try:
                self._manager.acquire(self._owner, target_index)
            except (CameraUnavailableError, VisionDependencyError, ValueError) as exc:
                self._state_store.update(
                    SceneSnapshot.idle(status="error", error=str(exc))
                )
                return False

            self._camera_index = target_index
            self._stop_event.clear()
            self._state_store.update(SceneSnapshot.idle(status="loading"))
            self._thread = threading.Thread(
                target=self._run,
                name="friday-object-detection",
                daemon=True,
            )
            self._thread.start()
        return True

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._manager.release(self._owner)
        with self._lock:
            self._thread = None
            self._camera_index = None
        self._state_store.update(SceneSnapshot.idle())

    def snapshot(self) -> SceneSnapshot:
        return self._state_store.snapshot()

    def describe_scene(self) -> str:
        return self._state_store.describe()

    def _run(self) -> None:
        tracker = IoUTracker()
        locker = TargetLocker(
            minimum_stable_frames=get_target_lock_minimum_frames()
        )
        try:
            decision = get_vision_runtime_decision()
            model_path = get_detection_model_path()
            detector = self._create_detector(
                model_path,
                providers=decision.execution_providers,
                confidence=get_detection_confidence(),
            )
            detection_fps = get_detection_target_fps(decision.detector_fps)
            detection_interval = 1.0 / detection_fps
            last_camera_sequence = -1
            inference_times: deque[float] = deque(maxlen=12)

            while not self._stop_event.is_set():
                loop_started = time.monotonic()
                camera_status = self._manager.status()
                if camera_status.frame_sequence == last_camera_sequence:
                    self._stop_event.wait(0.01)
                    continue
                frame = self._manager.latest_frame(copy=True, wait_timeout=0.1)
                if frame is None or not hasattr(frame, "shape"):
                    self._stop_event.wait(0.02)
                    continue

                last_camera_sequence = camera_status.frame_sequence
                detections = detector.detect(frame)
                objects = tracker.update(detections)
                height, width = frame.shape[:2]
                target_lock = (
                    locker.update(
                        objects,
                        frame_width=width,
                        frame_height=height,
                    )
                    if target_lock_enabled()
                    else TargetLock()
                )
                inference_times.append(time.monotonic())
                measured_fps = self._measure_fps(inference_times)
                self._state_store.update(
                    SceneSnapshot(
                        sequence=camera_status.frame_sequence,
                        captured_at=time.time(),
                        frame_width=width,
                        frame_height=height,
                        objects=objects,
                        target_lock=target_lock,
                        inference_ms=detector.last_inference_ms,
                        detector_fps=measured_fps,
                        status="ready",
                        model_name=detector.name,
                    )
                )
                remaining = detection_interval - (time.monotonic() - loop_started)
                if remaining > 0:
                    self._stop_event.wait(remaining)
        except DetectionModelError as exc:
            LOGGER.warning("Camera detector unavailable: %s", exc)
            self._state_store.update(
                SceneSnapshot.idle(status="error", error=str(exc))
            )
        except Exception as exc:
            LOGGER.exception("Camera perception worker stopped unexpectedly")
            self._state_store.update(
                SceneSnapshot.idle(
                    status="error",
                    error=f"camera analysis stopped: {exc}",
                )
            )
        finally:
            self._manager.release(self._owner)

    def _create_detector(
        self,
        model_path: Path,
        *,
        providers: tuple[str, ...],
        confidence: float,
    ) -> OnnxObjectDetector:
        return self._detector_factory(
            model_path,
            providers=providers,
            confidence=confidence,
        )

    @staticmethod
    def _measure_fps(inference_times: deque[float]) -> float:
        if len(inference_times) < 2:
            return 0.0
        elapsed = inference_times[-1] - inference_times[0]
        return (len(inference_times) - 1) / elapsed if elapsed > 0 else 0.0


_PERCEPTION_SERVICE = PerceptionService()


def get_perception_service() -> PerceptionService:
    return _PERCEPTION_SERVICE
