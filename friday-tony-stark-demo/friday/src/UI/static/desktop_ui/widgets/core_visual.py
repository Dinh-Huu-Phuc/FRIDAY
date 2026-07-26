from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
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
        painter.fillRect(self.rect(), QColor("#020608"))
        center = QPointF(self.rect().center())
        extent = min(self.width(), self.height())
        radius = min(230.0, max(112.0, extent * 0.31))

        painter.setPen(QPen(QColor(70, 141, 151, 18), 1))
        grid_step = 38
        for x in range(0, self.width(), grid_step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_step):
            painter.drawLine(0, y, self.width(), y)

        state_color = {
            "thinking": QColor("#edbf6b"),
            "speaking": QColor("#72f0b2"),
        }.get(self._state, QColor("#59dfe4"))

        glow = QRadialGradient(center, radius * 1.25)
        glow.setColorAt(0.0, QColor(state_color.red(), state_color.green(), state_color.blue(), 52))
        glow.setColorAt(0.55, QColor(state_color.red(), state_color.green(), state_color.blue(), 12))
        glow.setColorAt(1.0, QColor(2, 6, 8, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center, radius * 1.28, radius * 1.28)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(86, 172, 182, 32), 1))
        painter.drawEllipse(center, radius * 1.19, radius * 1.19)
        painter.drawEllipse(center, radius * 0.78, radius * 0.78)

        for index in range(72):
            angle = math.radians(index * 5 + self._phase * 0.05)
            outer = radius * 1.12
            inner = radius * (1.04 if index % 6 else 0.99)
            alpha = 110 if index % 6 == 0 else 42
            painter.setPen(QPen(QColor(state_color.red(), state_color.green(), state_color.blue(), alpha), 1))
            painter.drawLine(
                QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
                QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer),
            )

        for index, color in enumerate((state_color, QColor("#edbf6b"), QColor("#6d9fd3"))):
            ring_radius = radius * (0.86 + index * 0.14)
            rect = QRectF(
                center.x() - ring_radius,
                center.y() - ring_radius,
                ring_radius * 2,
                ring_radius * 2,
            )
            pen = QPen(color, 2 if index else 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start = int((self._phase * (1 if index % 2 == 0 else -0.72) + index * 79) * 16)
            span = int((68 + index * 24) * 16)
            painter.drawArc(rect, start, span)

        for index, offset in enumerate((18.0, 138.0, 258.0)):
            angle = math.radians(self._phase * (0.7 if index != 1 else -0.55) + offset)
            orbit = radius * (0.91 + index * 0.1)
            point = QPointF(
                center.x() + math.cos(angle) * orbit,
                center.y() + math.sin(angle) * orbit,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#f4d48b") if index == 1 else state_color)
            painter.drawEllipse(point, 3.5, 3.5)

        pulse = 1.0 + math.sin(math.radians(self._phase * 2)) * 0.035
        core_gradient = QRadialGradient(center, radius * 0.55)
        core_gradient.setColorAt(0.0, QColor(194, 255, 250, 235))
        core_gradient.setColorAt(0.18, QColor(state_color.red(), state_color.green(), state_color.blue(), 190))
        core_gradient.setColorAt(0.55, QColor(8, 30, 35, 245))
        core_gradient.setColorAt(1.0, QColor(3, 10, 13, 255))
        painter.setBrush(core_gradient)
        painter.setPen(QPen(QColor(state_color.red(), state_color.green(), state_color.blue(), 145), 1.5))
        painter.drawEllipse(center, radius * 0.53 * pulse, radius * 0.53 * pulse)

        painter.setPen(QPen(QColor("#efffff"), 1))
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(center.x() - 60, center.y() - 34, 120, 42),
            Qt.AlignmentFlag.AlignCenter,
            "F",
        )
        painter.setPen(QColor(145, 183, 190))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(center.x() - 80, center.y() + 11, 160, 28),
            Qt.AlignmentFlag.AlignCenter,
            self._state.upper(),
        )
