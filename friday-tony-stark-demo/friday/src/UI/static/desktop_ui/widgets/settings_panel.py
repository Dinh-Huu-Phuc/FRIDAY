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
        self.setFixedWidth(286)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        heading = QLabel("SETTINGS")
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)
        subtitle = QLabel("LOCAL CORE PREFERENCES")
        subtitle.setObjectName("sectionMeta")
        layout.addWidget(subtitle)
        interface_label = QLabel("INTERFACE")
        interface_label.setObjectName("sectionTitle")
        layout.addWidget(interface_label)
        visual_options = QVBoxLayout()
        visual_options.setSpacing(9)
        self.orb_button = QRadioButton("Core Orb")
        self.video_button = QRadioButton("FRIDAY Video")
        self.neural_button = QRadioButton("Neural Network")
        group = QButtonGroup(self)
        group.addButton(self.orb_button)
        group.addButton(self.video_button)
        group.addButton(self.neural_button)
        visual_options.addWidget(self.orb_button)
        visual_options.addWidget(self.video_button)
        visual_options.addWidget(self.neural_button)
        layout.addLayout(visual_options)

        current_visual = str(settings.value("appearance/visual", "orb"))
        self.video_button.setChecked(current_visual == "video")
        self.neural_button.setChecked(current_visual == "neural")
        self.orb_button.setChecked(current_visual not in {"video", "neural"})
        self.orb_button.toggled.connect(lambda checked: checked and self._set_visual("orb"))
        self.video_button.toggled.connect(lambda checked: checked and self._set_visual("video"))
        self.neural_button.toggled.connect(
            lambda checked: checked and self._set_visual("neural")
        )

        self.voice_reply = QCheckBox("Read replies aloud")
        self.voice_reply.setChecked(settings.value("voice/enabled", True, type=bool))
        self.voice_reply.toggled.connect(self._set_voice)
        layout.addWidget(self.voice_reply)

        sleep_label = QLabel("AUTOMATIC SLEEP")
        sleep_label.setObjectName("sectionTitle")
        layout.addWidget(sleep_label)
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

    def select_visual(self, visual: str) -> None:
        buttons = {
            "orb": self.orb_button,
            "video": self.video_button,
            "neural": self.neural_button,
        }
        button = buttons.get(visual, self.orb_button)
        was_checked = button.isChecked()
        button.setChecked(True)
        if was_checked:
            self._set_visual(visual if visual in buttons else "orb")

    def _set_voice(self, enabled: bool) -> None:
        self._settings.setValue("voice/enabled", enabled)
        self.voice_changed.emit(enabled)

    def _apply_sleep(self) -> None:
        value = self.sleep_minutes.value()
        update_auto_sleep_settings(minutes=value, source="desktop_ui")
        message = f"Automatic sleep updated to {value} minutes."
        self.feedback.setText(message)
        self.applied.emit(message)
