"""Automatic sleep after a configurable period without user activity."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from .activity import inactive_seconds, record_power_activity
from .auto_sleep_settings import get_auto_sleep_settings
from .service import get_power_state, set_power_state
from .sleep_environment import minimize_application_windows


logger = logging.getLogger(__name__)


def auto_sleep_enabled() -> bool:
    return get_auto_sleep_settings().enabled


def auto_sleep_timeout_seconds() -> float:
    return get_auto_sleep_settings().timeout_seconds


def auto_sleep_poll_seconds() -> float:
    return get_auto_sleep_settings().poll_seconds


class AutoSleepMonitor:
    def __init__(
        self,
        *,
        timeout_seconds: float | None = None,
        poll_seconds: float | None = None,
        sleep_action: Callable[[], object] | None = None,
    ) -> None:
        self._dynamic_timeout = timeout_seconds is None
        self.timeout_seconds = auto_sleep_timeout_seconds() if self._dynamic_timeout else max(0.0, timeout_seconds)
        self.poll_seconds = (
            auto_sleep_poll_seconds()
            if poll_seconds is None
            else max(0.01, poll_seconds)
        )
        self.sleep_action = sleep_action or minimize_application_windows
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        if not auto_sleep_enabled():
            logger.info("FRIDAY automatic sleep is disabled")
            return False
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_event.clear()
            if not get_power_state().sleeping:
                record_power_activity(source="auto_sleep_monitor_start")
            self._thread = threading.Thread(
                target=self._run,
                name="friday-auto-sleep",
                daemon=True,
            )
            self._thread.start()
        logger.info(
            "FRIDAY automatic sleep enabled timeout_seconds=%s",
            self.timeout_seconds,
        )
        return True

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self.poll_seconds + 0.5))
        self._thread = None

    def check_once(self) -> bool:
        if get_power_state().sleeping:
            return False
        timeout_seconds = (
            auto_sleep_timeout_seconds() if self._dynamic_timeout else self.timeout_seconds
        )
        if inactive_seconds() < timeout_seconds:
            return False

        # Recheck immediately before changing state in case another runtime
        # process recorded a command while this monitor was evaluating.
        if inactive_seconds() < timeout_seconds or get_power_state().sleeping:
            return False

        set_power_state("sleeping", source="inactivity_timeout")
        result = self.sleep_action()
        logger.info("FRIDAY entered automatic sleep after inactivity: %s", result)
        return True

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_seconds):
            try:
                self.check_once()
            except Exception:
                logger.exception("FRIDAY automatic sleep check failed")
