"""Keyboard helpers backed by pyautogui."""

from __future__ import annotations

from friday.tools.computer import get_pyautogui


def type_text(text: str, interval: float = 0.02) -> dict[str, str | float | bool]:
    pyautogui = get_pyautogui()
    pyautogui.write(str(text), interval=float(interval))
    return {"ok": True, "text": str(text), "interval": float(interval)}


def press(key: str) -> dict[str, str | bool]:
    pyautogui = get_pyautogui()
    pyautogui.press(str(key))
    return {"ok": True, "key": str(key)}


def hotkey(*keys: str) -> dict[str, list[str] | bool]:
    normalized_keys = [str(key) for key in keys if str(key).strip()]
    pyautogui = get_pyautogui()
    pyautogui.hotkey(*normalized_keys)
    return {"ok": True, "keys": normalized_keys}
