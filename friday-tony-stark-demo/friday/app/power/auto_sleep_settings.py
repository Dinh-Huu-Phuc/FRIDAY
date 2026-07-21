from __future__ import annotations

import json
import math
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


_LOCK = threading.RLock()
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SETTINGS_PATH = (
    _PROJECT_ROOT / "friday" / "log" / "runtime" / "auto_sleep_settings.json"
)
MIN_AUTO_SLEEP_MINUTES = 1.0
MAX_AUTO_SLEEP_MINUTES = 1_440.0


class InvalidAutoSleepSettingsError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AutoSleepSettings:
    enabled: bool
    minutes: float
    poll_seconds: float
    updated_at: str
    source: str

    @property
    def timeout_seconds(self) -> float:
        return self.minutes * 60.0

    def to_dict(self) -> dict[str, str | float | bool]:
        return asdict(self)


def get_auto_sleep_settings() -> AutoSleepSettings:
    with _LOCK:
        path = _settings_path()
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                return AutoSleepSettings(
                    enabled=bool(payload.get("enabled", _env_enabled())),
                    minutes=_validated_minutes(payload.get("minutes", _env_minutes())),
                    poll_seconds=_validated_poll_seconds(
                        payload.get("poll_seconds", _env_poll_seconds())
                    ),
                    updated_at=str(payload.get("updated_at") or _now_iso()),
                    source=str(payload.get("source") or "runtime_file"),
                )
            except (OSError, TypeError, ValueError, InvalidAutoSleepSettingsError):
                pass
        return AutoSleepSettings(
            enabled=_env_enabled(),
            minutes=_env_minutes(),
            poll_seconds=_env_poll_seconds(),
            updated_at=_now_iso(),
            source="environment",
        )


def update_auto_sleep_settings(
    *,
    minutes: float,
    source: str = "runtime_api",
) -> AutoSleepSettings:
    with _LOCK:
        current = get_auto_sleep_settings()
        settings = AutoSleepSettings(
            enabled=current.enabled,
            minutes=_validated_minutes(minutes),
            poll_seconds=current.poll_seconds,
            updated_at=_now_iso(),
            source=source,
        )
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
        temporary.replace(path)
        return settings


def _settings_path() -> Path:
    configured = os.getenv("FRIDAY_AUTO_SLEEP_SETTINGS_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else _DEFAULT_SETTINGS_PATH


def _env_enabled() -> bool:
    return os.getenv("FRIDAY_AUTO_SLEEP_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_minutes() -> float:
    try:
        return _validated_minutes(os.getenv("FRIDAY_AUTO_SLEEP_MINUTES", "5"))
    except InvalidAutoSleepSettingsError:
        return 5.0


def _env_poll_seconds() -> float:
    try:
        return _validated_poll_seconds(os.getenv("FRIDAY_AUTO_SLEEP_POLL_SECONDS", "5"))
    except InvalidAutoSleepSettingsError:
        return 5.0


def _validated_minutes(value) -> float:
    try:
        minutes = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidAutoSleepSettingsError("Auto-sleep minutes must be a number.") from exc
    if not math.isfinite(minutes) or not MIN_AUTO_SLEEP_MINUTES <= minutes <= MAX_AUTO_SLEEP_MINUTES:
        raise InvalidAutoSleepSettingsError(
            f"Auto-sleep minutes must be between {MIN_AUTO_SLEEP_MINUTES:g} and "
            f"{MAX_AUTO_SLEEP_MINUTES:g}."
        )
    return minutes


def _validated_poll_seconds(value) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidAutoSleepSettingsError("Auto-sleep poll interval must be a number.") from exc
    if not math.isfinite(seconds):
        raise InvalidAutoSleepSettingsError("Auto-sleep poll interval must be finite.")
    return min(max(seconds, 0.25), 60.0)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
