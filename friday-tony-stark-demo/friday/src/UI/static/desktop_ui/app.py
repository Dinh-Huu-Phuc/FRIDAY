from __future__ import annotations

import os
import sys

if os.name == "nt":
    os.environ.setdefault("QT_MEDIA_BACKEND", "windows")

from PySide6.QtWidgets import QApplication, QDialog

from friday.src.UI.static.desktop_ui.theme import DESKTOP_STYLESHEET
from friday.src.UI.static.desktop_ui.widgets.unlock_dialog import UnlockDialog
from friday.src.UI.static.desktop_ui.window import DesktopWindow


def run_desktop_app() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("FRIDAY Local Core")
    app.setOrganizationName("FRIDAY")
    app.setStyle("Fusion")
    app.setStyleSheet(DESKTOP_STYLESHEET)

    unlock = UnlockDialog()
    if unlock.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = DesktopWindow()
    window.show()
    return app.exec()


def main() -> None:
    raise SystemExit(run_desktop_app())


if __name__ == "__main__":
    main()
