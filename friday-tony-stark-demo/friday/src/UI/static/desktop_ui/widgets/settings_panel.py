from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from friday.app.power import get_auto_sleep_settings, update_auto_sleep_settings


class SettingsPanel(QFrame):
    visual_changed = Signal(str)
    voice_changed = Signal(bool)
    applied = Signal(str)

    def __init__(self, settings: QSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setObjectName("settingsPanel")
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        heading = QLabel("SETTINGS")
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Interface"))
        visual_row = QHBoxLayout()
        self.orb_button = QRadioButton("Core Orb")
        self.video_button = QRadioButton("FRIDAY Video")
        group = QButtonGroup(self)
        group.addButton(self.orb_button)
        group.addButton(self.video_button)
        visual_row.addWidget(self.orb_button)
        visual_row.addWidget(self.video_button)
        layout.addLayout(visual_row)

        current_visual = str(settings.value("appearance/visual", "orb"))
        self.video_button.setChecked(current_visual == "video")
        self.orb_button.setChecked(current_visual != "video")
        self.orb_button.toggled.connect(lambda checked: checked and self._set_visual("orb"))
        self.video_button.toggled.connect(lambda checked: checked and self._set_visual("video"))

        self.voice_reply = QCheckBox("Voice reply")
        self.voice_reply.setChecked(settings.value("voice/enabled", True, type=bool))
        self.voice_reply.toggled.connect(self._set_voice)
        layout.addWidget(self.voice_reply)

        layout.addWidget(QLabel("Automatic sleep"))
        sleep_row = QHBoxLayout()
        self.sleep_minutes = QSpinBox()
        self.sleep_minutes.setRange(1, 1440)
        self.sleep_minutes.setSuffix(" min")
        self.sleep_minutes.setValue(round(get_auto_sleep_settings().minutes))
        sleep_row.addWidget(self.sleep_minutes, 1)
        apply_button = QPushButton("Apply")
        apply_button.setObjectName("primaryButton")
        apply_button.clicked.connect(self._apply_sleep)
        sleep_row.addWidget(apply_button)
        layout.addLayout(sleep_row)
        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setObjectName("settingsFeedback")
        layout.addWidget(self.feedback)
        layout.addStretch(1)

    def _set_visual(self, visual: str) -> None:
        self._settings.setValue("appearance/visual", visual)
        self.visual_changed.emit(visual)

    def _set_voice(self, enabled: bool) -> None:
        self._settings.setValue("voice/enabled", enabled)
        self.voice_changed.emit(enabled)

    def _apply_sleep(self) -> None:
        value = self.sleep_minutes.value()
        update_auto_sleep_settings(minutes=value, source="desktop_ui")
        message = f"Automatic sleep updated to {value} minutes."
        self.feedback.setText(message)
        self.applied.emit(message)
