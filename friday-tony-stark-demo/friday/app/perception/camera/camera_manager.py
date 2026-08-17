from __future__ import annotations

import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from friday.app.perception.camera.settings import get_default_camera_index
from friday.app.spatial.exceptions import CameraUnavailableError, VisionDependencyError

CaptureFactory = Callable[[int], Any]


@dataclass(frozen=True, slots=True)
class CameraStatus:
    is_open: bool
    camera_index: int | None
    owners: tuple[str, ...]
    frame_sequence: int
    capture_fps: float = 0.0
    frame_width: int = 0
    frame_height: int = 0
    last_error: str = ""


def _default_capture_factory(camera_index: int):
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise VisionDependencyError(
            "opencv-python is required for camera access."
        ) from exc

    if os.name == "nt":
        capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if capture.isOpened():
            return capture
        capture.release()
    return cv2.VideoCapture(camera_index)


class CameraManager:
    """Own one physical camera and share its latest frame across consumers."""

    def __init__(self, capture_factory: CaptureFactory = _default_capture_factory) -> None:
        self._capture_factory = capture_factory
        self._condition = threading.Condition(threading.RLock())
        self._capture: Any | None = None
        self._camera_index: int | None = None
        self._owners: set[str] = set()
        self._latest_frame: Any | None = None
        self._frame_sequence = 0
        self._capture_times: deque[float] = deque(maxlen=90)
        self._capture_fps = 0.0
        self._frame_width = 0
        self._frame_height = 0
        self._last_error = ""
        self._stop_event = threading.Event()
        self._capture_thread: threading.Thread | None = None

    def acquire(self, owner: str, camera_index: int | None = None) -> CameraStatus:
        normalized_owner = str(owner or "").strip()
        if not normalized_owner:
            raise ValueError("Camera owner must be a non-empty identifier.")
        target_index = get_default_camera_index() if camera_index is None else camera_index
        if target_index < 0:
            raise ValueError("Camera index must be zero or greater.")

        with self._condition:
            if self._capture is not None:
                if self._camera_index != target_index:
                    raise CameraUnavailableError(
                        f"Camera {self._camera_index} is already active; cannot switch to {target_index}."
                    )
                self._owners.add(normalized_owner)
                return self._status_locked()

            capture = self._capture_factory(target_index)
            if capture is None or not capture.isOpened():
                if capture is not None:
                    capture.release()
                raise CameraUnavailableError(
                    f"Unable to open webcam at index {target_index}."
                )
            self._capture = capture
            self._camera_index = target_index
            self._owners.add(normalized_owner)
            self._latest_frame = None
            self._capture_times.clear()
            self._capture_fps = 0.0
            self._frame_width = 0
            self._frame_height = 0
            self._last_error = ""
            self._stop_event.clear()
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                args=(capture,),
                name="friday-camera-capture",
                daemon=True,
            )
            self._capture_thread.start()
            return self._status_locked()

    def release(self, owner: str) -> CameraStatus:
        thread: threading.Thread | None = None
        capture: Any | None = None
        with self._condition:
            self._owners.discard(str(owner or "").strip())
            if self._owners or self._capture is None:
                return self._status_locked()
            self._stop_event.set()
            thread = self._capture_thread
            capture = self._capture
            self._capture = None
            self._capture_thread = None
            self._camera_index = None
            self._condition.notify_all()

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        if capture is not None:
            capture.release()
        with self._condition:
            self._latest_frame = None
            self._capture_times.clear()
            self._capture_fps = 0.0
            self._frame_width = 0
            self._frame_height = 0
            return self._status_locked()

    def latest_frame(self, *, copy: bool = True, wait_timeout: float = 0.0):
        deadline = time.monotonic() + max(0.0, wait_timeout)
        with self._condition:
            while self._latest_frame is None and self._capture is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(timeout=remaining)
            frame = self._latest_frame
            if frame is None:
                return None
            return frame.copy() if copy and hasattr(frame, "copy") else frame

    def status(self) -> CameraStatus:
        with self._condition:
            return self._status_locked()

    def shutdown(self) -> None:
        with self._condition:
            owners = tuple(self._owners)
        for owner in owners:
            self.release(owner)

    def _capture_loop(self, capture: Any) -> None:
        while not self._stop_event.is_set():
            ok, frame = capture.read()
            with self._condition:
                if capture is not self._capture:
                    return
                if ok and frame is not None:
                    captured_at = time.monotonic()
                    self._latest_frame = frame
                    self._frame_sequence += 1
                    self._capture_times.append(captured_at)
                    self._capture_fps = self._measure_capture_fps()
                    if hasattr(frame, "shape") and len(frame.shape) >= 2:
                        self._frame_height, self._frame_width = frame.shape[:2]
                    self._last_error = ""
                    self._condition.notify_all()
                else:
                    self._last_error = "Camera returned an empty frame."
            if not ok:
                self._stop_event.wait(0.05)

    def _status_locked(self) -> CameraStatus:
        return CameraStatus(
            is_open=self._capture is not None,
            camera_index=self._camera_index,
            owners=tuple(sorted(self._owners)),
            frame_sequence=self._frame_sequence,
            capture_fps=self._capture_fps,
            frame_width=self._frame_width,
            frame_height=self._frame_height,
            last_error=self._last_error,
        )

    def _measure_capture_fps(self) -> float:
        if len(self._capture_times) < 2:
            return 0.0
        elapsed = self._capture_times[-1] - self._capture_times[0]
        return (len(self._capture_times) - 1) / elapsed if elapsed > 0 else 0.0


_CAMERA_MANAGER = CameraManager()


def get_camera_manager() -> CameraManager:
    return _CAMERA_MANAGER
