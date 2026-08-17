from __future__ import annotations

from friday.app.perception.camera import CameraManager, get_camera_manager


class CameraService:
    def __init__(self, manager: CameraManager | None = None) -> None:
        self._manager = manager or get_camera_manager()
        self._owner = f"spatial:{id(self)}"

    @property
    def is_open(self) -> bool:
        return self._owner in self._manager.status().owners

    def open(self, camera_index: int | None = None) -> None:
        self._manager.acquire(self._owner, camera_index)

    def read_frame(self):
        return self._manager.latest_frame(copy=True, wait_timeout=0.2)

    def stop(self) -> None:
        self._manager.release(self._owner)
