from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QSizePolicy,
    QStyle,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from friday.app.secure_browser.navigation import FRIDAY_HOME_URL, navigation_url
from friday.app.secure_browser.settings import (
    SecureBrowserSettings,
    get_secure_browser_settings,
)
from friday.src.UI.static.browser_ui.theme import SECURE_BROWSER_STYLESHEET

HOME_PAGE = Path(__file__).with_name("home.html")


class SecureBrowserPage(QWebEnginePage):
    def __init__(
        self,
        profile: QWebEngineProfile,
        *,
        popup_page_factory: Callable[[], QWebEnginePage],
        parent=None,
    ) -> None:
        super().__init__(profile, parent)
        self._popup_page_factory = popup_page_factory

    def createWindow(self, _window_type) -> QWebEnginePage:
        return self._popup_page_factory()


class SecureBrowserWindow(QMainWindow):
    closed = Signal()

    def __init__(
        self,
        *,
        profile: QWebEngineProfile,
        initial_url: str,
        popup_page_factory: Callable[[], QWebEnginePage],
        settings: SecureBrowserSettings | None = None,
        signed_in: bool = False,
    ) -> None:
        super().__init__()
        self._settings = settings or get_secure_browser_settings()
        self._signed_in = bool(signed_in)
        self._shortcuts: list[QShortcut] = []
        self._typed_query = ""
        self._typed_index = 0
        self._search_target_url = ""
        self._follow_up_url = ""
        self._typing_active = False
        self._search_timer = QTimer(self)
        self._search_timer.setInterval(55)
        self._search_timer.timeout.connect(self._type_next_search_character)
        self._search_launch_timer = QTimer(self)
        self._search_launch_timer.setSingleShot(True)
        self._search_launch_timer.setInterval(180)
        self._search_launch_timer.timeout.connect(self._open_search_results)
        self._follow_up_timer = QTimer(self)
        self._follow_up_timer.setSingleShot(True)
        self._follow_up_timer.setInterval(1800)
        self._follow_up_timer.timeout.connect(self._open_follow_up_result)

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("FRIDAY Browser")
        self.setMinimumSize(920, 620)
        self.resize(1420, 900)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(SECURE_BROWSER_STYLESHEET)
        if self._settings.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self._settings.icon_path)))

        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        self._page = SecureBrowserPage(
            profile,
            popup_page_factory=popup_page_factory,
            parent=self,
        )
        self._view = QWebEngineView(self)
        self._view.setPage(self._page)

        self._toolbar = self._build_toolbar()
        root_layout.addWidget(self._toolbar)
        self._progress = QProgressBar(self)
        self._progress.setObjectName("loadProgress")
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.hide()
        root_layout.addWidget(self._progress)
        root_layout.addWidget(self._view, 1)

        self._connect_signals()
        self._add_shortcut(QKeySequence.StandardKey.Close, self.close)
        self._add_shortcut(QKeySequence.StandardKey.Refresh, self._view.reload)
        self._add_shortcut(QKeySequence("Ctrl+L"), self._focus_address)
        self.set_signed_in(self._signed_in)
        self._navigate(initial_url)

    @property
    def page(self) -> QWebEnginePage:
        return self._page

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("FRIDAY Browser controls", self)
        toolbar.setObjectName("browserToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(18, 18))

        brand = QLabel("FRIDAY")
        brand.setObjectName("browserBrand")
        toolbar.addWidget(brand)

        self._back = self._navigation_button(
            QStyle.StandardPixmap.SP_ArrowBack,
            "Back",
            self._view.back,
        )
        self._forward = self._navigation_button(
            QStyle.StandardPixmap.SP_ArrowForward,
            "Forward",
            self._view.forward,
        )
        toolbar.addWidget(self._back)
        toolbar.addWidget(self._forward)
        toolbar.addWidget(
            self._navigation_button(
                QStyle.StandardPixmap.SP_BrowserReload,
                "Reload",
                self._view.reload,
            )
        )

        self._address = QLineEdit(self)
        self._address.setObjectName("addressBar")
        self._address.setClearButtonEnabled(True)
        self._address.setPlaceholderText("Search or enter an address")
        self._address.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._address.returnPressed.connect(self._navigate_from_address)
        toolbar.addWidget(self._address)

        self._avatar = QToolButton(self)
        self._avatar.setObjectName("profileAvatar")
        self._avatar.setText(_account_initial())
        self._avatar.setToolTip("Open Google account")
        self._avatar.clicked.connect(self._open_google_account)
        toolbar.addWidget(self._avatar)
        return toolbar

    def _navigation_button(self, icon_name, tooltip: str, callback) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("navigationButton")
        button.setIcon(self.style().standardIcon(icon_name))
        button.setToolTip(tooltip)
        button.setFixedSize(34, 34)
        button.clicked.connect(callback)
        return button

    def _connect_signals(self) -> None:
        self._view.loadStarted.connect(self._on_load_started)
        self._view.loadProgress.connect(self._on_load_progress)
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.urlChanged.connect(self._on_url_changed)
        self._view.titleChanged.connect(self._on_title_changed)

    def _add_shortcut(self, key, callback) -> None:
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)

    def _navigate_from_address(self) -> None:
        self._navigate(self._address.text())

    def _navigate(self, value: str) -> None:
        target = navigation_url(value)
        if target == FRIDAY_HOME_URL and HOME_PAGE.is_file():
            self._view.setUrl(QUrl.fromLocalFile(str(HOME_PAGE)))
            return
        self._view.setUrl(QUrl(target))

    def _focus_address(self) -> None:
        self._address.setFocus()
        self._address.selectAll()

    def start_animated_search(self, query: str, target_url: str) -> None:
        self._typed_query = " ".join(str(query or "").split()).strip()
        self._typed_index = 0
        self._search_target_url = str(target_url or "").strip()
        self._typing_active = bool(self._typed_query and self._search_target_url)
        if not self._typing_active:
            self._navigate(self._search_target_url)
            return
        self._address.clear()
        self._address.setPlaceholderText("FRIDAY is searching...")
        self._search_timer.start()

    def navigate_to_result(self, url: str) -> None:
        target = str(url or "").strip()
        if not target:
            return
        if (
            self._typing_active
            or self._search_launch_timer.isActive()
            or self._is_google_search_page()
        ):
            self._follow_up_url = target
            self._schedule_follow_up_if_ready()
            return
        self._navigate(target)

    def _type_next_search_character(self) -> None:
        if self._typed_index < len(self._typed_query):
            self._typed_index += 1
            self._address.setText(self._typed_query[: self._typed_index])
            self._address.setCursorPosition(self._typed_index)
            return

        self._search_timer.stop()
        self._typing_active = False
        self._address.setPlaceholderText("Search or enter an address")
        self._search_launch_timer.start()

    def _open_search_results(self) -> None:
        self._navigate(self._search_target_url)

    def _is_google_search_page(self) -> bool:
        url = self._view.url()
        return (
            url.scheme().lower() == "https"
            and url.host().lower() in {"google.com", "www.google.com"}
            and url.path().rstrip("/") == "/search"
        )

    def _schedule_follow_up_if_ready(self) -> None:
        if (
            self._follow_up_url
            and self._is_google_search_page()
            and not self._follow_up_timer.isActive()
        ):
            self._follow_up_timer.start()

    def _open_follow_up_result(self) -> None:
        target = self._follow_up_url
        self._follow_up_url = ""
        if target:
            self._navigate(target)

    def _open_google_account(self) -> None:
        self._view.setUrl(QUrl("https://myaccount.google.com/"))

    def _on_load_started(self) -> None:
        self._progress.setValue(0)
        self._progress.show()

    def _on_load_progress(self, progress: int) -> None:
        self._progress.setValue(progress)

    def _on_load_finished(self, _succeeded: bool) -> None:
        self._progress.hide()
        self._update_navigation()
        self._schedule_follow_up_if_ready()

    def _on_url_changed(self, url: QUrl) -> None:
        is_home = (
            url.isLocalFile()
            and Path(url.toLocalFile()).resolve() == HOME_PAGE.resolve()
        )
        if not self._typing_active:
            self._address.setText("" if is_home else url.toDisplayString())
            self._address.setCursorPosition(0)
        self._update_navigation()

    def _on_title_changed(self, title: str) -> None:
        clean_title = " ".join(str(title or "").split()).strip()
        self.setWindowTitle(
            f"{clean_title} | FRIDAY Browser"
            if clean_title
            else "FRIDAY Browser"
        )

    def _update_navigation(self) -> None:
        history = self._view.history()
        self._back.setEnabled(history.canGoBack())
        self._forward.setEnabled(history.canGoForward())

    def set_signed_in(self, signed_in: bool) -> None:
        self._signed_in = bool(signed_in)
        self._avatar.setProperty("signedIn", "true" if self._signed_in else "false")
        self._avatar.setToolTip(
            "Google account session is available"
            if self._signed_in
            else "Open Google account and sign in once"
        )
        self._avatar.style().unpolish(self._avatar)
        self._avatar.style().polish(self._avatar)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        super().closeEvent(event)


def _account_initial() -> str:
    email = os.getenv("GMAIL", "").strip()
    local_name = email.partition("@")[0].strip()
    return (local_name[:1] or "F").upper()
