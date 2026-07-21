from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class CoreVisual(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._state = "online"
        self.setMinimumSize(360, 360)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(30)

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def _advance(self) -> None:
        self._phase = (self._phase + (3.8 if self._state == "thinking" else 2.0)) % 360
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        extent = min(self.width(), self.height())
        radius = max(90.0, extent * 0.26)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(5, 13, 18, 235))
        painter.drawEllipse(center, radius * 0.78, radius * 0.78)
        painter.setBrush(QColor(56, 245, 211, 42))
        pulse = 1.0 + math.sin(math.radians(self._phase * 2)) * 0.05
        painter.drawEllipse(center, radius * 0.62 * pulse, radius * 0.62 * pulse)
        painter.setBrush(QColor(111, 255, 225, 205))
        painter.drawEllipse(center, radius * 0.22, radius * 0.22)

        for index, color in enumerate((QColor("#59f7df"), QColor("#f1ba62"), QColor("#70a7ff"))):
            ring_radius = radius * (0.92 + index * 0.22)
            rect = self.rect().adjusted(
                int((self.width() - ring_radius * 2) / 2),
                int((self.height() - ring_radius * 2) / 2),
                -int((self.width() - ring_radius * 2) / 2),
                -int((self.height() - ring_radius * 2) / 2),
            )
            pen = QPen(color, 2 if index else 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start = int((self._phase * (1 if index % 2 == 0 else -1) + index * 74) * 16)
            span = int((92 + index * 28) * 16)
            painter.drawArc(rect, start, span)

        painter.setPen(QPen(QColor(89, 247, 223, 45), 1))
        for offset in (-0.42, 0.42):
            line_y = center.y() + int(radius * offset)
            painter.drawLine(center.x() - int(radius * 0.9), line_y, center.x() + int(radius * 0.9), line_y)
