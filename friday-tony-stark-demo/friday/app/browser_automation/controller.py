from __future__ import annotations

import ctypes
import json
import os
import time
from ctypes import wintypes
from typing import Protocol

from friday.app.windows_launcher.service import open_app
from friday.tools.computer import keyboard as keyboard_tools


SW_RESTORE = 9
CHROME_WINDOW_CLASS = "Chrome_WidgetWin_1"
PLATFORM_HOME_URLS = {
    "youtube": "https://www.youtube.com/",
    "tiktok": "https://www.tiktok.com/",
}
PLATFORM_VIDEO_SELECTORS = {
    "youtube": "ytd-video-renderer a#video-title[href]",
    "tiktok": "main a[href*='/video/']",
}
TIKTOK_SEARCH_FOCUS_SCRIPT = (
    "javascript:(()=>{const e=document.querySelector("
    "\"input[type='search'],input[placeholder*='Search' i],"
    "input[data-e2e*='search']\");if(e){e.focus();e.select()}})()"
)


class BrowserControlError(RuntimeError):
    pass


class ChromeBackend(Protocol):
    def ensure_chrome(self) -> bool: ...
    def is_chrome_active(self) -> bool: ...
    def hotkey(self, *keys: str) -> None: ...
    def type_text(self, text: str, interval: float) -> None: ...
    def press(self, key: str) -> None: ...
    def wait(self, seconds: float) -> None: ...


class Win32ChromeBackend:
    def __init__(self) -> None:
        if os.name != "nt":
            raise BrowserControlError("Chrome automation is available only on Windows.")
        self.user32 = ctypes.windll.user32

    def _class_name(self, hwnd: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def _find_chrome_window(self) -> int:
        foreground = int(self.user32.GetForegroundWindow())
        if (
            foreground
            and self.user32.IsWindowVisible(foreground)
            and self._class_name(foreground) == CHROME_WINDOW_CLASS
        ):
            return foreground

        handles: list[int] = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def callback(hwnd: int, _: int) -> bool:
            if self.user32.IsWindowVisible(hwnd) and self._class_name(hwnd) == CHROME_WINDOW_CLASS:
                handles.append(int(hwnd))
                return False
            return True

        self.user32.EnumWindows(callback, 0)
        return handles[0] if handles else 0

    def _focus(self, hwnd: int) -> bool:
        if not hwnd:
            return False
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindowAsync(hwnd, SW_RESTORE)
        self.user32.SetForegroundWindow(hwnd)
        for _ in range(20):
            if int(self.user32.GetForegroundWindow()) == int(hwnd):
                return True
            time.sleep(0.1)
        return False

    def ensure_chrome(self) -> bool:
        hwnd = self._find_chrome_window()
        if hwnd and self._focus(hwnd):
            return True

        launched = open_app(query="Google Chrome")
        if not launched.ok:
            launched = open_app(query="Chrome")
        if not launched.ok:
            return False

        for _ in range(40):
            time.sleep(0.2)
            hwnd = self._find_chrome_window()
            if hwnd and self._focus(hwnd):
                return True
        return False

    def is_chrome_active(self) -> bool:
        hwnd = int(self.user32.GetForegroundWindow())
        return bool(hwnd) and self._class_name(hwnd) == CHROME_WINDOW_CLASS

    def hotkey(self, *keys: str) -> None:
        keyboard_tools.hotkey(*keys)

    def type_text(self, text: str, interval: float) -> None:
        keyboard_tools.type_text(text, interval=interval)

    def press(self, key: str) -> None:
        keyboard_tools.press(key)

    def wait(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds))


class ChromeController:
    def __init__(
        self,
        *,
        backend: ChromeBackend | None = None,
        type_interval: float | None = None,
        step_delay: float | None = None,
        page_delay: float | None = None,
        platform_load_delay: float | None = None,
        result_delay: float | None = None,
    ) -> None:
        self.backend = backend or Win32ChromeBackend()
        self.type_interval = type_interval if type_interval is not None else _env_float("FRIDAY_BROWSER_TYPE_INTERVAL", 0.035)
        self.step_delay = step_delay if step_delay is not None else _env_float("FRIDAY_BROWSER_STEP_DELAY", 0.2)
        self.page_delay = page_delay if page_delay is not None else _env_float("FRIDAY_BROWSER_PAGE_DELAY", 1.2)
        self.platform_load_delay = platform_load_delay if platform_load_delay is not None else _env_float("FRIDAY_PLATFORM_LOAD_DELAY", 4.0)
        self.result_delay = result_delay if result_delay is not None else _env_float("FRIDAY_PLATFORM_RESULT_DELAY", 3.0)

    def _require_focus(self) -> None:
        if not self.backend.is_chrome_active():
            raise BrowserControlError(
                "Chrome lost focus, so I stopped before typing into the wrong application."
            )

    def search_in_new_tab(self, query: str) -> None:
        if not self.backend.ensure_chrome():
            raise BrowserControlError("I could not find or start Google Chrome.")
        self._require_focus()
        self.backend.hotkey("ctrl", "t")
        self.backend.wait(self.step_delay)
        self._require_focus()
        self.backend.type_text(query, interval=self.type_interval)
        self._require_focus()
        self.backend.press("enter")
        self.backend.wait(self.page_delay)
        self._require_focus()

    def open_url(self, url: str) -> None:
        self._require_focus()
        self.backend.hotkey("ctrl", "l")
        self.backend.wait(self.step_delay)
        self._require_focus()
        self.backend.type_text(url, interval=min(self.type_interval, 0.01))
        self._require_focus()
        self.backend.press("enter")
        self.backend.wait(self.page_delay)
        self._require_focus()

    def search_platform_videos(
        self,
        *,
        platform: str,
        query: str,
        result_index: int,
    ) -> None:
        if platform not in PLATFORM_HOME_URLS:
            raise BrowserControlError("That video platform is not supported.")
        if not self.backend.ensure_chrome():
            raise BrowserControlError("I could not find or start Google Chrome.")

        self._open_new_tab_url(PLATFORM_HOME_URLS[platform])
        self.backend.wait(self.platform_load_delay)
        if platform == "youtube":
            self._focus_youtube_search()
        else:
            self._run_javascript(TIKTOK_SEARCH_FOCUS_SCRIPT, wait_after=self.step_delay)

        self._require_focus()
        self.backend.hotkey("ctrl", "a")
        self.backend.type_text(query, interval=self.type_interval)
        self._require_focus()
        self.backend.press("enter")
        self.backend.wait(self.result_delay)
        self._require_focus()

        selector = PLATFORM_VIDEO_SELECTORS[platform]
        safe_index = max(0, min(2, int(result_index)))
        select_script = (
            "javascript:(()=>{const a=[...new Map([...document.querySelectorAll(\""
            f"{selector}"
            "\")].filter(e=>e.href).map(e=>[e.href,e])).values()].slice(0,3);"
            f"if(a.length)location.href=a[{safe_index}%a.length].href"
            "})()"
        )
        self._run_javascript(select_script, wait_after=self.page_delay)

    def open_binance_market(
        self,
        *,
        overview_url: str,
        trade_url: str,
        symbol: str,
        asset_name: str,
    ) -> None:
        if not self.backend.ensure_chrome():
            raise BrowserControlError("I could not find or start Google Chrome.")

        self._open_new_tab_url(overview_url)
        self.backend.wait(self.platform_load_delay)
        symbol_json = json.dumps(symbol.upper())
        name_json = json.dumps(asset_name.upper())
        click_script = (
            "javascript:(()=>{const s=" + symbol_json + ",n=" + name_json + ";"
            "const a=[...document.querySelectorAll('a[href]')];"
            "const e=a.find(x=>x.href.toUpperCase().includes('/TRADE/'+s+'_'))||"
            "a.find(x=>{const t=(x.innerText||x.textContent||'').trim().toUpperCase();"
            "return t===s||t.startsWith(s+'\\n')||t.includes(n)});"
            "if(e){e.scrollIntoView({block:'center'});e.click()}})()"
        )
        self._run_javascript(click_script, wait_after=self.result_delay)
        self._open_new_tab_url(trade_url)
        self.backend.wait(self.platform_load_delay)

    def _focus_youtube_search(self) -> None:
        self._require_focus()
        self.backend.press("esc")
        self.backend.wait(self.step_delay)
        self._require_focus()
        self.backend.type_text("/", interval=0.0)
        self.backend.wait(self.step_delay)

    def _open_new_tab_url(self, url: str) -> None:
        self._require_focus()
        self.backend.hotkey("ctrl", "t")
        self.backend.wait(self.step_delay)
        self._require_focus()
        self.backend.type_text(url, interval=min(self.type_interval, 0.01))
        self._require_focus()
        self.backend.press("enter")
        self.backend.wait(self.page_delay)
        self._require_focus()

    def _run_javascript(self, script: str, *, wait_after: float) -> None:
        self._require_focus()
        self.backend.hotkey("ctrl", "l")
        self.backend.wait(self.step_delay)
        self._require_focus()
        self.backend.type_text(script, interval=0.001)
        self._require_focus()
        self.backend.press("enter")
        self.backend.wait(wait_after)
        self._require_focus()

def _env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except ValueError:
        return default
