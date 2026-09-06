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
    TrackingState,
)
from friday.app.perception.detection.grounding import (
    GroundingMatch,
    GroundingResult,
    GroundingStatus,
)
from friday.app.perception.scene import (
    ObjectRelation,
    ObjectRelationType,
    TemporalSceneSnapshot,
)
from friday.app.perception.segmentation import (
    MaskContour,
    MaskPoint,
    MaskRle,
    SegmentationMask,
    SegmentationResult,
    SegmentationStatus,
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


def test_camera_hud_keeps_kalman_box_during_short_track_loss() -> None:
    application = QApplication.instance() or QApplication([])
    overlay = DetectionHudOverlay(smoothing_ms=110)
    overlay.set_source_size(320, 180)
    snapshot = _person_snapshot(20, 120)
    overlay.set_snapshot(snapshot)
    person = snapshot.objects[0]
    overlay.set_snapshot(
        SceneSnapshot(
            status="ready",
            frame_width=320,
            frame_height=180,
            objects=(
                TrackedObject(
                    track_id=person.track_id,
                    class_id=person.class_id,
                    label=person.label,
                    confidence=person.confidence,
                    box=BoundingBox(28, 20, 128, 170),
                    age_frames=person.age_frames + 1,
                    missed_frames=1,
                    tracking_state=TrackingState.LOST,
                ),
            ),
            target_lock=TargetLock(
                state=TargetLockState.LOST,
                target=person,
            ),
        )
    )
    application.processEvents()

    assert overlay.displayed_box(person.track_id) is not None


def test_camera_hud_labels_active_object_relation() -> None:
    overlay = DetectionHudOverlay(smoothing_ms=110)
    overlay.set_source_size(320, 180)
    overlay.set_snapshot(_person_snapshot(20, 120))
    overlay.set_temporal_snapshot(
        TemporalSceneSnapshot(
            observed_at=10.0,
            status="ready",
            relations=(
                ObjectRelation(
                    relation_type=ObjectRelationType.POINTED_AT_BY_HAND,
                    track_id=7,
                    label="person",
                    hand_id="right-1",
                    handedness="right",
                    confidence=0.88,
                    since=10.0,
                    origin_x=0.5,
                    origin_y=0.5,
                ),
            ),
        )
    )

    assert overlay._relation_suffix(7) == " / POINTED"


def test_camera_hud_accepts_transient_open_vocabulary_target() -> None:
    application = QApplication.instance() or QApplication([])
    overlay = DetectionHudOverlay(smoothing_ms=110)
    overlay.set_source_size(320, 180)
    overlay.set_grounding_result(
        GroundingResult(
            status=GroundingStatus.READY,
            query="red screwdriver",
            answer="Located it.",
            matches=(
                GroundingMatch(
                    label="red screwdriver",
                    confidence=0.84,
                    box=BoundingBox(170, 40, 280, 150),
                ),
            ),
            frame_width=320,
            frame_height=180,
        )
    )
    application.processEvents()

    displayed = overlay.displayed_grounding_box(0)
    assert displayed is not None
    assert displayed.left() == 170

    overlay.set_grounding_result(None)
    assert overlay.displayed_grounding_box(0) is None


def test_camera_hud_renders_sam2_contour_without_decoding_rle_per_frame() -> None:
    application = QApplication.instance() or QApplication([])
    overlay = DetectionHudOverlay(smoothing_ms=110)
    overlay.resize(640, 360)
    overlay.set_source_size(320, 180)
    overlay.set_segmentation_result(
        SegmentationResult(
            status=SegmentationStatus.READY,
            answer="Segmented.",
            target_label="person",
            prompt_box=BoundingBox(80, 20, 240, 170),
            confidence=0.92,
            mask=SegmentationMask(
                width=4,
                height=4,
                area_pixels=4,
                coverage=0.25,
                rle=MaskRle(width=4, height=4, counts=(5, 2, 2, 2, 5)),
                contours=(
                    MaskContour(
                        points=(
                            MaskPoint(x=0.25, y=0.2),
                            MaskPoint(x=0.75, y=0.2),
                            MaskPoint(x=0.75, y=0.9),
                            MaskPoint(x=0.25, y=0.9),
                        )
                    ),
                ),
            ),
        )
    )

    rendered = overlay.grab().toImage()
    application.processEvents()

    assert not rendered.isNull()
    center = rendered.pixelColor(320, 180)
    assert center.alpha() > 0
