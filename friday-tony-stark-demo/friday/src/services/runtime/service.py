from __future__ import annotations

from friday.src.schemas.runtime.responses import RuntimeStateResponse, RuntimeStatusResponse
from friday.app.power import (
    get_auto_sleep_settings,
    get_power_state,
    inactive_seconds,
    minimize_application_windows,
    record_power_activity,
    restore_application_windows,
    set_power_state,
    update_auto_sleep_settings,
)


def get_state() -> RuntimeStateResponse:
    return RuntimeStateResponse(state=get_power_state().to_dict())


def get_status() -> RuntimeStatusResponse:
    return RuntimeStatusResponse(status=get_power_state().state)


def sleep() -> RuntimeStateResponse:
    snapshot = set_power_state("sleeping", source="runtime_api")
    minimize_application_windows()
    return RuntimeStateResponse(state=snapshot.to_dict())


def wake() -> RuntimeStateResponse:
    restore_application_windows()
    snapshot = set_power_state("active", source="runtime_api")
    record_power_activity(source="runtime_api")
    return RuntimeStateResponse(state=snapshot.to_dict())


def minimize_windows() -> dict[str, str | int | bool]:
    return minimize_application_windows().to_dict()


def restore_windows() -> dict[str, str | int | bool]:
    return restore_application_windows().to_dict()


def get_auto_sleep_config() -> dict[str, str | float | bool]:
    settings = get_auto_sleep_settings()
    inactive = inactive_seconds()
    return {
        **settings.to_dict(),
        "timeout_seconds": settings.timeout_seconds,
        "inactive_seconds": round(inactive, 1),
        "remaining_seconds": round(max(0.0, settings.timeout_seconds - inactive), 1),
    }


def update_auto_sleep_config(minutes: float) -> dict[str, str | float | bool]:
    update_auto_sleep_settings(minutes=minutes, source="runtime_api")
    record_power_activity(source="auto_sleep_settings_apply")
    return get_auto_sleep_config()
