from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


FRIDAY_DIR = Path(__file__).resolve().parents[5]
CLONE_ICON = FRIDAY_DIR / "assets" / "icons" / "fontawesome" / "clone-regular-full.svg"


class MessageBubble(QFrame):
    copied = Signal()

    def __init__(self, message: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.content = str(message.get("content") or "")
        role = str(message.get("role") or "assistant")
        self.setObjectName("userBubble" if role == "user" else "assistantBubble")
        self.setFixedWidth(354)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        header = QHBoxLayout()
        stamp = _format_timestamp(str(message.get("timestamp") or ""))
        title = QLabel(f"{'YOU' if role == 'user' else 'FRIDAY'}  /  {stamp}")
        title.setObjectName("messageMeta")
        header.addWidget(title)
        header.addStretch(1)
        copy_button = QPushButton()
        copy_button.setObjectName("copyButton")
        copy_button.setFixedSize(26, 26)
        copy_button.setToolTip("Copy message")
        if CLONE_ICON.is_file():
            copy_button.setIcon(QIcon(str(CLONE_ICON)))
        else:
            copy_button.setText("C")
        copy_button.clicked.connect(self._copy)
        header.addWidget(copy_button)
        layout.addLayout(header)

        body = QTextBrowser()
        body.setObjectName("messageBody")
        body.setOpenExternalLinks(True)
        body.setFrameShape(QFrame.Shape.NoFrame)
        body.setStyleSheet("QTextBrowser { background: transparent; border: 0; }")
        body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.setMarkdown(self.content)
        body.document().setTextWidth(322)
        body.setFixedHeight(
            max(32, min(320, math.ceil(body.document().size().height()) + 8))
        )
        layout.addWidget(body)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.content)
        self.copied.emit()


def _format_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
        return parsed.strftime("%I:%M:%S %p").lstrip("0")
    except ValueError:
        return "now"
