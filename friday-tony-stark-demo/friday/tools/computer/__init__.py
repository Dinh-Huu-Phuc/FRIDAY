"""Low-level computer control helpers."""

from __future__ import annotations

from importlib import import_module


def get_pyautogui():
    try:
        module = import_module("pyautogui")
    except Exception as exc:
        raise RuntimeError(
            "pyautogui is required for computer automation. Install it with `uv add pyautogui`."
        ) from exc

    module.FAILSAFE = True
    module.PAUSE = 0.05
    return module
