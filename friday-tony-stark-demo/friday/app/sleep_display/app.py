from __future__ import annotations

import asyncio
import ctypes
import json
import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QCloseEvent, QCursor, QScreen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from friday.app.sleep_display.icon_resolver import (
    resolve_temperature_icon,
    resolve_weather_icon,
)
from friday.search import get_weather_snapshot


WINDOW_TITLE = "FRIDAY Sleep Display"
BACKGROUND_WINDOW_TITLE = "FRIDAY Sleep Display Background"
_FRIDAY_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _FRIDAY_DIR.parent
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_VIDEO_PATH = _FRIDAY_DIR / "assets" / "videos" / "FRIDAY.mp4"
_ICON_DIR = _FRIDAY_DIR / "assets" / "icons" / "fontawesome"
_STATE_PATH = _FRIDAY_DIR / "log" / "runtime" / "sleep_display.json"
_HEALTH_PATH = _FRIDAY_DIR / "log" / "runtime" / "sleep_display_health.json"
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class WeatherSignals(QObject):
    updated = Signal(str)


class VideoBackgroundWindow(QMainWindow):
    def __init__(self, screen: QScreen) -> None:
        super().__init__()
        self.screen = screen
        self.setWindowTitle(BACKGROUND_WINDOW_TITLE)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))

        self.video_widget = QVideoWidget(self)
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.setCentralWidget(self.video_widget)

        self.audio_output = QAudioOutput(self)
        self.audio_output.setMuted(True)
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.media_player.setSource(QUrl.fromLocalFile(str(_VIDEO_PATH)))

    def start(self) -> None:
        _cover_screen(self, self.screen, topmost=False)
        self.media_player.play()


class SleepDisplayWindow(QMainWindow):
    def __init__(self, screen: QScreen, manager: SleepDisplayManager) -> None:
        super().__init__()
        self.screen = screen
        self.manager = manager
        self._closing_for_screen_change = False
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))

        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        self.setCentralWidget(self.web_view)
        self.web_view.loadFinished.connect(self._on_page_ready)
        self.web_view.setUrl(QUrl.fromLocalFile(str(_STATIC_DIR / "index.html")))

    def start(self, *, activate: bool) -> None:
        _cover_screen(self, self.screen, topmost=True, activate=activate)

    def apply_weather(self, payload_json: str) -> None:
        self.web_view.page().runJavaScript(f"window.updateWeather({payload_json});")

    def dispose_for_screen_change(self) -> None:
        self._closing_for_screen_change = True
        self.close()

    def _on_page_ready(self, ok: bool) -> None:
        if not ok:
            return
        self.manager.on_window_ready(self)
        QTimer.singleShot(2_000, self._capture_web_health)

    def _capture_web_health(self) -> None:
        script = (
            "JSON.stringify({hasSvgIcon: Boolean(document.querySelector('#weather-icon-image').src), "
            "viewport: [window.innerWidth, window.innerHeight], "
            "weatherRect: (() => { const r = document.querySelector('.weather').getBoundingClientRect(); "
            "return [r.x, r.y, r.width, r.height]; })(), "
            "iconLoaded: document.querySelector('#weather-icon-image').complete, "
            "iconName: document.querySelector('.weather').dataset.icon || '', "
            "screenName: " + json.dumps(self.screen.name()) + "})"
        )
        self.web_view.page().runJavaScript(script, self.manager.write_health_state)

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        if not self._closing_for_screen_change:
            application = QApplication.instance()
            if application is not None:
                application.quit()


@dataclass(slots=True)
class ScreenWindows:
    screen: QScreen
    background: VideoBackgroundWindow
    overlay: SleepDisplayWindow

    def close(self) -> None:
        self.overlay.dispose_for_screen_change()
        self.background.close()


class SleepDisplayManager(QObject):
    def __init__(self, application: QApplication) -> None:
        super().__init__()
        self.application = application
        self.windows: dict[int, ScreenWindows] = {}
        self.weather_signals = WeatherSignals()
        self.weather_signals.updated.connect(self._broadcast_weather)
        self._weather_thread: threading.Thread | None = None
        self._weather_payload_json = ""
        self._ready_windows: set[int] = set()

        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(_weather_refresh_ms())
        self.weather_timer.timeout.connect(self.refresh_weather)

        application.screenAdded.connect(self._screens_changed)
        application.screenRemoved.connect(self._screens_changed)

    def start(self) -> None:
        _write_process_state(
            ready=True,
            screen_count=len(self.application.screens()),
        )
        QTimer.singleShot(0, self.sync_screens)
        self.weather_timer.start()
        self.refresh_weather()

    def sync_screens(self) -> None:
        current_screens = list(self.application.screens())
        current_ids = {id(screen) for screen in current_screens}

        for screen_id in list(self.windows):
            if screen_id not in current_ids:
                pair = self.windows.pop(screen_id)
                self._ready_windows.discard(screen_id)
                pair.close()

        primary = self.application.primaryScreen()
        for screen in current_screens:
            screen_id = id(screen)
            if screen_id in self.windows:
                continue
            background = VideoBackgroundWindow(screen)
            overlay = SleepDisplayWindow(screen, self)
            pair = ScreenWindows(screen, background, overlay)
            self.windows[screen_id] = pair
            background.start()
            overlay.start(activate=screen is primary)
            # The launcher only needs one visible window to consider startup healthy.
            # Additional monitors continue initializing in this same process.
            _write_process_state(ready=True, screen_count=len(self.windows))
            QTimer.singleShot(
                500,
                lambda target=overlay, active=screen is primary: target.start(activate=active),
            )

        _write_process_state(ready=bool(self.windows), screen_count=len(self.windows))

    def on_window_ready(self, window: SleepDisplayWindow) -> None:
        screen_id = id(window.screen)
        self._ready_windows.add(screen_id)
        if self._weather_payload_json:
            window.apply_weather(self._weather_payload_json)
        _write_process_state(ready=True, screen_count=len(self.windows))

    def refresh_weather(self) -> None:
        if self._weather_thread and self._weather_thread.is_alive():
            return
        self._weather_thread = threading.Thread(target=self._fetch_weather, daemon=True)
        self._weather_thread.start()

    def _fetch_weather(self) -> None:
        try:
            snapshot = asyncio.run(get_weather_snapshot(city="Da Lat", country="Vietnam"))
            payload = _weather_payload(snapshot)
        except Exception:
            payload = _weather_payload({"ok": False})
        self.weather_signals.updated.emit(json.dumps(payload))

    def _broadcast_weather(self, payload_json: str) -> None:
        self._weather_payload_json = payload_json
        for pair in self.windows.values():
            if id(pair.screen) in self._ready_windows:
                pair.overlay.apply_weather(payload_json)

    def _screens_changed(self, _screen: QScreen) -> None:
        QTimer.singleShot(250, self.sync_screens)

    def write_health_state(self, result) -> None:
        try:
            payload = json.loads(result) if isinstance(result, str) and result else {}
            health = _read_json(_HEALTH_PATH)
            screens = health.get("screens") if isinstance(health.get("screens"), list) else []
            screens = [item for item in screens if item.get("screenName") != payload.get("screenName")]
            screens.append(payload)
            _HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
            _HEALTH_PATH.write_text(
                json.dumps({"screenCount": len(self.windows), "screens": screens}, indent=2),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError):
            return


def _cover_screen(
    window: QMainWindow,
    screen: QScreen,
    *,
    topmost: bool,
    activate: bool = False,
) -> None:
    geometry = screen.geometry()
    window.setScreen(screen)
    window.setGeometry(geometry)
    window.showFullScreen()
    window.setGeometry(geometry)
    window.raise_()
    if os.name == "nt":
        ctypes.windll.user32.SetWindowPos(
            int(window.winId()),
            HWND_TOPMOST if topmost else 0,
            0,
            0,
            0,
            0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        if activate:
            ctypes.windll.user32.SetForegroundWindow(int(window.winId()))


def _weather_payload(snapshot: dict) -> dict[str, object]:
    description = str(snapshot.get("description") or "Weather unavailable").strip()
    wind_kmh = _as_float(snapshot.get("wind_kmh"))
    temperature = snapshot.get("temp") or "--"
    timezone_offset = int(_as_float(snapshot.get("timezone_offset")))
    local_timezone = timezone(timedelta(seconds=timezone_offset))
    now = datetime.now(timezone.utc).astimezone(local_timezone)
    sunrise = _timestamp_to_datetime(snapshot.get("sunrise_unix"), local_timezone)
    sunset = _timestamp_to_datetime(snapshot.get("sunset_unix"), local_timezone)
    icon_name = resolve_weather_icon(
        description,
        wind_kmh,
        now=now,
        sunrise=sunrise,
        sunset=sunset,
    )
    temperature_icon = resolve_temperature_icon(temperature)
    return {
        "ok": bool(snapshot.get("ok")),
        "location": "Da Lat, Vietnam",
        "temperature": str(temperature),
        "description": description.capitalize(),
        "wind": str(snapshot.get("wind_kmh") or "--"),
        "sunrise": str(snapshot.get("sunrise") or "--:--"),
        "sunset": str(snapshot.get("sunset") or "--:--"),
        "isDaylight": bool(sunrise and sunset and sunrise <= now < sunset)
        if sunrise and sunset
        else 6 <= now.hour < 18,
        "icon": icon_name,
        "iconUrl": _icon_url(icon_name),
        "temperatureIconUrl": _icon_url(temperature_icon),
    }


def _timestamp_to_datetime(value, target_timezone: timezone) -> datetime | None:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=target_timezone)


def _icon_url(icon_name: str) -> str:
    candidate = (_ICON_DIR / Path(icon_name).name).resolve()
    if candidate.parent != _ICON_DIR.resolve() or not candidate.is_file():
        return ""
    return QUrl.fromLocalFile(str(candidate)).toString()


def _as_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _weather_refresh_ms() -> int:
    try:
        minutes = max(1.0, float(os.getenv("FRIDAY_SLEEP_WEATHER_REFRESH_MINUTES", "10")))
    except ValueError:
        minutes = 10.0
    return int(minutes * 60_000)


def _write_process_state(*, ready: bool, screen_count: int = 0) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "ready": ready,
        "screen_count": screen_count,
        "window_title": WINDOW_TITLE,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    temporary = _STATE_PATH.with_name(f".{_STATE_PATH.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(_STATE_PATH)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}


def _remove_own_process_state() -> None:
    try:
        payload = _read_json(_STATE_PATH)
        if int(payload.get("pid") or 0) == os.getpid():
            _STATE_PATH.unlink(missing_ok=True)
    except (OSError, TypeError, ValueError):
        return


def main() -> int:
    os.chdir(_PROJECT_ROOT)
    application = QApplication(sys.argv)
    application.setApplicationName("FRIDAY Sleep Display")
    application.setQuitOnLastWindowClosed(False)
    application.aboutToQuit.connect(_remove_own_process_state)
    _write_process_state(ready=False)
    manager = SleepDisplayManager(application)
    manager.start()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
