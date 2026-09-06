from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace
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
from friday.app.perception.detection.grounding import (
    GroundingResult,
    grounding_result_ttl,
)
from friday.app.perception.reasoning import KeyframeStore, VisionKeyframe
from friday.app.perception.relation import (
    HandObservationProvider,
    get_hand_sample_fps,
    relations_enabled,
)
from friday.app.perception.scene import (
    HandObservation,
    SceneStateStore,
    TemporalSceneSnapshot,
)
from friday.app.perception.segmentation.config import segmentation_result_ttl
from friday.app.perception.segmentation.schemas import SegmentationResult
from friday.app.perception.tracking import (
    ByteTracker,
    TargetLocker,
    TrackingDependencyError,
)
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
        keyframe_store: KeyframeStore | None = None,
    ) -> None:
        self._manager = manager or get_camera_manager()
        self._detector_factory = detector_factory
        self._state_store = state_store or SceneStateStore()
        self._keyframes = keyframe_store or KeyframeStore()
        self._owner = f"object-detection:{id(self)}"
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._camera_index: int | None = None
        self._grounding_result: GroundingResult | None = None
        self._segmentation_result: SegmentationResult | None = None

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
            self._keyframes.reset()
            self._grounding_result = None
            self._segmentation_result = None
            self._state_store.update(SceneSnapshot.idle(status="loading"))
            self._thread = threading.Thread(
                target=self._run,
                name="friday-object-detection",
                daemon=True,
            )
            self._thread.start()
        return True

    def stop(self) -> None:
        from friday.app.perception.segmentation.service import (
            stop_segmentation_for_perception,
        )

        stop_segmentation_for_perception(self)
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._manager.release(self._owner)
        with self._lock:
            self._thread = None
            self._camera_index = None
        self._keyframes.reset()
        with self._lock:
            self._grounding_result = None
            self._segmentation_result = None
        self._state_store.update(SceneSnapshot.idle())

    def snapshot(self) -> SceneSnapshot:
        return self._state_store.snapshot()

    def describe_scene(self) -> str:
        return self._state_store.describe()

    def temporal_snapshot(self) -> TemporalSceneSnapshot:
        return self._state_store.temporal_snapshot()

    def latest_keyframe(self) -> VisionKeyframe | None:
        return self._keyframes.latest()

    def set_grounding_result(self, result: GroundingResult) -> None:
        with self._lock:
            self._grounding_result = result

    def grounding_result(self) -> GroundingResult | None:
        with self._lock:
            result = self._grounding_result
        if result is None or not result.is_fresh(grounding_result_ttl()):
            return None
        return result

    def set_segmentation_result(self, result: SegmentationResult | None) -> None:
        with self._lock:
            self._segmentation_result = result

    def segmentation_result(self) -> SegmentationResult | None:
        with self._lock:
            result = self._segmentation_result
        if result is None or not result.is_fresh(segmentation_result_ttl()):
            return None
        return result

    def capture_keyframe(self) -> VisionKeyframe | None:
        snapshot = self._state_store.snapshot()
        if snapshot.status != "ready":
            return None
        frame = self._manager.latest_frame(copy=True, wait_timeout=0.15)
        if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 2:
            return self._keyframes.latest()
        frame_height, frame_width = frame.shape[:2]
        current = self._manager.status()
        snapshot = replace(
            snapshot,
            sequence=current.frame_sequence,
            captured_at=time.time(),
            frame_width=int(frame_width),
            frame_height=int(frame_height),
        )
        return self._keyframes.consider(
            frame,
            snapshot,
            self._state_store.temporal_snapshot(),
            force=True,
        )

    def _run(self) -> None:
        hand_observer: HandObservationProvider | None = None
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
            tracker_fps = max(detection_fps, decision.tracker_fps)
            tracker = ByteTracker.from_environment(frame_rate=tracker_fps)
            detection_interval = 1.0 / detection_fps
            tracking_interval = 1.0 / tracker_fps
            hand_interval = 1.0 / get_hand_sample_fps()
            if relations_enabled():
                hand_observer = HandObservationProvider()
            last_camera_sequence = -1
            inference_times: deque[float] = deque(maxlen=12)
            tracker_times: deque[float] = deque(maxlen=max(12, tracker_fps))
            frame_width = 0
            frame_height = 0
            objects = ()
            target_lock = TargetLock()
            next_detection_at = time.monotonic()
            next_prediction_at = next_detection_at
            next_hand_sample_at = next_detection_at

            def publish(
                sequence: int,
                *,
                detector_sampled: bool,
                hand_observations: tuple[HandObservation, ...] | None = None,
            ) -> SceneSnapshot:
                snapshot = SceneSnapshot(
                    sequence=sequence,
                    captured_at=time.time(),
                    frame_width=frame_width,
                    frame_height=frame_height,
                    objects=objects,
                    target_lock=target_lock,
                    inference_ms=detector.last_inference_ms,
                    detector_fps=self._measure_fps(inference_times),
                    tracker_fps=self._measure_fps(tracker_times),
                    detector_sampled=detector_sampled,
                    status="ready",
                    model_name=detector.name,
                )
                self._state_store.update(
                    snapshot,
                    hand_observations=hand_observations,
                )
                return snapshot

            while not self._stop_event.is_set():
                now = time.monotonic()
                camera_status = self._manager.status()
                detection_due = now >= next_detection_at
                has_new_frame = camera_status.frame_sequence != last_camera_sequence
                if detection_due and has_new_frame:
                    frame = self._manager.latest_frame(copy=True, wait_timeout=0.1)
                    if frame is None or not hasattr(frame, "shape"):
                        self._stop_event.wait(0.01)
                        continue

                    last_camera_sequence = camera_status.frame_sequence
                    detections = detector.detect(frame)
                    tracked_at = time.monotonic()
                    objects = tracker.update(detections, timestamp=tracked_at)
                    frame_height, frame_width = frame.shape[:2]
                    target_lock = (
                        locker.update(
                            objects,
                            frame_width=frame_width,
                            frame_height=frame_height,
                        )
                        if target_lock_enabled()
                        else TargetLock()
                    )
                    inference_times.append(tracked_at)
                    tracker_times.append(tracked_at)
                    hand_observations = None
                    if hand_observer is not None and tracked_at >= next_hand_sample_at:
                        try:
                            hand_observations = hand_observer.detect(frame)
                        # This optional branch must never stop core detection.
                        except Exception as exc:  # noqa: BLE001
                            LOGGER.warning(
                                "Camera hand-relation branch disabled: %s",
                                exc,
                            )
                            hand_observer.close()
                            hand_observer = None
                        next_hand_sample_at = time.monotonic() + hand_interval
                    next_detection_at = tracked_at + detection_interval
                    next_prediction_at = tracked_at + tracking_interval
                    scene_snapshot = publish(
                        camera_status.frame_sequence,
                        detector_sampled=True,
                        hand_observations=hand_observations,
                    )
                    self._keyframes.consider(
                        frame,
                        scene_snapshot,
                        self._state_store.temporal_snapshot(),
                    )
                    continue

                if now >= next_prediction_at and frame_width > 0 and frame_height > 0:
                    objects = tracker.predict(timestamp=now)
                    target_lock = (
                        locker.predict(objects)
                        if target_lock_enabled()
                        else TargetLock()
                    )
                    tracker_times.append(now)
                    next_prediction_at = now + tracking_interval
                    publish(camera_status.frame_sequence, detector_sampled=False)
                    continue

                if detection_due:
                    self._stop_event.wait(0.005)
                    continue

                wait_until = min(next_detection_at, next_prediction_at)
                self._stop_event.wait(min(0.02, max(0.001, wait_until - now)))
        except (DetectionModelError, TrackingDependencyError) as exc:
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
            if hand_observer is not None:
                hand_observer.close()
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
