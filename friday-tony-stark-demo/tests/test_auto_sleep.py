from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from friday.app.power import (
    AutoSleepMonitor,
    get_power_activity,
    get_power_state,
    handle_power_message,
    inactive_seconds,
    initialize_power_state,
    record_power_activity,
    update_auto_sleep_settings,
)


class AutoSleepTests(unittest.TestCase):
    def _environment(self, directory: str, *, initial_state: str = "active") -> dict[str, str]:
        return {
            "FRIDAY_POWER_STATE_PATH": str(Path(directory) / "power-state.json"),
            "FRIDAY_POWER_ACTIVITY_PATH": str(Path(directory) / "power-activity.json"),
            "FRIDAY_AUTO_SLEEP_SETTINGS_PATH": str(Path(directory) / "auto-sleep.json"),
            "FRIDAY_INITIAL_STATE": initial_state,
        }

    def test_recent_activity_keeps_friday_active(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, self._environment(directory), clear=False):
                initialize_power_state(source="test")
                record_power_activity(source="test")
                actions: list[str] = []
                monitor = AutoSleepMonitor(
                    timeout_seconds=300,
                    sleep_action=lambda: actions.append("sleep"),
                )

                self.assertFalse(monitor.check_once())
                self.assertEqual(get_power_state().state, "active")
                self.assertEqual(actions, [])

    def test_five_minutes_of_inactivity_puts_friday_to_sleep(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, self._environment(directory), clear=False):
                initialize_power_state(source="test")
                record_power_activity(
                    source="test",
                    at=datetime.now(timezone.utc) - timedelta(minutes=5, seconds=1),
                )
                actions: list[str] = []
                monitor = AutoSleepMonitor(
                    timeout_seconds=300,
                    sleep_action=lambda: actions.append("sleep"),
                )

                self.assertTrue(monitor.check_once())
                self.assertEqual(get_power_state().state, "sleeping")
                self.assertEqual(get_power_state().source, "inactivity_timeout")
                self.assertEqual(actions, ["sleep"])
                self.assertFalse(monitor.check_once())
                self.assertEqual(actions, ["sleep"])

    def test_user_command_resets_shared_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, self._environment(directory), clear=False):
                initialize_power_state(source="test")
                record_power_activity(
                    source="old_activity",
                    at=datetime.now(timezone.utc) - timedelta(minutes=10),
                )

                result = handle_power_message("open youtube", source="web:test")

                self.assertFalse(result.handled)
                self.assertEqual(get_power_activity().source, "web:test")
                self.assertLess(inactive_seconds(), 2)

    def test_background_speech_does_not_reset_activity_while_sleeping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = self._environment(directory, initial_state="sleeping")
            with patch.dict(os.environ, env, clear=False):
                initialize_power_state(source="test")
                old_activity = datetime.now(timezone.utc) - timedelta(minutes=10)
                record_power_activity(source="old_activity", at=old_activity)

                result = handle_power_message(
                    "background speech",
                    source="microphone",
                    silent_when_sleeping=True,
                )

                self.assertTrue(result.handled)
                self.assertEqual(result.reply, "")
                self.assertEqual(get_power_activity().source, "old_activity")

    def test_runtime_timeout_update_is_used_without_restarting_monitor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, self._environment(directory), clear=False):
                initialize_power_state(source="test")
                record_power_activity(
                    source="test",
                    at=datetime.now(timezone.utc) - timedelta(minutes=2),
                )
                actions: list[str] = []
                monitor = AutoSleepMonitor(sleep_action=lambda: actions.append("sleep"))

                self.assertFalse(monitor.check_once())
                update_auto_sleep_settings(minutes=1, source="test")

                self.assertTrue(monitor.check_once())
                self.assertEqual(actions, ["sleep"])


if __name__ == "__main__":
    unittest.main()
