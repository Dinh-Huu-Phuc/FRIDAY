from __future__ import annotations

import time

from friday.app.perception.camera import CameraManager


class FakeFrame:
    def __init__(self, value: int) -> None:
        self.value = value
        self.shape = (480, 640, 3)

    def copy(self) -> FakeFrame:
        return FakeFrame(self.value)


class FakeCapture:
    def __init__(self, camera_index: int) -> None:
        self.camera_index = camera_index
        self.opened = True
        self.released = False
        self.frames = 0

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        time.sleep(0.002)
        self.frames += 1
        return True, FakeFrame(self.frames)

    def release(self) -> None:
        self.opened = False
        self.released = True


def test_camera_manager_shares_capture_until_last_owner_releases() -> None:
    captures: list[FakeCapture] = []

    def factory(index: int) -> FakeCapture:
        capture = FakeCapture(index)
        captures.append(capture)
        return capture

    manager = CameraManager(factory)
    manager.acquire("spatial", 0)
    manager.acquire("camera-window", 0)

    frame = manager.latest_frame(wait_timeout=0.2)
    assert isinstance(frame, FakeFrame)
    deadline = time.monotonic() + 0.2
    while manager.status().capture_fps <= 0 and time.monotonic() < deadline:
        time.sleep(0.005)
    assert len(captures) == 1
    assert set(manager.status().owners) == {"camera-window", "spatial"}
    assert manager.status().capture_fps > 0
    assert manager.status().frame_width == 640
    assert manager.status().frame_height == 480

    manager.release("camera-window")
    assert manager.status().is_open is True
    assert captures[0].released is False

    manager.release("spatial")
    assert manager.status().is_open is False
    assert captures[0].released is True
