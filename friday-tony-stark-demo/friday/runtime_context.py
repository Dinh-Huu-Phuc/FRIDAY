"""Runtime context helpers for FRIDAY's personal-assistant behavior."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from friday.language.constants import DEFAULT_LANGUAGE

DEVICE_MODEL = "ASUS TUF Gaming F15 FX506LI"
DEFAULT_LOCATION_CITY = "Da Lat"
DEFAULT_LOCATION_COUNTRY = "Vietnam"
DEFAULT_COMPUTER_SAFETY_MODE = "strict"

LOCATION_CITY_ENV_CANDIDATES = (
    "FRIDAY_MACHINE_LOCATION",
    "FRIDAY_CURRENT_LOCATION",
    "FRIDAY_LOCATION_CITY",
)
LOCATION_COUNTRY_ENV_CANDIDATES = (
    "FRIDAY_MACHINE_COUNTRY",
    "FRIDAY_LOCATION_COUNTRY",
)


def _first_non_empty_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


@dataclass(slots=True, frozen=True)
class RuntimeLocation:
    city: str
    country: str
    source: str

    @property
    def display_name(self) -> str:
        if self.country:
            return f"{self.city}, {self.country}"
        return self.city


@dataclass(slots=True)
class ComputerRuntimeContext:
    current_goal: str = ""
    current_plan: list[str] = field(default_factory=list)
    last_action: dict[str, Any] | None = None
    active_window_title: str = ""
    last_screenshot_path: str = ""
    screen_width: int = 0
    screen_height: int = 0
    safety_mode: str = DEFAULT_COMPUTER_SAFETY_MODE
    current_language: str = DEFAULT_LANGUAGE


_COMPUTER_RUNTIME_LOCK = Lock()
_COMPUTER_RUNTIME_CONTEXT = ComputerRuntimeContext()


def resolve_runtime_location() -> RuntimeLocation:
    city = _first_non_empty_env(LOCATION_CITY_ENV_CANDIDATES)
    country = _first_non_empty_env(LOCATION_COUNTRY_ENV_CANDIDATES)
    if city:
        return RuntimeLocation(
            city=city,
            country=country or DEFAULT_LOCATION_COUNTRY,
            source="environment",
        )
    return RuntimeLocation(
        city=DEFAULT_LOCATION_CITY,
        country=DEFAULT_LOCATION_COUNTRY,
        source="default",
    )


def _snapshot_computer_runtime_context() -> dict[str, Any]:
    return {
        "current_goal": _COMPUTER_RUNTIME_CONTEXT.current_goal,
        "current_plan": list(_COMPUTER_RUNTIME_CONTEXT.current_plan),
        "last_action": deepcopy(_COMPUTER_RUNTIME_CONTEXT.last_action),
        "active_window_title": _COMPUTER_RUNTIME_CONTEXT.active_window_title,
        "last_screenshot_path": _COMPUTER_RUNTIME_CONTEXT.last_screenshot_path,
        "screen_width": _COMPUTER_RUNTIME_CONTEXT.screen_width,
        "screen_height": _COMPUTER_RUNTIME_CONTEXT.screen_height,
        "safety_mode": _COMPUTER_RUNTIME_CONTEXT.safety_mode,
        "current_language": _COMPUTER_RUNTIME_CONTEXT.current_language,
    }


def get_computer_runtime_context() -> dict[str, Any]:
    with _COMPUTER_RUNTIME_LOCK:
        return _snapshot_computer_runtime_context()


def update_computer_runtime_context(**changes: Any) -> dict[str, Any]:
    with _COMPUTER_RUNTIME_LOCK:
        for key, value in changes.items():
            if not hasattr(_COMPUTER_RUNTIME_CONTEXT, key):
                continue
            if key == "current_plan" and value is not None:
                setattr(_COMPUTER_RUNTIME_CONTEXT, key, list(value))
                continue
            if key == "last_action":
                setattr(_COMPUTER_RUNTIME_CONTEXT, key, deepcopy(value))
                continue
            if value is not None:
                setattr(_COMPUTER_RUNTIME_CONTEXT, key, value)
        return _snapshot_computer_runtime_context()


def reset_computer_runtime_context() -> dict[str, Any]:
    with _COMPUTER_RUNTIME_LOCK:
        _COMPUTER_RUNTIME_CONTEXT.current_goal = ""
        _COMPUTER_RUNTIME_CONTEXT.current_plan = []
        _COMPUTER_RUNTIME_CONTEXT.last_action = None
        _COMPUTER_RUNTIME_CONTEXT.active_window_title = ""
        _COMPUTER_RUNTIME_CONTEXT.last_screenshot_path = ""
        _COMPUTER_RUNTIME_CONTEXT.screen_width = 0
        _COMPUTER_RUNTIME_CONTEXT.screen_height = 0
        _COMPUTER_RUNTIME_CONTEXT.safety_mode = DEFAULT_COMPUTER_SAFETY_MODE
        _COMPUTER_RUNTIME_CONTEXT.current_language = DEFAULT_LANGUAGE
        return _snapshot_computer_runtime_context()


def build_runtime_context_snapshot() -> dict[str, Any]:
    location = resolve_runtime_location()
    snapshot: dict[str, Any] = {
        "assistant_name": "Friday",
        "device_model": DEVICE_MODEL,
        "location_city": location.city,
        "location_country": location.country,
        "location_display": location.display_name,
        "location_source": location.source,
    }
    snapshot.update(get_computer_runtime_context())
    return snapshot
