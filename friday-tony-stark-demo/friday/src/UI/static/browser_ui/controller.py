from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

from friday.app.secure_browser import (
    SecureBrowserAction,
    SecureBrowserRequest,
    SecureBrowserSettings,
    get_secure_browser_command_bus,
    get_secure_browser_settings,
)
from friday.app.secure_browser.customization import install_browser_customizations
from friday.src.UI.static.browser_ui.settings_dialog import BrowserSettingsDialog
from friday.src.UI.static.browser_ui.window import SecureBrowserWindow

WindowFactory = Callable[[str], SecureBrowserWindow]
_GOOGLE_AUTH_COOKIES = {
    "APISID",
    "HSID",
    "SAPISID",
    "SID",
    "SSID",
    "__Secure-1PSID",
    "__Secure-3PSID",
}


class SecureBrowserWindowController(QObject):
    request_received = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        settings: SecureBrowserSettings | None = None,
        window_factory: WindowFactory | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings or get_secure_browser_settings()
        self._window_factory = window_factory
        self._profile: QWebEngineProfile | None = None
        self._windows: list[SecureBrowserWindow] = []
        self._settings_dialog: BrowserSettingsDialog | None = None
        self._google_auth_cookies: set[tuple[str, str]] = set()
        self._subscriber = lambda request: self.request_received.emit(request)
        self._unsubscribe = get_secure_browser_command_bus().subscribe(
            self._subscriber
        )
        self.request_received.connect(
            self._apply_request,
            Qt.ConnectionType.QueuedConnection,
        )

    @property
    def windows(self) -> tuple[SecureBrowserWindow, ...]:
        return tuple(self._windows)

    @property
    def signed_in(self) -> bool:
        return bool(self._google_auth_cookies)

    @property
    def settings_dialog(self) -> BrowserSettingsDialog | None:
        return self._settings_dialog

    def open_window(
        self,
        url: str,
        *,
        animated_query: str = "",
    ) -> SecureBrowserWindow:
        initial_url = self._settings.home_url if animated_query else url
        window = self._build_window(initial_url)
        self._windows.append(window)
        window.closed.connect(lambda: self._on_window_closed(window))
        window.showNormal()
        window.raise_()
        window.activateWindow()
        if animated_query:
            animate = getattr(window, "start_animated_search", None)
            if callable(animate):
                animate(animated_query, url)
        return window

    def close_all_windows(self) -> None:
        for window in tuple(self._windows):
            window.close()

    def close_current_window(self) -> None:
        current = self._current_window()
        if current is not None:
            current.close()

    def navigate_current_window(self, url: str) -> None:
        current = self._current_window()
        if current is None:
            self.open_window(url)
            return
        navigate = getattr(current, "navigate_to_result", None)
        if callable(navigate):
            navigate(url)

    def clear_history(self) -> None:
        profile = self._ensure_profile()
        profile.clearAllVisitedLinks()
        for window in tuple(self._windows):
            window.page.history().clear()
        if self._settings_dialog is not None:
            self._settings_dialog.show_history_cleared()

    def open_settings(self) -> None:
        if self._settings_dialog is None:
            self._settings_dialog = BrowserSettingsDialog(
                signed_in=self.signed_in,
                parent=self.parent(),
            )
            self._settings_dialog.clear_history_requested.connect(self.clear_history)
        self._settings_dialog.showNormal()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def shutdown(self) -> None:
        self._unsubscribe()
        self.close_all_windows()
        if self._settings_dialog is not None:
            self._settings_dialog.close()
            self._settings_dialog = None
        if self._profile is not None:
            self._profile.deleteLater()
            self._profile = None

    def _apply_request(self, request: object) -> None:
        if not isinstance(request, SecureBrowserRequest):
            return
        if request.action == SecureBrowserAction.OPEN:
            self.open_window(
                request.url or self._settings.home_url,
                animated_query=request.query if request.animate_query else "",
            )
        elif request.action == SecureBrowserAction.NAVIGATE_CURRENT:
            self.navigate_current_window(request.url)
        elif request.action == SecureBrowserAction.CLOSE_CURRENT:
            self.close_current_window()
        elif request.action == SecureBrowserAction.CLOSE_ALL:
            self.close_all_windows()
        elif request.action == SecureBrowserAction.CLEAR_HISTORY:
            self.clear_history()
        elif request.action == SecureBrowserAction.OPEN_SETTINGS:
            self.open_settings()

    def _build_window(self, url: str) -> SecureBrowserWindow:
        if self._window_factory is not None:
            return self._window_factory(url)
        return SecureBrowserWindow(
            profile=self._ensure_profile(),
            initial_url=url,
            popup_page_factory=self._open_popup_page,
            settings=self._settings,
            signed_in=self.signed_in,
        )

    def _open_popup_page(self) -> QWebEnginePage:
        return self.open_window("about:blank").page

    def _ensure_profile(self) -> QWebEngineProfile:
        if self._profile is not None:
            return self._profile

        storage = self._settings.profile_path / "storage"
        cache = self._settings.profile_path / "cache"
        storage.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        profile = QWebEngineProfile("friday-secure-browser", self)
        profile.setPersistentStoragePath(str(storage))
        profile.setCachePath(str(cache))
        profile.setHttpCacheType(
            QWebEngineProfile.HttpCacheType.DiskHttpCache
        )
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        install_browser_customizations(profile)
        cookie_store = profile.cookieStore()
        cookie_store.cookieAdded.connect(self._on_cookie_added)
        cookie_store.cookieRemoved.connect(self._on_cookie_removed)
        cookie_store.loadAllCookies()
        self._profile = profile
        return profile

    def _on_cookie_added(self, cookie) -> None:
        key = _google_auth_cookie_key(cookie)
        if key is None:
            return
        was_signed_in = self.signed_in
        self._google_auth_cookies.add(key)
        if not was_signed_in:
            self._update_signed_in_state()

    def _on_cookie_removed(self, cookie) -> None:
        key = _google_auth_cookie_key(cookie)
        if key is None:
            return
        was_signed_in = self.signed_in
        self._google_auth_cookies.discard(key)
        if was_signed_in != self.signed_in:
            self._update_signed_in_state()

    def _update_signed_in_state(self) -> None:
        for window in tuple(self._windows):
            window.set_signed_in(self.signed_in)
        if self._settings_dialog is not None:
            self._settings_dialog.set_signed_in(self.signed_in)

    def _on_window_closed(self, window: SecureBrowserWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)

    def _current_window(self) -> SecureBrowserWindow | None:
        if not self._windows:
            return None
        return next(
            (window for window in reversed(self._windows) if window.isActiveWindow()),
            self._windows[-1],
        )


def _google_auth_cookie_key(cookie) -> tuple[str, str] | None:
    domain = str(cookie.domain() or "").lower().lstrip(".")
    name = bytes(cookie.name()).decode("utf-8", errors="ignore")
    if not domain.endswith("google.com") or name not in _GOOGLE_AUTH_COOKIES:
        return None
    return domain, name
