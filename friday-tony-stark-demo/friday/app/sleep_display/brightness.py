from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from friday.app.sleep_display.mutex import named_mutex


_FRIDAY_DIR = Path(__file__).resolve().parents[2]
_STATE_PATH = _FRIDAY_DIR / "log" / "runtime" / "brightness_state.json"


class BrightnessBackend(Protocol):
    def get_levels(self) -> list[tuple[int, int]]: ...
    def set_all(self, value: int) -> None: ...
    def set_display(self, index: int, value: int) -> None: ...


class ScreenBrightnessBackend:
    def _module(self):
        import screen_brightness_control as sbc

        return sbc

    def get_levels(self) -> list[tuple[int, int]]:
        return [
            (index, int(value))
            for index, value in enumerate(self._module().get_brightness())
            if value is not None
        ]

    def set_all(self, value: int) -> None:
        self._module().set_brightness(int(value))

    def set_display(self, index: int, value: int) -> None:
        self._module().set_brightness(int(value), display=index)


@dataclass(frozen=True, slots=True)
class BrightnessResult:
    ok: bool
    action: str
    levels: tuple[int, ...]
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


class BrightnessManager:
    def __init__(self, *, backend: BrightnessBackend | None = None, state_path: Path | None = None) -> None:
        self.backend = backend or ScreenBrightnessBackend()
        self.state_path = state_path or _STATE_PATH

    def dim(self) -> BrightnessResult:
        if not _brightness_enabled():
            return BrightnessResult(False, "dim", (), "Brightness control is disabled.")
        with named_mutex("FRIDAY_SLEEP_BRIGHTNESS"):
            existing = self._load()
            if existing:
                levels = tuple(int(item["level"]) for item in _saved_monitors(existing))
                return BrightnessResult(True, "dim", levels, "Brightness was already dimmed by FRIDAY.")
            try:
                monitors = self.backend.get_levels()
                if not monitors:
                    return BrightnessResult(False, "dim", (), "No controllable display brightness was found.")
                levels = tuple(level for _, level in monitors)
                self._save({
                    "monitors": [
                        {"display": display, "level": level}
                        for display, level in monitors
                    ],
                    "active": True,
                })
                self.backend.set_all(_sleep_brightness())
                return BrightnessResult(True, "dim", levels, "Display brightness reduced.")
            except Exception as exc:
                return BrightnessResult(False, "dim", (), f"Brightness reduction failed: {type(exc).__name__}.")

    def restore(self) -> BrightnessResult:
        with named_mutex("FRIDAY_SLEEP_BRIGHTNESS"):
            state = self._load()
            monitors = _saved_monitors(state)
            levels = tuple(int(item["level"]) for item in monitors)
            if not monitors:
                self.state_path.unlink(missing_ok=True)
                return BrightnessResult(True, "restore", (), "No saved brightness state was found.")
            try:
                wake_level = _wake_brightness()
                if wake_level is not None:
                    self.backend.set_all(wake_level)
                else:
                    for item in monitors:
                        self.backend.set_display(int(item["display"]), int(item["level"]))
                self.state_path.unlink(missing_ok=True)
                return BrightnessResult(True, "restore", levels, "Display brightness restored.")
            except Exception as exc:
                return BrightnessResult(False, "restore", levels, f"Brightness restore failed: {type(exc).__name__}.")

    def _load(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return {}

    def _save(self, payload: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(f".{self.state_path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)


def dim_displays() -> BrightnessResult:
    return BrightnessManager().dim()


def restore_displays() -> BrightnessResult:
    return BrightnessManager().restore()


def _saved_monitors(state: dict) -> list[dict[str, int]]:
    monitors = state.get("monitors") or []
    if monitors:
        return [
            {"display": int(item["display"]), "level": int(item["level"])}
            for item in monitors
            if isinstance(item, dict) and "display" in item and "level" in item
        ]
    return [
        {"display": index, "level": int(level)}
        for index, level in enumerate(state.get("levels") or [])
    ]


def _brightness_enabled() -> bool:
    return os.getenv("FRIDAY_SLEEP_BRIGHTNESS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _sleep_brightness() -> int:
    try:
        return min(100, max(0, int(os.getenv("FRIDAY_SLEEP_BRIGHTNESS", "30"))))
    except ValueError:
        return 30


def _wake_brightness() -> int | None:
    configured = os.getenv("FRIDAY_WAKE_BRIGHTNESS", "100").strip().lower()
    if configured in {"restore", "previous", "original"}:
        return None
    try:
        return min(100, max(0, int(configured)))
    except ValueError:
        return 100
