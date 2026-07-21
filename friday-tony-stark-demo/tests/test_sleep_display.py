from __future__ import annotations

import tempfile
import unittest
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from friday.app.power.window_manager import WindowActionResult
from friday.app.sleep_display.brightness import BrightnessManager
from friday.app.sleep_display.icon_resolver import (
    resolve_temperature_icon,
    resolve_weather_icon,
)


class FakeBrightnessBackend:
    def __init__(self) -> None:
        self.levels = [64, 72]
        self.set_all_calls: list[int] = []
        self.set_display_calls: list[tuple[int, int]] = []

    def get_levels(self) -> list[tuple[int, int]]:
        return [(index, level) for index, level in enumerate(self.levels)]

    def set_all(self, value: int) -> None:
        self.set_all_calls.append(value)

    def set_display(self, index: int, value: int) -> None:
        self.set_display_calls.append((index, value))


class SleepDisplayTests(unittest.TestCase):
    def test_stop_finds_sleep_window_when_pid_state_is_missing(self) -> None:
        from friday.app.sleep_display import process_manager

        user32 = Mock()
        with (
            patch.object(process_manager.os, "name", "nt"),
            patch.object(process_manager, "named_mutex", return_value=nullcontext()),
            patch.object(process_manager, "_read_state", return_value={}),
            patch.object(process_manager, "_find_window", side_effect=[2468, 0, 0]),
            patch.object(process_manager, "_window_process_id", return_value=913),
            patch.object(process_manager.ctypes, "windll", Mock(user32=user32)),
            patch.object(process_manager, "_STATE_PATH", Mock()),
        ):
            result = process_manager.stop_sleep_display()

        self.assertTrue(result.ok)
        self.assertEqual(result.pid, 913)
        user32.PostMessageW.assert_called_once_with(2468, process_manager.WM_CLOSE, 0, 0)

    def test_weather_icons_follow_condition_wind_and_time(self) -> None:
        self.assertEqual(
            resolve_weather_icon("heavy rain", 4, now=datetime(2026, 7, 14, 12)),
            "cloud-showers-heavy-solid-full.svg",
        )
        self.assertEqual(
            resolve_weather_icon("clear sky", 25, now=datetime(2026, 7, 14, 22)),
            "moon-regular-full.svg",
        )
        self.assertEqual(
            resolve_weather_icon("clear sky", 4, now=datetime(2026, 7, 14, 9)),
            "cloud-sun-solid-full.svg",
        )

    def test_weather_icon_uses_real_sunrise_and_sunset(self) -> None:
        sunrise = datetime(2026, 7, 14, 5, 35)
        sunset = datetime(2026, 7, 14, 18, 17)

        self.assertEqual(
            resolve_weather_icon(
                "light rain",
                4,
                now=datetime(2026, 7, 14, 5, 20),
                sunrise=sunrise,
                sunset=sunset,
            ),
            "cloud-moon-rain-solid-full.svg",
        )
        self.assertEqual(
            resolve_weather_icon(
                "light rain",
                4,
                now=datetime(2026, 7, 14, 7),
                sunrise=sunrise,
                sunset=sunset,
            ),
            "cloud-sun-rain-solid-full.svg",
        )

    def test_temperature_icons_follow_temperature_band(self) -> None:
        self.assertEqual(resolve_temperature_icon(9), "temperature-low-solid-full.svg")
        self.assertEqual(resolve_temperature_icon(24), "temperature-half-solid-full.svg")
        self.assertEqual(resolve_temperature_icon(34), "temperature-high-solid-full.svg")

    def test_brightness_is_snapshotted_once_and_wakes_at_full_brightness(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ",
            {
                "FRIDAY_SLEEP_BRIGHTNESS_ENABLED": "true",
                "FRIDAY_SLEEP_BRIGHTNESS": "30",
                "FRIDAY_WAKE_BRIGHTNESS": "100",
            },
        ):
            backend = FakeBrightnessBackend()
            state_path = Path(directory) / "brightness.json"
            manager = BrightnessManager(backend=backend, state_path=state_path)

            first = manager.dim()
            second = manager.dim()
            restored = manager.restore()

            self.assertTrue(first.ok)
            self.assertTrue(second.ok)
            self.assertTrue(restored.ok)
            self.assertEqual(first.levels, (64, 72))
            self.assertEqual(backend.set_all_calls, [30, 100])
            self.assertFalse(state_path.exists())

    @patch("friday.app.power.sleep_environment.start_sleep_display")
    @patch("friday.app.power.sleep_environment.dim_displays")
    @patch("friday.app.power.sleep_environment.WindowSleepManager")
    def test_sleep_environment_starts_only_after_windows_are_minimized(
        self,
        manager_class: Mock,
        dim_displays: Mock,
        start_display: Mock,
    ) -> None:
        events: list[str] = []
        manager_class.return_value.minimize_all.side_effect = lambda: (
            events.append("minimize")
            or WindowActionResult(True, "minimize", 2, 0, "done")
        )
        dim_displays.side_effect = lambda: events.append("dim") or Mock(message="dimmed")
        start_display.side_effect = lambda: events.append("display") or Mock(message="ready")

        from friday.app.power.sleep_environment import minimize_application_windows

        result = minimize_application_windows()

        self.assertTrue(result.ok)
        self.assertEqual(events, ["minimize", "dim", "display"])

    @patch("friday.app.power.sleep_environment.WindowSleepManager")
    @patch("friday.app.power.sleep_environment.restore_displays")
    @patch("friday.app.power.sleep_environment.stop_sleep_display")
    def test_wake_closes_display_before_restoring_windows(
        self,
        stop_display: Mock,
        restore_displays: Mock,
        manager_class: Mock,
    ) -> None:
        events: list[str] = []
        stop_display.side_effect = lambda: events.append("close-display") or Mock(message="closed")
        restore_displays.side_effect = lambda: events.append("brightness") or Mock(message="restored")
        manager_class.return_value.restore_all.side_effect = lambda: (
            events.append("restore-windows")
            or WindowActionResult(True, "restore", 2, 0, "done")
        )

        from friday.app.power.sleep_environment import restore_application_windows

        result = restore_application_windows()

        self.assertTrue(result.ok)
        self.assertEqual(events, ["close-display", "brightness", "restore-windows"])


if __name__ == "__main__":
    unittest.main()
