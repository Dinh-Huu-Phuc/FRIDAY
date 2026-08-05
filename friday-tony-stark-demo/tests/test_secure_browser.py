from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PySide6.QtCore import QEventLoop, QObject, QTimer, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtWidgets import QApplication

from friday.app.secure_browser import (
    FRIDAY_HOME_URL,
    SecureBrowserAction,
    SecureBrowserCommandBus,
    SecureBrowserRequest,
    SecureBrowserSettings,
    get_secure_browser_command_bus,
    handle_secure_browser_message,
    match_secure_browser_intent,
    navigation_url,
)
from friday.app.secure_browser.customization import (
    GOOGLE_SEARCH_BRAND_SCRIPT_NAME,
    PLATFORM_VIDEO_SCRIPT_NAME,
    build_google_search_brand_script,
    build_platform_video_script,
    install_google_search_branding,
    is_google_search_url,
)
from friday.src.UI.static.browser_ui.controller import (
    SecureBrowserWindowController,
)
from friday.src.UI.static.browser_ui.window import SecureBrowserWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _FakeBrowserWindow(QObject):
    closed = Signal()

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self.show_count = 0
        self.raise_count = 0
        self.activate_count = 0
        self.close_count = 0
        self.active = False
        self.animated_searches: list[tuple[str, str]] = []
        self.result_urls: list[str] = []

    def showNormal(self) -> None:
        self.show_count += 1

    def raise_(self) -> None:
        self.raise_count += 1

    def activateWindow(self) -> None:
        self.activate_count += 1

    def isActiveWindow(self) -> bool:
        return self.active

    def start_animated_search(self, query: str, url: str) -> None:
        self.animated_searches.append((query, url))

    def navigate_to_result(self, url: str) -> None:
        self.result_urls.append(url)

    def close(self) -> None:
        self.close_count += 1
        self.closed.emit()


def _settings(tmp_path: Path) -> SecureBrowserSettings:
    return SecureBrowserSettings(
        enabled=True,
        home_url=FRIDAY_HOME_URL,
        profile_path=tmp_path / "profile",
        icon_path=tmp_path / "Friday.jpg",
    )


def _load_html(page: QWebEnginePage, html: str, url: str) -> None:
    loop = QEventLoop()
    page.loadFinished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    page.setHtml(html, QUrl(url))
    loop.exec()


def _javascript_value(page: QWebEnginePage, source: str):
    result: list[object] = []
    loop = QEventLoop()

    def receive(value: object) -> None:
        result.append(value)
        loop.quit()

    QTimer.singleShot(5000, loop.quit)
    page.runJavaScript(source, receive)
    loop.exec()
    assert result, "JavaScript result timed out"
    return result[0]


def test_secure_browser_intents_cover_all_supported_commands() -> None:
    home = match_secure_browser_intent("FRIDAY, open the browser.")
    assert home.action == SecureBrowserAction.OPEN
    assert home.url == FRIDAY_HOME_URL

    search = match_secure_browser_intent("FRIDAY, search Tony Stark.")
    assert search.action == SecureBrowserAction.OPEN
    assert search.query == "Tony Stark"
    assert parse_qs(urlparse(search.url).query)["q"] == ["Tony Stark"]
    assert match_secure_browser_intent("Look up Tony Stark.").action == (
        SecureBrowserAction.NONE
    )

    target = match_secure_browser_intent(
        "FRIDAY open secure browser to youtube.com."
    )
    assert target.url == "https://youtube.com"

    current = match_secure_browser_intent("FRIDAY, close this browser window.")
    assert current.action == SecureBrowserAction.CLOSE_CURRENT
    close_all = match_secure_browser_intent("FRIDAY, close all browser windows.")
    assert close_all.action == SecureBrowserAction.CLOSE_ALL
    clear = match_secure_browser_intent("FRIDAY, clear browser history.")
    assert clear.action == SecureBrowserAction.CLEAR_HISTORY
    settings = match_secure_browser_intent("FRIDAY, open browser settings.")
    assert settings.action == SecureBrowserAction.OPEN_SETTINGS
    assert match_secure_browser_intent("open browser in Chrome").action == (
        SecureBrowserAction.NONE
    )


def test_navigation_bar_accepts_urls_and_turns_plain_text_into_search() -> None:
    assert navigation_url("https://example.com/path") == "https://example.com/path"
    assert navigation_url("example.com") == "https://example.com"
    search_url = navigation_url("latest artificial intelligence news")
    assert parse_qs(urlparse(search_url).query)["q"] == [
        "latest artificial intelligence news"
    ]


def test_google_branding_only_matches_public_search_results() -> None:
    assert is_google_search_url("https://www.google.com/search?q=Tony+Stark")
    assert is_google_search_url("https://google.com/search/?q=AI")
    assert not is_google_search_url("http://www.google.com/search?q=AI")
    assert not is_google_search_url("https://www.google.com/")
    assert not is_google_search_url("https://accounts.google.com/search?q=AI")
    assert not is_google_search_url("https://consent.google.com/search?q=AI")
    assert not is_google_search_url("https://example.com/search?q=AI")


def test_google_brand_script_has_safe_profile_configuration() -> None:
    script = build_google_search_brand_script()
    assert script.name() == GOOGLE_SEARCH_BRAND_SCRIPT_NAME
    assert script.injectionPoint() == QWebEngineScript.InjectionPoint.DocumentReady
    assert script.worldId() == QWebEngineScript.ScriptWorldId.ApplicationWorld
    assert not script.runsOnSubFrames()
    assert "__FRIDAY_GOOGLE_BRAND_CSS__" not in script.sourceCode()
    assert "accounts.google.com" not in script.sourceCode()


def test_platform_video_script_is_isolated_and_requires_explicit_rank() -> None:
    script = build_platform_video_script()
    assert script.name() == PLATFORM_VIDEO_SCRIPT_NAME
    assert script.injectionPoint() == QWebEngineScript.InjectionPoint.DocumentReady
    assert script.worldId() == QWebEngineScript.ScriptWorldId.ApplicationWorld
    assert not script.runsOnSubFrames()
    assert "friday_play" in script.sourceCode()
    assert "slice(0, 3)" in script.sourceCode()


def test_google_brand_script_replaces_search_logo_in_chromium(tmp_path: Path) -> None:
    app = _app()
    profile = QWebEngineProfile("friday-brand-test", app)
    profile.setPersistentStoragePath(str(tmp_path / "brand-storage"))
    profile.setCachePath(str(tmp_path / "brand-cache"))
    install_google_search_branding(profile)
    install_google_search_branding(profile)
    scripts = profile.scripts()
    assert len(scripts.toList()) == 1

    page = QWebEnginePage(profile)
    try:
        _load_html(
            page,
            "<html><head></head><body><a id='logo' href='/webhp'>"
            "<span id='google-mark'>Google</span></a></body></html>",
            "https://www.google.com/search?q=Tony+Stark",
        )
        result = _javascript_value(
            page,
            "JSON.stringify({"
            "brand: document.querySelector('#friday-search-brand')?.textContent,"
            "hidden: document.querySelector('#google-mark')?.classList.contains("
            "'friday-original-google-brand'),"
            "label: document.querySelector('#logo')?.getAttribute('aria-label')"
            "})",
        )
        assert result == (
            '{"brand":"FRIDAY","hidden":true,'
            '"label":"FRIDAY Search home"}'
        )
    finally:
        page.deleteLater()
        app.processEvents()
        profile.deleteLater()
        app.processEvents()


def test_command_bus_dispatches_and_unsubscribes() -> None:
    bus = SecureBrowserCommandBus()
    received: list[SecureBrowserRequest] = []
    unsubscribe = bus.subscribe(received.append)
    request = SecureBrowserRequest(
        SecureBrowserAction.OPEN,
        "https://example.com",
    )

    assert bus.dispatch(request)
    unsubscribe()
    assert not bus.dispatch(
        SecureBrowserRequest(SecureBrowserAction.CLOSE_ALL)
    )
    assert received == [request]


def test_service_dispatches_open_request_to_running_desktop(monkeypatch) -> None:
    received: list[SecureBrowserRequest] = []
    unsubscribe = get_secure_browser_command_bus().subscribe(received.append)
    monkeypatch.setattr(
        "friday.app.secure_browser.service.get_secure_browser_settings",
        lambda: SecureBrowserSettings(
            True,
            FRIDAY_HOME_URL,
            Path("profile"),
            Path("Friday.jpg"),
        ),
    )
    try:
        result = handle_secure_browser_message(
            "FRIDAY search current weather in FRIDAY browser"
        )
    finally:
        unsubscribe()

    assert result.handled
    assert result.accepted
    assert result.action == SecureBrowserAction.OPEN
    assert len(received) == 1
    assert received[0].query == "current weather"


def test_controller_manages_current_and_all_browser_windows(
    tmp_path: Path,
) -> None:
    app = _app()
    windows: list[_FakeBrowserWindow] = []

    def build_window(url: str) -> _FakeBrowserWindow:
        window = _FakeBrowserWindow(url)
        windows.append(window)
        return window

    controller = SecureBrowserWindowController(
        settings=_settings(tmp_path),
        window_factory=build_window,
    )
    bus = get_secure_browser_command_bus()
    try:
        assert bus.dispatch(
            SecureBrowserRequest(
                SecureBrowserAction.OPEN,
                "https://example.com/one",
            )
        )
        assert bus.dispatch(
            SecureBrowserRequest(
                SecureBrowserAction.OPEN,
                "https://example.com/two",
            )
        )
        app.processEvents()

        assert [window.url for window in windows] == [
            "https://example.com/one",
            "https://example.com/two",
        ]
        assert len(controller.windows) == 2
        assert all(window.show_count == 1 for window in windows)

        windows[-1].active = True
        assert bus.dispatch(SecureBrowserRequest(SecureBrowserAction.CLOSE_CURRENT))
        app.processEvents()
        assert windows[0].close_count == 0
        assert windows[1].close_count == 1
        assert len(controller.windows) == 1

        assert bus.dispatch(SecureBrowserRequest(SecureBrowserAction.CLOSE_ALL))
        app.processEvents()
        assert windows[0].close_count == 1
        assert controller.windows == ()
    finally:
        controller.shutdown()

    assert not bus.dispatch(
        SecureBrowserRequest(SecureBrowserAction.OPEN)
    )


def test_controller_animates_search_then_navigates_same_window(
    tmp_path: Path,
) -> None:
    app = _app()
    windows: list[_FakeBrowserWindow] = []

    def build_window(url: str) -> _FakeBrowserWindow:
        window = _FakeBrowserWindow(url)
        windows.append(window)
        return window

    controller = SecureBrowserWindowController(
        settings=_settings(tmp_path),
        window_factory=build_window,
    )
    bus = get_secure_browser_command_bus()
    try:
        search_url = "https://www.google.com/search?q=Tony+Stark"
        assert bus.dispatch(
            SecureBrowserRequest(
                SecureBrowserAction.OPEN,
                search_url,
                query="Tony Stark",
                animate_query=True,
            )
        )
        app.processEvents()
        assert len(windows) == 1
        assert windows[0].url == FRIDAY_HOME_URL
        assert windows[0].animated_searches == [("Tony Stark", search_url)]

        result_url = "https://example.com/tony-stark"
        assert bus.dispatch(
            SecureBrowserRequest(
                SecureBrowserAction.NAVIGATE_CURRENT,
                result_url,
            )
        )
        app.processEvents()
        assert windows[0].result_urls == [result_url]
        assert len(controller.windows) == 1
    finally:
        controller.shutdown()
        app.processEvents()


def test_controller_opens_settings_and_clears_history(tmp_path: Path) -> None:
    app = _app()
    controller = SecureBrowserWindowController(settings=_settings(tmp_path))
    bus = get_secure_browser_command_bus()
    try:
        assert bus.dispatch(SecureBrowserRequest(SecureBrowserAction.OPEN_SETTINGS))
        app.processEvents()
        assert controller.settings_dialog is not None
        assert controller.settings_dialog.isVisible()

        assert bus.dispatch(SecureBrowserRequest(SecureBrowserAction.CLEAR_HISTORY))
        app.processEvents()
        assert "history cleared" in controller.settings_dialog.status_text.lower()
    finally:
        controller.shutdown()
        app.processEvents()


def test_real_chromium_window_builds_with_friday_identity(
    tmp_path: Path,
) -> None:
    app = _app()
    project_root = Path(__file__).resolve().parents[1]
    settings = SecureBrowserSettings(
        enabled=True,
        home_url=FRIDAY_HOME_URL,
        profile_path=tmp_path / "profile",
        icon_path=project_root / "friday" / "assets" / "img" / "Friday.jpg",
    )
    profile = QWebEngineProfile("friday-browser-test", app)
    profile.setPersistentStoragePath(str(tmp_path / "storage"))
    profile.setCachePath(str(tmp_path / "cache"))
    window = SecureBrowserWindow(
        profile=profile,
        initial_url="about:blank",
        popup_page_factory=lambda: window.page,
        settings=settings,
    )
    try:
        window.show()
        app.processEvents()
        assert window.windowTitle() == "FRIDAY Browser"
        assert not window.windowIcon().isNull()
        assert window.findChild(QObject, "addressBar") is not None
        assert window.findChild(QObject, "profileAvatar") is not None
    finally:
        window.close()
        app.processEvents()
        profile.deleteLater()
        app.processEvents()
