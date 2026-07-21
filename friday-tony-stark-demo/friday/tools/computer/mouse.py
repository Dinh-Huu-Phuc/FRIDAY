"""Mouse helpers backed by pyautogui."""

from __future__ import annotations

from friday.tools.computer import get_pyautogui


def move_to(x: int, y: int, duration: float = 0.15) -> dict[str, int | float | bool]:
    pyautogui = get_pyautogui()
    pyautogui.moveTo(int(x), int(y), duration=float(duration))
    return {"ok": True, "x": int(x), "y": int(y), "duration": float(duration)}


def click(x: int | None = None, y: int | None = None, button: str = "left") -> dict[str, int | str | bool | None]:
    pyautogui = get_pyautogui()
    pyautogui.click(x=x, y=y, button=button)
    return {"ok": True, "x": x, "y": y, "button": button}


def double_click(x: int | None = None, y: int | None = None) -> dict[str, int | bool | None]:
    pyautogui = get_pyautogui()
    pyautogui.doubleClick(x=x, y=y)
    return {"ok": True, "x": x, "y": y}


def right_click(x: int | None = None, y: int | None = None) -> dict[str, int | bool | None]:
    pyautogui = get_pyautogui()
    pyautogui.rightClick(x=x, y=y)
    return {"ok": True, "x": x, "y": y}


def scroll(amount: int) -> dict[str, int | bool]:
    pyautogui = get_pyautogui()
    pyautogui.scroll(int(amount))
    return {"ok": True, "amount": int(amount)}


def drag_to(
    x: int,
    y: int,
    *,
    start_x: int | None = None,
    start_y: int | None = None,
    duration: float = 0.2,
    button: str = "left",
) -> dict[str, int | str | float | bool | None]:
    pyautogui = get_pyautogui()
    if start_x is not None and start_y is not None:
        pyautogui.moveTo(int(start_x), int(start_y), duration=float(duration))
    pyautogui.dragTo(int(x), int(y), duration=float(duration), button=button)
    return {
        "ok": True,
        "start_x": start_x,
        "start_y": start_y,
        "end_x": int(x),
        "end_y": int(y),
        "duration": float(duration),
        "button": button,
    }
