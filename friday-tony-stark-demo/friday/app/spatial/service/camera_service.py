from __future__ import annotations

import threading
from typing import Any

from friday.app.spatial.exceptions import CameraUnavailableError, VisionDependencyError


class CameraService:
    def __init__(self) -> None:
        self._capture: Any | None = None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            return bool(self._capture is not None and self._capture.isOpened())

    def open(self, camera_index: int = 0) -> None:
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise VisionDependencyError("opencv-python is required for spatial camera access.") from exc

        with self._lock:
            if self._capture is not None and self._capture.isOpened():
                return
            capture = cv2.VideoCapture(camera_index)
            if not capture.isOpened():
                capture.release()
                raise CameraUnavailableError(f"Unable to open webcam at index {camera_index}.")
            self._capture = capture

    def read_frame(self):
        with self._lock:
            if self._capture is None or not self._capture.isOpened():
                return None
            ok, frame = self._capture.read()
            return frame if ok else None

    def stop(self) -> None:
        with self._lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None
