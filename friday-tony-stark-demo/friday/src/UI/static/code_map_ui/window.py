from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStyle,
    QToolBar,
    QToolButton,
)

from friday.app.code_map.settings import (
    DEFAULT_CODE_MAP_URL,
    CodeMapSettings,
    get_code_map_settings,
)
from friday.src.UI.static.code_map_ui.theme import CODE_MAP_STYLESHEET


class CodeMapWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(
        self,
        level,
        message: str,
        line_number: int,
        source_id: str,
    ) -> None:
        verbose = os.getenv("FRIDAY_CODE_MAP_JS_CONSOLE", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if verbose:
            super().javaScriptConsoleMessage(level, message, line_number, source_id)


class CodeMapWindow(QMainWindow):
    closed = Signal()

    def __init__(self, settings: CodeMapSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or get_code_map_settings()
        self._profile_path = Path(self._settings.profile_path)
        self._profile_path.mkdir(parents=True, exist_ok=True)
        self._qt_settings = QSettings("FRIDAY", "CodeMap")
        self._full_screen = False
        self._shortcuts: list[QShortcut] = []

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("FRIDAY Code Map")
        self.setMinimumSize(960, 620)
        self.resize(1500, 920)
        self.setStyleSheet(CODE_MAP_STYLESHEET)

        self._profile = QWebEngineProfile("friday-code-map", self)
        self._profile.setPersistentStoragePath(str(self._profile_path / "storage"))
        self._profile.setCachePath(str(self._profile_path / "cache"))
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self._page = CodeMapWebPage(self._profile, self)
        self._page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
            True,
        )
        self._page.fullScreenRequested.connect(self._handle_web_full_screen)
        self._view = QWebEngineView(self)
        self._view.setPage(self._page)
        self.setCentralWidget(self._view)

        self._build_toolbar()
        self._connect_browser_signals()
        self._add_shortcut(QKeySequence.StandardKey.Close, self.close)
        self._add_shortcut(QKeySequence("F11"), self.toggle_full_screen)
        self._add_shortcut(QKeySequence("Esc"), self._escape)
        self._view.setUrl(QUrl(self._initial_url()))

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Code Map controls", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        brand = QLabel("FRIDAY  /  CODE MAP")
        brand.setObjectName("codeMapBrand")
        toolbar.addWidget(brand)
        self._back = self._tool_button(
            QStyle.StandardPixmap.SP_ArrowBack, "Back", self._view.back
        )
        self._forward = self._tool_button(
            QStyle.StandardPixmap.SP_ArrowForward, "Forward", self._view.forward
        )
        toolbar.addWidget(self._back)
        toolbar.addWidget(self._forward)
        toolbar.addWidget(
            self._tool_button(
                QStyle.StandardPixmap.SP_BrowserReload,
                "Reload graph",
                self._view.reload,
            )
        )
        toolbar.addWidget(
            self._tool_button(
                QStyle.StandardPixmap.SP_DirHomeIcon,
                "Open Grapuco dashboard",
                self.open_home,
            )
        )
        toolbar.addSeparator()
        self._status = QLabel("Loading code map...")
        self._status.setObjectName("codeMapStatus")
        toolbar.addWidget(self._status)
        spacer = QLabel()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addWidget(
            self._tool_button(
                QStyle.StandardPixmap.SP_TitleBarMaxButton,
                "Toggle full screen (F11)",
                self.toggle_full_screen,
            )
        )
        close_button = self._tool_button(
            QStyle.StandardPixmap.SP_DialogCloseButton,
            "Close Code Map",
            self.close,
        )
        close_button.setObjectName("codeMapClose")
        toolbar.addWidget(close_button)

    def _tool_button(self, icon_name, tooltip: str, callback) -> QToolButton:
        button = QToolButton(self)
        button.setIcon(self.style().standardIcon(icon_name))
        button.setToolTip(tooltip)
        button.setFixedSize(34, 34)
        button.clicked.connect(callback)
        return button

    def _add_shortcut(self, key, callback) -> None:
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)

    def _connect_browser_signals(self) -> None:
        self._view.loadStarted.connect(lambda: self._status.setText("Loading code map..."))
        self._view.loadProgress.connect(
            lambda progress: self._status.setText(f"Loading code map... {progress}%")
        )
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.urlChanged.connect(self._on_url_changed)
        self._view.titleChanged.connect(
            lambda title: self.setWindowTitle(
                f"{title} | FRIDAY Code Map" if title else "FRIDAY Code Map"
            )
        )

    def _initial_url(self) -> str:
        configured = self._settings.url
        remembered = str(self._qt_settings.value("lastUrl", ""))
        if configured == DEFAULT_CODE_MAP_URL and remembered.startswith("https://grapuco.com/"):
            return remembered
        return configured

    def _on_load_finished(self, succeeded: bool) -> None:
        self._status.setText("Connected" if succeeded else "Could not load Code Map")
        self._update_navigation()

    def _on_url_changed(self, url: QUrl) -> None:
        if url.scheme() == "https" and url.host().endswith("grapuco.com"):
            self._qt_settings.setValue("lastUrl", url.toString())
        self._update_navigation()

    def _update_navigation(self) -> None:
        history = self._view.history()
        self._back.setEnabled(history.canGoBack())
        self._forward.setEnabled(history.canGoForward())

    def open_home(self) -> None:
        self._view.setUrl(QUrl(self._settings.url))

    def toggle_full_screen(self) -> None:
        self._set_full_screen(not self._full_screen)

    def _set_full_screen(self, enabled: bool) -> None:
        self._full_screen = enabled
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _handle_web_full_screen(self, request) -> None:
        request.accept()
        self._set_full_screen(request.toggleOn())

    def _escape(self) -> None:
        if self._full_screen:
            self._set_full_screen(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        super().closeEvent(event)
