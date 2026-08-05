from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BrowserSettingsDialog(QDialog):
    clear_history_requested = Signal()

    def __init__(self, *, signed_in: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FRIDAY Browser Settings")
        self.setModal(False)
        self.setMinimumWidth(520)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet(_SETTINGS_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        title = QLabel("FRIDAY Browser")
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        subtitle = QLabel("LOCAL BROWSER PREFERENCES")
        subtitle.setObjectName("settingsSubtitle")
        layout.addWidget(subtitle)
        layout.addWidget(_separator())
        layout.addLayout(_setting_row("Search provider", value="Google Search"))

        self._session_value = QLabel()
        layout.addLayout(
            _setting_row("Google session", value_widget=self._session_value)
        )
        layout.addWidget(_separator())

        privacy_title = QLabel("PRIVACY")
        privacy_title.setObjectName("settingsSection")
        layout.addWidget(privacy_title)

        privacy_copy = QLabel(
            "Clear navigation and visited-link history without removing cookies "
            "or your saved Google sign-in."
        )
        privacy_copy.setWordWrap(True)
        privacy_copy.setObjectName("settingsCopy")
        layout.addWidget(privacy_copy)

        clear_button = QPushButton("Clear browsing history")
        clear_button.setObjectName("clearHistoryButton")
        clear_button.clicked.connect(self.clear_history_requested.emit)
        layout.addWidget(clear_button, 0, Qt.AlignmentFlag.AlignLeft)

        self._status = QLabel("")
        self._status.setObjectName("settingsStatus")
        layout.addWidget(self._status)
        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.hide)
        layout.addWidget(buttons)
        self.set_signed_in(signed_in)

    def set_signed_in(self, signed_in: bool) -> None:
        self._session_value.setText("Signed in" if signed_in else "Not signed in")

    @property
    def status_text(self) -> str:
        return self._status.text()

    def show_history_cleared(self) -> None:
        self._status.setText("Browsing history cleared. Saved sign-in was kept.")


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setObjectName("settingsSeparator")
    return line


def _setting_row(
    label: str,
    value: str = "",
    *,
    value_widget: QLabel | None = None,
) -> QHBoxLayout:
    row = QHBoxLayout()
    name = QLabel(label)
    name.setObjectName("settingsName")
    row.addWidget(name)
    row.addStretch(1)
    active_value = value_widget or QLabel(value)
    active_value.setObjectName("settingsValue")
    row.addWidget(active_value)
    return row


_SETTINGS_STYLESHEET = """
QDialog {
    background: #070d11;
    color: #e8f7f8;
    font-family: "Segoe UI";
    font-size: 13px;
}
QLabel#settingsTitle {
    color: #75fff8;
    font-size: 22px;
    font-weight: 700;
}
QLabel#settingsSubtitle, QLabel#settingsSection {
    color: #78a5ad;
    font-size: 10px;
    font-weight: 700;
}
QLabel#settingsName { color: #b9cdd1; }
QLabel#settingsValue { color: #75fff8; font-weight: 600; }
QLabel#settingsCopy { color: #91a7ac; }
QLabel#settingsStatus { color: #73d9b0; min-height: 20px; }
QFrame#settingsSeparator { color: #18343a; }
QPushButton {
    background: #10252a;
    color: #ddffff;
    border: 1px solid #2c626a;
    padding: 8px 13px;
}
QPushButton:hover { background: #17363c; border-color: #69e9e3; }
QPushButton#clearHistoryButton { color: #75fff8; }
"""
