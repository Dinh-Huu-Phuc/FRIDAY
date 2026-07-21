from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class AudioWaveform(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._levels: deque[float] = deque([0.0] * 30, maxlen=30)
        self.setFixedSize(150, 36)
        self.setToolTip("Live microphone input level")

    def set_level(self, level: float) -> None:
        self._levels.append(max(0.0, min(1.0, float(level))))
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        middle = self.height() / 2
        painter.setPen(QPen(QColor(89, 247, 223, 38), 1))
        painter.drawLine(0, round(middle), self.width(), round(middle))

        spacing = self.width() / len(self._levels)
        for index, level in enumerate(self._levels):
            height = max(2.0, level * (self.height() - 5))
            color = QColor("#f1ba62") if level > 0.72 else QColor("#59f7df")
            color.setAlpha(90 + round(level * 165))
            pen = QPen(color, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            x = round((index + 0.5) * spacing)
            painter.drawLine(x, round(middle - height / 2), x, round(middle + height / 2))
