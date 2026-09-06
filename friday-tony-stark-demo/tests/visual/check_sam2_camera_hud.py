from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from friday.app.perception.detection import BoundingBox
from friday.app.perception.segmentation import (
    MaskContour,
    MaskPoint,
    MaskRle,
    SegmentationMask,
    SegmentationResult,
    SegmentationStatus,
)
from friday.src.UI.static.camera_ui.feed_view import CameraFeedView


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    output = Path(__file__).resolve().parent / "output" / "sam2_camera_hud.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    view = CameraFeedView()
    view.resize(960, 540)
    frame = QImage(960, 540, QImage.Format.Format_RGB888)
    frame.fill(QColor(17, 27, 34))
    view.set_frame(frame)
    view.set_segmentation_result(
        SegmentationResult(
            status=SegmentationStatus.READY,
            answer="Visual check.",
            target_label="person",
            prompt_box=BoundingBox(280, 70, 680, 500),
            confidence=0.94,
            tracking=True,
            mask=SegmentationMask(
                width=8,
                height=8,
                area_pixels=24,
                coverage=0.375,
                rle=MaskRle(width=8, height=8, counts=(10, 4, 4, 6, 4, 6, 4, 4, 22)),
                contours=(
                    MaskContour(
                        points=(
                            MaskPoint(x=0.43, y=0.13),
                            MaskPoint(x=0.57, y=0.13),
                            MaskPoint(x=0.63, y=0.28),
                            MaskPoint(x=0.61, y=0.48),
                            MaskPoint(x=0.70, y=0.92),
                            MaskPoint(x=0.30, y=0.92),
                            MaskPoint(x=0.39, y=0.48),
                            MaskPoint(x=0.37, y=0.28),
                        )
                    ),
                ),
            ),
        )
    )
    view.show()
    application.processEvents()
    saved = view.grab().save(str(output), "PNG")
    view.close()
    print(output)
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
