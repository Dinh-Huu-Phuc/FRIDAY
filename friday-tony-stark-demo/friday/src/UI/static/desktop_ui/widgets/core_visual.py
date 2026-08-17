from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from friday.src.UI.static.desktop_ui.effects import OrbRenderer


class CoreVisual(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._state = "online"
        self._audio_level = 0.0
        self._renderer = OrbRenderer()
        self.setMinimumSize(400, 400)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._advance)
        self._timer.start(33)

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def set_audio_level(self, level: float) -> None:
        self._audio_level = max(0.0, min(1.0, float(level)))

    def _advance(self) -> None:
        speed = {
            "thinking": 3.4,
            "speaking": 2.8,
            "listening": 2.4,
            "sleeping": 0.65,
        }.get(self._state, 1.65)
        self._phase = (self._phase + speed) % 360
        self._audio_level *= 0.88
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        self._renderer.paint(
            painter,
            self.rect(),
            phase=self._phase,
            state=self._state,
            audio_level=self._audio_level,
        )
