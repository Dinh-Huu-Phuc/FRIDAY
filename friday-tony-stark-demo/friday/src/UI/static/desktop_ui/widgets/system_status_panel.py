from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _StatusRow(QWidget):
    def __init__(self, name: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("systemRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)

        marker = QLabel("+")
        marker.setObjectName("systemMarker")
        marker.setFixedWidth(12)
        marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(marker)

        label = QLabel(name)
        label.setObjectName("systemName")
        layout.addWidget(label, 1)

        self.value = QLabel(value)
        self.value.setObjectName("systemValue")
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.value)


class SystemStatusPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("systemPanel")
        self.setMinimumWidth(190)
        self.setMaximumWidth(224)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("FRIDAY / SYSTEM")
        title.setObjectName("systemTitle")
        layout.addWidget(title)

        health = QFrame()
        health.setObjectName("healthStrip")
        health_layout = QHBoxLayout(health)
        health_layout.setContentsMargins(0, 2, 0, 7)
        health_layout.setSpacing(7)
        dot = QLabel()
        dot.setObjectName("healthDot")
        dot.setFixedSize(6, 6)
        health_layout.addWidget(dot)
        self.health_label = QLabel("ALL SYSTEMS OPERATIONAL")
        self.health_label.setObjectName("healthLabel")
        health_layout.addWidget(self.health_label, 1)
        layout.addWidget(health)

        self._rows: dict[str, _StatusRow] = {}
        for name, value in (
            ("INTENT", "READY"),
            ("VISION", "LOCAL"),
            ("SEARCH", "READY"),
            ("BROWSER", "READY"),
            ("COMMS", "ONLINE"),
            ("MEMORY", "LINKED"),
            ("TOOLS", "READY"),
            ("POWER", "OPTIMAL"),
            ("VOICE", "READY"),
            ("DISPLAY", "READY"),
            ("CALENDAR", "SYNCED"),
            ("OLLAMA / LLM", "READY"),
        ):
            row = _StatusRow(name, value)
            self._rows[name] = row
            layout.addWidget(row)

        layout.addStretch(1)

        state_label = QLabel("RUNTIME STATE")
        state_label.setObjectName("systemCaption")
        layout.addWidget(state_label)
        self.runtime_state = QLabel("ONLINE")
        self.runtime_state.setObjectName("runtimeState")
        layout.addWidget(self.runtime_state)

        activity = QFrame()
        activity.setObjectName("activityMeter")
        activity_layout = QHBoxLayout(activity)
        activity_layout.setContentsMargins(0, 0, 0, 0)
        activity_layout.setSpacing(3)
        for index in range(10):
            segment = QFrame()
            segment.setObjectName("activitySegmentOn" if index < 7 else "activitySegmentOff")
            segment.setFixedHeight(3)
            activity_layout.addWidget(segment, 1)
        layout.addWidget(activity)

    def set_core_state(self, state: str) -> None:
        normalized = state.strip().upper() or "ONLINE"
        self.runtime_state.setText(normalized)
        if normalized == "SLEEPING":
            self._rows["POWER"].value.setText("SLEEP")
            self._rows["VOICE"].value.setText("STANDBY")
        else:
            self._rows["POWER"].value.setText("OPTIMAL")
            self._rows["VOICE"].value.setText(
                "ACTIVE" if normalized in {"LISTENING", "SPEAKING"} else "READY"
            )
