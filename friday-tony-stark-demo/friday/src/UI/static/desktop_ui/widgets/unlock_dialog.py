from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from friday.core.db import (
    CredentialAlreadyConfiguredError,
    InvalidPasswordError,
    PasswordConfirmationError,
    get_core_access_gate,
)


class UnlockDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.gate = get_core_access_gate()
        self.configured = self.gate.is_configured()
        self.setWindowTitle("Unlock FRIDAY")
        self.setModal(True)
        self.setFixedWidth(430)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(16)
        title = QLabel("FRIDAY CORE")
        title.setObjectName("unlockTitle")
        layout.addWidget(title)
        subtitle = QLabel(
            "Enter your core password." if self.configured else
            "Create the permanent core password. It cannot be recovered or recreated."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password")
        self.password.returnPressed.connect(self._submit)
        form.addRow("Password", self.password)
        self.confirmation = QLineEdit()
        self.confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmation.setPlaceholderText("Confirm password")
        self.confirmation.returnPressed.connect(self._submit)
        if not self.configured:
            form.addRow("Confirm", self.confirmation)
        layout.addLayout(form)
        self.error = QLabel("")
        self.error.setObjectName("unlockError")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        submit = QPushButton("Unlock" if self.configured else "Create password")
        submit.setObjectName("primaryButton")
        submit.clicked.connect(self._submit)
        layout.addWidget(submit)

    def _submit(self) -> None:
        try:
            if self.configured:
                self.gate.unlock(self.password.text())
            else:
                self.gate.setup(self.password.text(), self.confirmation.text())
        except (
            CredentialAlreadyConfiguredError,
            InvalidPasswordError,
            PasswordConfirmationError,
        ) as exc:
            self.error.setText(str(exc))
            self.password.selectAll()
            return
        self.accept()
