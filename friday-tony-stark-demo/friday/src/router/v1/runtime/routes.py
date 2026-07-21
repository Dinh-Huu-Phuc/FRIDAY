from __future__ import annotations

from fastapi import APIRouter

from friday.src.schemas.runtime.requests import AutoSleepSettingsUpdateRequest
from friday.src.schemas.runtime.responses import RuntimeStateResponse, RuntimeStatusResponse
from friday.src.services.runtime.service import (
    get_state,
    get_status,
    get_auto_sleep_config,
    minimize_windows,
    restore_windows,
    sleep,
    update_auto_sleep_config,
    wake,
)


router = APIRouter()


@router.get("/state", response_model=RuntimeStateResponse)
def runtime_state() -> RuntimeStateResponse:
    return get_state()


@router.get("/status", response_model=RuntimeStatusResponse)
def runtime_status() -> RuntimeStatusResponse:
    return get_status()


@router.post("/sleep", response_model=RuntimeStateResponse)
def runtime_sleep() -> RuntimeStateResponse:
    return sleep()


@router.post("/wake", response_model=RuntimeStateResponse)
def runtime_wake() -> RuntimeStateResponse:
    return wake()


@router.post("/windows/minimize")
def runtime_minimize_windows() -> dict[str, str | int | bool]:
    return minimize_windows()


@router.post("/windows/restore")
def runtime_restore_windows() -> dict[str, str | int | bool]:
    return restore_windows()


@router.get("/auto-sleep")
def runtime_auto_sleep_settings() -> dict[str, str | float | bool]:
    return get_auto_sleep_config()


@router.put("/auto-sleep")
def runtime_update_auto_sleep_settings(
    payload: AutoSleepSettingsUpdateRequest,
) -> dict[str, str | float | bool]:
    return update_auto_sleep_config(payload.minutes)
