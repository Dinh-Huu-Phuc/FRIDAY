from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication

from friday.app.perception.camera import CameraManager
from friday.app.perception.detection import (
    BoundingBox,
    SceneSnapshot,
    TargetLock,
    TargetLockState,
    TrackedObject,
)
from friday.src.UI.static.camera_ui.hud_overlay import DetectionHudOverlay
from friday.src.UI.static.camera_ui.window import CameraWindow


class FakeVideoCapture:
    def __init__(self, _index: int) -> None:
        self.opened = True
        self.frame = np.zeros((180, 320, 3), dtype=np.uint8)
        self.frame[:, :, 1] = 180

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        time.sleep(0.005)
        return True, self.frame.copy()

    def release(self) -> None:
        self.opened = False


class FakePerceptionService:
    def __init__(self) -> None:
        person = TrackedObject(
            track_id=1,
            class_id=0,
            label="person",
            confidence=0.94,
            box=BoundingBox(80, 20, 240, 170),
            age_frames=3,
        )
        self._snapshot = SceneSnapshot(
            status="ready",
            frame_width=320,
            frame_height=180,
            objects=(person,),
            target_lock=TargetLock(
                state=TargetLockState.LOCKED,
                target=person,
                stable_frames=3,
            ),
            inference_ms=34.0,
            model_name="yolo26n",
        )

    def start(self, _camera_index: int) -> bool:
        return True

    def stop(self) -> None:
        return None

    def snapshot(self) -> SceneSnapshot:
        return self._snapshot


def _person_snapshot(x1: int, x2: int) -> SceneSnapshot:
    person = TrackedObject(
        track_id=7,
        class_id=0,
        label="person",
        confidence=0.91,
        box=BoundingBox(x1, 20, x2, 170),
        age_frames=4,
    )
    return SceneSnapshot(
        status="ready",
        frame_width=320,
        frame_height=180,
        objects=(person,),
        target_lock=TargetLock(
            state=TargetLockState.LOCKED,
            target=person,
            stable_frames=4,
        ),
    )


def test_camera_window_renders_shared_camera_frame() -> None:
    application = QApplication.instance() or QApplication([])
    manager = CameraManager(FakeVideoCapture)
    window = CameraWindow(manager, FakePerceptionService())

    assert window.start_preview() is True
    deadline = time.monotonic() + 1.0
    while manager.status().frame_sequence == 0 and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    window._render_latest_frame()

    assert window.feed.pixmap() is not None
    assert not window.feed.pixmap().isNull()
    assert "LOCKED / PERSON #01 / 94%" in window.target_label.text()
    window.close()
    application.processEvents()
    assert manager.status().is_open is False


def test_camera_hud_interpolates_box_instead_of_jumping() -> None:
    application = QApplication.instance() or QApplication([])
    overlay = DetectionHudOverlay(smoothing_ms=110)
    overlay.set_source_size(320, 180)
    overlay.set_snapshot(_person_snapshot(20, 120))
    before = overlay.displayed_box(7)
    assert before is not None

    overlay.set_snapshot(_person_snapshot(120, 220))
    time.sleep(0.03)
    overlay.advance()
    application.processEvents()
    after = overlay.displayed_box(7)

    assert after is not None
    assert before.left() < after.left() < 120
