from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Protocol

from friday.app.messenger.bridge import MessengerExtensionBridge
from friday.app.messenger.chrome_profile import ChromeProfileLaunchError, ChromeProfileLauncher
from friday.app.messenger.schemas import MessengerConversationPreview


MESSENGER_URL = "https://www.messenger.com/"
DEFAULT_PROFILE_DIR = Path(__file__).resolve().parents[2] / "log" / "runtime" / "messenger_chrome_profile"
_UNREAD_LABEL_TOKENS = (
    "unread",
    "new message",
    "mark as read",
    "chua doc",
    "tin nhan moi",
    "danh dau la da doc",
)
_IGNORED_LINES = {
    "active now",
    "dang hoat dong",
    "more",
    "xem them",
    "open chat",
    "mo doan chat",
    "profile picture",
    "anh dai dien",
    "react",
}
_TIME_PATTERN = re.compile(
    r"^(?:\d{1,2}:\d{2}(?:\s*[ap]m)?|\d+\s*(?:m|h|d|min|hr|day)s?|"
    r"\d+\s*(?:phut|gio|ngay|tuan)|hom qua|hom nay|t[2-7]|cn|"
    r"yesterday|today|mon|tue|wed|thu|fri|sat|sun)$",
    re.IGNORECASE,
)


class MessengerReader(Protocol):
    def read_latest(self) -> MessengerConversationPreview | None: ...


class MessengerLoginRequired(RuntimeError):
    pass


class MessengerBrowserError(RuntimeError):
    pass


class ExtensionMessengerReader:
    def __init__(
        self,
        *,
        bridge: MessengerExtensionBridge | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.bridge = bridge or MessengerExtensionBridge()
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else _env_float("FRIDAY_MESSENGER_EXTENSION_TIMEOUT", 20.0)
        )

    def read_latest(self) -> MessengerConversationPreview | None:
        request_id = self.bridge.request_scan()
        try:
            return self.bridge.wait_for_latest(
                request_id,
                timeout_seconds=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise MessengerBrowserError(
                "I could not reach the FRIDAY Messenger bridge. Start friday-api and "
                "enable the unpacked extension in the configured Chrome profile."
            ) from exc


class ChromeProfileMessengerReader(ExtensionMessengerReader):
    def __init__(
        self,
        *,
        launcher: ChromeProfileLauncher | None = None,
        bridge: MessengerExtensionBridge | None = None,
        timeout_seconds: float | None = None,
        launch_delay: float | None = None,
    ) -> None:
        super().__init__(bridge=bridge, timeout_seconds=timeout_seconds)
        self.launcher = launcher or ChromeProfileLauncher()
        self.launch_delay = (
            launch_delay
            if launch_delay is not None
            else _env_float("FRIDAY_MESSENGER_PROFILE_LAUNCH_DELAY", 2.0)
        )

    def read_latest(self) -> MessengerConversationPreview | None:
        try:
            self.launcher.open_messenger()
        except ChromeProfileLaunchError as exc:
            raise MessengerBrowserError(str(exc)) from exc
        time.sleep(max(0.0, self.launch_delay))
        return super().read_latest()


class PlaywrightMessengerReader:
    def __init__(
        self,
        *,
        profile_dir: Path | None = None,
        login_wait_seconds: float | None = None,
    ) -> None:
        configured_profile = os.getenv("FRIDAY_MESSENGER_PROFILE_DIR", "").strip()
        self.profile_dir = profile_dir or (
            Path(configured_profile).expanduser() if configured_profile else DEFAULT_PROFILE_DIR
        )
        self.login_wait_seconds = (
            login_wait_seconds
            if login_wait_seconds is not None
            else _env_float("FRIDAY_MESSENGER_LOGIN_WAIT_SECONDS", 90.0)
        )

    def read_latest(self) -> MessengerConversationPreview | None:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise MessengerBrowserError(
                "Messenger reading requires Playwright. Run 'uv sync' and restart FRIDAY."
            ) from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir.resolve()),
                    channel=os.getenv("FRIDAY_MESSENGER_BROWSER_CHANNEL", "chrome").strip() or "chrome",
                    headless=False,
                    viewport=None,
                    args=["--start-maximized"],
                )
                try:
                    page = _messenger_page(context.pages) or context.new_page()
                    page.goto(MESSENGER_URL, wait_until="domcontentloaded", timeout=45_000)
                    self._wait_for_login(page)
                    page.wait_for_timeout(2_000)
                    return self._read_conversation_rows(page)
                finally:
                    context.close()
        except MessengerLoginRequired:
            raise
        except (PlaywrightError, PlaywrightTimeoutError) as exc:
            raise MessengerBrowserError(
                "I could not read Messenger from the FRIDAY Chrome profile."
            ) from exc

    def _wait_for_login(self, page) -> None:
        if not _login_required(page):
            return
        deadline = time.monotonic() + max(0.0, self.login_wait_seconds)
        while time.monotonic() < deadline:
            page.wait_for_timeout(1_000)
            if not _login_required(page):
                page.wait_for_load_state("domcontentloaded", timeout=15_000)
                return
        raise MessengerLoginRequired(
            "I opened a private FRIDAY Messenger window. Sign in there once, then ask me to check Messenger again."
        )

    def _read_conversation_rows(self, page) -> MessengerConversationPreview | None:
        locator = page.locator('a[href*="/t/"]')
        candidates: list[MessengerConversationPreview] = []
        seen_urls: set[str] = set()
        for index in range(min(locator.count(), 40)):
            row = locator.nth(index)
            try:
                if not row.is_visible(timeout=500):
                    continue
                url = str(row.get_attribute("href") or "").strip()
                if not url or url in seen_urls:
                    continue
                text = row.inner_text(timeout=1_000)
                labels = row.locator("[aria-label]").evaluate_all(
                    "elements => elements.map(element => element.getAttribute('aria-label') || '')"
                )
            except Exception:
                continue
            preview = parse_conversation_row(text, labels=labels, url=url)
            if preview is None:
                continue
            seen_urls.add(url)
            candidates.append(preview)

        if not candidates:
            return None
        return next((item for item in candidates if item.unread), candidates[0])


def parse_conversation_row(
    text: str,
    *,
    labels: list[str] | tuple[str, ...] = (),
    url: str = "",
) -> MessengerConversationPreview | None:
    lines = []
    for raw_line in str(text or "").splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line or _normalize_ascii(line) in _IGNORED_LINES or line in lines:
            continue
        lines.append(line)
    if not lines:
        return None

    sender = lines[0]
    timestamp = next(
        (line for line in lines[1:] if _TIME_PATTERN.fullmatch(_normalize_ascii(line))),
        "",
    )
    preview_parts = [line for line in lines[1:] if line != timestamp]
    preview = " ".join(preview_parts).strip()
    if not preview:
        preview = "No text preview is available."

    normalized_labels = _normalize_ascii(" ".join(str(label or "") for label in labels))
    unread = any(token in normalized_labels for token in _UNREAD_LABEL_TOKENS)
    return MessengerConversationPreview(
        sender=sender,
        preview=preview,
        timestamp=timestamp,
        unread=unread,
        url=url,
    )


def _messenger_page(pages):
    return next((page for page in pages if "messenger.com" in page.url.lower()), None)


def _login_required(page) -> bool:
    url = page.url.lower()
    if "login" in url:
        return True
    return page.locator('input[name="email"], input[name="pass"]').count() > 0


def _normalize_ascii(value: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize(
        "NFD",
        value.replace("\u0110", "D").replace("\u0111", "d"),
    )
    return " ".join(
        "".join(character for character in decomposed if unicodedata.category(character) != "Mn")
        .lower()
        .split()
    )


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except ValueError:
        return default
