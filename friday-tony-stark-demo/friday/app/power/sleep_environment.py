from __future__ import annotations

import logging
import threading

from friday.app.power.window_manager import WindowActionResult, WindowSleepManager, window_sleep_enabled
from friday.app.sleep_display import start_sleep_display, stop_sleep_display
from friday.app.sleep_display.brightness import dim_displays, restore_displays


logger = logging.getLogger(__name__)
_ENVIRONMENT_LOCK = threading.RLock()


def minimize_application_windows() -> WindowActionResult:
    with _ENVIRONMENT_LOCK:
        if not window_sleep_enabled():
            return WindowActionResult(False, "minimize", 0, 0, "Window sleep is disabled.")

        display = start_sleep_display()
        result = WindowSleepManager().minimize_all()
        brightness = dim_displays()
        logger.info(
            "Sleep environment display=%s windows=%s brightness=%s",
            display.message,
            result.message,
            brightness.message,
        )
        return result


def restore_application_windows() -> WindowActionResult:
    with _ENVIRONMENT_LOCK:
        if not window_sleep_enabled():
            return WindowActionResult(False, "restore", 0, 0, "Window restore is disabled.")

        display = stop_sleep_display()
        brightness = restore_displays()
        logger.info(
            "Wake environment display=%s brightness=%s",
            display.message,
            brightness.message,
        )
        return WindowSleepManager().restore_all()
