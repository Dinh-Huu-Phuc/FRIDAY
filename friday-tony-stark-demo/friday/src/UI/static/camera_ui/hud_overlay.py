from __future__ import annotations

import math
import time
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from friday.app.perception.detection import SceneSnapshot, TargetLockState

PRIMARY_BLUE = QColor(53, 181, 255)
PRIMARY_CYAN = QColor(98, 235, 255)
SECONDARY_BLUE = QColor(74, 143, 194, 190)
MUTED_BLUE = QColor(91, 127, 158, 175)
PANEL_DARK = QColor(2, 13, 20, 210)


@dataclass(slots=True)
class _SmoothBox:
    x1: float
    y1: float
    x2: float
    y2: float
    target_x1: float
    target_y1: float
    target_x2: float
    target_y2: float

    @classmethod
    def from_box(cls, box) -> _SmoothBox:
        coordinates = tuple(float(value) for value in (box.x1, box.y1, box.x2, box.y2))
        return cls(*coordinates, *coordinates)

    def set_target(self, box) -> None:
        self.target_x1 = float(box.x1)
        self.target_y1 = float(box.y1)
        self.target_x2 = float(box.x2)
        self.target_y2 = float(box.y2)

    def advance(self, alpha: float) -> None:
        self.x1 += (self.target_x1 - self.x1) * alpha
        self.y1 += (self.target_y1 - self.y1) * alpha
        self.x2 += (self.target_x2 - self.x2) * alpha
        self.y2 += (self.target_y2 - self.y2) * alpha

    def as_rect(self) -> QRectF:
        return QRectF(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)


class DetectionHudOverlay(QWidget):
    """Lightweight 60 Hz HUD over a lower-rate detector scene state."""

    def __init__(self, parent: QWidget | None = None, *, smoothing_ms: int = 110) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self._smoothing_seconds = max(0.04, smoothing_ms / 1000)
        self._snapshot = SceneSnapshot.idle()
        self._boxes: dict[int, _SmoothBox] = {}
        self._source_width = 0
        self._source_height = 0
        self._camera_index = 0
        self._source_fps = 0.0
        self._detector_fps = 0.0
        self._render_fps = 0.0
        self._uptime_seconds = 0.0
        self._last_advanced_at = time.monotonic()
        self._label_font = QFont("Segoe UI", 9)
        self._label_font.setBold(True)
        self._meta_font = QFont("Consolas", 8)

    def set_source_size(self, width: int, height: int) -> None:
        self._source_width = max(0, width)
        self._source_height = max(0, height)

    def set_snapshot(self, snapshot: SceneSnapshot) -> None:
        self._snapshot = snapshot
        active_ids: set[int] = set()
        for item in snapshot.objects:
            active_ids.add(item.track_id)
            smooth_box = self._boxes.get(item.track_id)
            if smooth_box is None:
                self._boxes[item.track_id] = _SmoothBox.from_box(item.box)
            else:
                smooth_box.set_target(item.box)
        for track_id in tuple(self._boxes):
            if track_id not in active_ids:
                del self._boxes[track_id]

    def set_metrics(
        self,
        *,
        camera_index: int,
        source_fps: float,
        render_fps: float,
        uptime_seconds: float,
    ) -> None:
        self._camera_index = camera_index
        self._source_fps = source_fps
        self._render_fps = render_fps
        self._uptime_seconds = uptime_seconds
        self._detector_fps = self._snapshot.detector_fps

    def advance(self, now: float | None = None) -> None:
        current_time = time.monotonic() if now is None else now
        elapsed = min(0.1, max(0.0, current_time - self._last_advanced_at))
        self._last_advanced_at = current_time
        alpha = 1.0 - math.exp(-elapsed / self._smoothing_seconds)
        for box in self._boxes.values():
            box.advance(alpha)
        self.update()

    def displayed_box(self, track_id: int) -> QRectF | None:
        box = self._boxes.get(track_id)
        return box.as_rect() if box else None

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if self._source_width <= 0 or self._source_height <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        video_rect, scale = self._video_geometry()
        self._draw_camera_metrics(painter, video_rect)

        locked_target = self._snapshot.target_lock.target
        locked_id = locked_target.track_id if locked_target else None
        for item in self._snapshot.objects[:12]:
            smooth_box = self._boxes.get(item.track_id)
            if smooth_box is None:
                continue
            mapped = self._map_box(smooth_box.as_rect(), video_rect, scale)
            if item.track_id == locked_id:
                self._draw_lock_frame(
                    painter,
                    mapped,
                    item.label,
                    item.track_id,
                    item.confidence,
                    self._snapshot.target_lock.state,
                    video_rect,
                )
            else:
                self._draw_annotation(
                    painter,
                    mapped,
                    item.label,
                    item.track_id,
                    item.confidence,
                    video_rect,
                )
        painter.end()

    def _video_geometry(self) -> tuple[QRectF, float]:
        scale = min(
            self.width() / self._source_width,
            self.height() / self._source_height,
        )
        width = self._source_width * scale
        height = self._source_height * scale
        return (
            QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height),
            scale,
        )

    @staticmethod
    def _map_box(box: QRectF, video_rect: QRectF, scale: float) -> QRectF:
        return QRectF(
            video_rect.left() + box.left() * scale,
            video_rect.top() + box.top() * scale,
            box.width() * scale,
            box.height() * scale,
        )

    def _draw_camera_metrics(self, painter: QPainter, video_rect: QRectF) -> None:
        x = video_rect.left() + 16
        y = video_rect.top() + 18
        panel = QRectF(x, y, 190, 92)
        painter.fillRect(panel, QColor(1, 10, 17, 150))
        painter.fillRect(QRectF(x, y, 2, panel.height()), PRIMARY_BLUE)
        painter.setFont(self._label_font)
        painter.setPen(PRIMARY_CYAN)
        painter.drawText(QPointF(x + 12, y + 17), f"CAMERA {self._camera_index:02d} / LIVE")
        painter.setFont(self._meta_font)
        painter.setPen(QColor(167, 212, 235))
        rows = (
            f"SOURCE   {self._source_width}x{self._source_height}  {self._source_fps:04.1f} FPS",
            f"DETECT   {self._detector_fps:04.1f} FPS  {self._snapshot.model_name.upper() or 'WAIT'}",
            f"OBJECTS  {len(self._snapshot.objects):02d}",
            f"HUD      {self._render_fps:04.1f} FPS  UP {self._format_uptime()}",
        )
        for index, row in enumerate(rows):
            painter.drawText(QPointF(x + 12, y + 35 + index * 14), row)

    def _draw_annotation(
        self,
        painter: QPainter,
        box: QRectF,
        label: str,
        track_id: int,
        confidence: float,
        video_rect: QRectF,
    ) -> None:
        painter.setPen(self._pen(SECONDARY_BLUE, 1))
        corner = max(10.0, min(24.0, min(box.width(), box.height()) * 0.16))
        self._draw_corners(painter, box, corner)

        text = f"{label.upper()} #{track_id:02d}   {confidence:.0%}"
        painter.setFont(self._meta_font)
        text_width = painter.fontMetrics().horizontalAdvance(text) + 14
        label_x = max(video_rect.left() + 8, min(box.left() - 12, video_rect.right() - text_width - 8))
        label_y = max(video_rect.top() + 8, box.top() - 28)
        label_rect = QRectF(label_x, label_y, text_width, 20)
        anchor = QPointF(box.left(), box.top() + min(24.0, box.height() * 0.25))
        elbow = QPointF(label_rect.left(), anchor.y())
        painter.drawLine(anchor, elbow)
        painter.drawLine(elbow, QPointF(label_rect.left(), label_rect.bottom()))
        painter.fillRect(label_rect, PANEL_DARK)
        painter.fillRect(QRectF(label_rect.left(), label_rect.bottom() - 1, label_rect.width(), 1), SECONDARY_BLUE)
        painter.setPen(QColor(167, 222, 246))
        painter.drawText(QPointF(label_rect.left() + 7, label_rect.top() + 14), text)

    def _draw_lock_frame(
        self,
        painter: QPainter,
        box: QRectF,
        label: str,
        track_id: int,
        confidence: float,
        state: TargetLockState,
        video_rect: QRectF,
    ) -> None:
        margin = max(5.0, min(12.0, min(box.width(), box.height()) * 0.025))
        frame = box.adjusted(-margin, -margin, margin, margin).intersected(video_rect)
        color = {
            TargetLockState.LOCKED: PRIMARY_CYAN,
            TargetLockState.ACQUIRING: PRIMARY_BLUE,
            TargetLockState.LOST: MUTED_BLUE,
        }.get(state, PRIMARY_BLUE)
        painter.setPen(self._pen(color, 2))
        corner = max(18.0, min(52.0, min(frame.width(), frame.height()) * 0.18))
        self._draw_corners(painter, frame, corner)

        tick = 8.0
        center_x = frame.center().x()
        center_y = frame.center().y()
        painter.setPen(self._pen(QColor(color.red(), color.green(), color.blue(), 180), 1))
        painter.drawLine(QPointF(center_x - tick, frame.top()), QPointF(center_x + tick, frame.top()))
        painter.drawLine(QPointF(center_x - tick, frame.bottom()), QPointF(center_x + tick, frame.bottom()))
        painter.drawLine(QPointF(frame.left(), center_y - tick), QPointF(frame.left(), center_y + tick))
        painter.drawLine(QPointF(frame.right(), center_y - tick), QPointF(frame.right(), center_y + tick))

        text = f"{state.value.upper()} / {label.upper()} #{track_id:02d} / {confidence:.0%}"
        painter.setFont(self._label_font)
        text_width = painter.fontMetrics().horizontalAdvance(text) + 18
        label_x = max(video_rect.left() + 8, min(frame.left(), video_rect.right() - text_width - 8))
        label_y = frame.top() - 27
        if label_y < video_rect.top() + 6:
            label_y = frame.top() + 7
        label_rect = QRectF(label_x, label_y, text_width, 22)
        painter.fillRect(label_rect, PANEL_DARK)
        painter.fillRect(QRectF(label_rect.left(), label_rect.bottom() - 2, label_rect.width(), 2), color)
        painter.setPen(color)
        painter.drawText(QPointF(label_rect.left() + 8, label_rect.top() + 16), text)

        confidence_width = max(20.0, min(80.0, frame.width() * 0.22))
        confidence_y = frame.bottom() + 7
        if confidence_y + 3 <= video_rect.bottom():
            painter.fillRect(QRectF(frame.left(), confidence_y, confidence_width, 2), MUTED_BLUE)
            painter.fillRect(
                QRectF(frame.left(), confidence_y, confidence_width * confidence, 2),
                color,
            )

    @staticmethod
    def _draw_corners(painter: QPainter, rect: QRectF, length: float) -> None:
        segments = (
            (rect.topLeft(), QPointF(rect.left() + length, rect.top())),
            (rect.topLeft(), QPointF(rect.left(), rect.top() + length)),
            (rect.topRight(), QPointF(rect.right() - length, rect.top())),
            (rect.topRight(), QPointF(rect.right(), rect.top() + length)),
            (rect.bottomLeft(), QPointF(rect.left() + length, rect.bottom())),
            (rect.bottomLeft(), QPointF(rect.left(), rect.bottom() - length)),
            (rect.bottomRight(), QPointF(rect.right() - length, rect.bottom())),
            (rect.bottomRight(), QPointF(rect.right(), rect.bottom() - length)),
        )
        for start, end in segments:
            painter.drawLine(start, end)

    @staticmethod
    def _pen(color: QColor, width: int) -> QPen:
        pen = QPen(color, width)
        pen.setCosmetic(True)
        return pen

    def _format_uptime(self) -> str:
        total_seconds = max(0, round(self._uptime_seconds))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
