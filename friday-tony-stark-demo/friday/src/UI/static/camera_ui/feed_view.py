from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from friday.app.perception.detection import SceneSnapshot
from friday.src.UI.static.camera_ui.hud_overlay import DetectionHudOverlay


class CameraFeedView(QWidget):
    """Stack a low-rate camera surface and independently animated HUD."""

    def __init__(self, parent: QWidget | None = None, *, smoothing_ms: int = 110) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        layout = QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.video_label = QLabel("CAMERA OFFLINE")
        self.video_label.setObjectName("cameraFeed")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)

        self.hud = DetectionHudOverlay(self, smoothing_ms=smoothing_ms)
        layout.addWidget(self.hud)
        self.hud.raise_()

    def set_frame(self, image: QImage) -> None:
        self._image = image
        self.hud.set_source_size(image.width(), image.height())
        self._refresh_pixmap()

    def clear_frame(self, message: str = "CAMERA OFFLINE") -> None:
        self._image = None
        self.video_label.clear()
        self.video_label.setText(message)
        self.hud.set_source_size(0, 0)

    def set_snapshot(self, snapshot: SceneSnapshot) -> None:
        self.hud.set_snapshot(snapshot)

    def set_metrics(
        self,
        *,
        camera_index: int,
        source_fps: float,
        render_fps: float,
        uptime_seconds: float,
    ) -> None:
        self.hud.set_metrics(
            camera_index=camera_index,
            source_fps=source_fps,
            render_fps=render_fps,
            uptime_seconds=uptime_seconds,
        )

    def advance_hud(self, now: float) -> None:
        self.hud.advance(now)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._image is None or self.width() <= 0 or self.height() <= 0:
            return
        pixmap = QPixmap.fromImage(self._image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(pixmap)
