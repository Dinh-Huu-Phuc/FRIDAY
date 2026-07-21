from __future__ import annotations

import threading

from friday.app.spatial.config import get_spatial_config
from friday.core.schemas.spatial_entities import SpatialSessionState


class SpatialSession:
    def __init__(self) -> None:
        config = get_spatial_config()
        self._state = SpatialSessionState(
            session_id=config.session_id,
            enabled=False,
            mode=config.mode,
            camera_index=config.camera_index,
            fps=config.fps,
        )
        self._lock = threading.Lock()

    def start(self, *, mode: str | None = None, camera_index: int | None = None) -> SpatialSessionState:
        with self._lock:
            if mode:
                self._state.mode = mode
            if camera_index is not None:
                self._state.camera_index = camera_index
            self._state.enabled = True
            self._state.last_error = None
            return self.snapshot()

    def stop(self) -> SpatialSessionState:
        with self._lock:
            self._state.enabled = False
            return self.snapshot()

    def set_mode(self, mode: str) -> SpatialSessionState:
        with self._lock:
            self._state.mode = mode
            return self.snapshot()

    def record_gesture(self, gesture: str) -> None:
        with self._lock:
            self._state.last_gesture = gesture

    def record_error(self, error: str | None) -> None:
        with self._lock:
            self._state.last_error = error

    def snapshot(self) -> SpatialSessionState:
        return self._state.model_copy()
