from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from friday.app.calendar.schemas import CalendarAudioTarget

_FRIDAY_DIR = Path(__file__).resolve().parents[2]


def _enabled(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _float_setting(name: str, default: float, minimum: float) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _int_setting(name: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _default_source_path() -> Path:
    configured = os.getenv("FRIDAY_CALENDAR_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _FRIDAY_DIR / "docs" / "calendar" / "healthy.md"


def _default_state_path() -> Path:
    configured = os.getenv("FRIDAY_CALENDAR_STATE_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _FRIDAY_DIR / "log" / "runtime" / "calendar_state.json"


def resolve_timezone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Ho_Chi_Minh":
            return timezone(timedelta(hours=7), name)
        return datetime_local_timezone()


def datetime_local_timezone() -> tzinfo:
    return datetime.now().astimezone().tzinfo or UTC


@dataclass(frozen=True, slots=True)
class CalendarSettings:
    enabled: bool = field(
        default_factory=lambda: _enabled("FRIDAY_CALENDAR_ENABLED")
    )
    source_path: Path = field(default_factory=_default_source_path)
    state_path: Path = field(default_factory=_default_state_path)
    timezone_name: str = field(
        default_factory=lambda: os.getenv(
            "FRIDAY_CALENDAR_TIMEZONE", "Asia/Ho_Chi_Minh"
        ).strip()
        or "Asia/Ho_Chi_Minh"
    )
    poll_interval_seconds: float = field(
        default_factory=lambda: _float_setting(
            "FRIDAY_CALENDAR_POLL_SECONDS", 0.5, 0.1
        )
    )
    reload_interval_seconds: float = field(
        default_factory=lambda: _float_setting(
            "FRIDAY_CALENDAR_RELOAD_SECONDS", 15.0, 1.0
        )
    )
    misfire_grace_seconds: int = field(
        default_factory=lambda: _int_setting(
            "FRIDAY_CALENDAR_MISFIRE_GRACE_SECONDS", 120, 0
        )
    )
    display_when_active: bool = field(
        default_factory=lambda: _enabled(
            "FRIDAY_CALENDAR_DISPLAY_WHEN_ACTIVE"
        )
    )
    voice_enabled: bool = field(
        default_factory=lambda: _enabled("FRIDAY_CALENDAR_VOICE_ENABLED")
    )
    voice_when_sleeping: bool = field(
        default_factory=lambda: _enabled(
            "FRIDAY_CALENDAR_VOICE_WHEN_SLEEPING"
        )
    )
    audio_target: str = field(
        default_factory=lambda: os.getenv(
            "FRIDAY_CALENDAR_AUDIO_TARGET", "auto"
        ).strip().lower()
        or "auto"
    )

    @property
    def timezone(self) -> tzinfo:
        return resolve_timezone(self.timezone_name)

    @property
    def resolved_audio_target(self) -> CalendarAudioTarget:
        if not self.voice_enabled:
            return "none"
        if self.audio_target in {"desktop", "web", "all", "none"}:
            return self.audio_target  # type: ignore[return-value]
        desktop_enabled = _enabled("FRIDAY_DESKTOP_UI_ENABLED")
        return "desktop" if desktop_enabled else "web"
