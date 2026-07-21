from __future__ import annotations

import unittest
from datetime import datetime

from friday.app.agent_console.greeting_engine import build_time_greeting


class TimeGreetingTests(unittest.TestCase):
    def test_startup_greeting_tracks_machine_time(self) -> None:
        message = build_time_greeting(now=datetime(2026, 7, 13, 8, 30), event="startup")

        self.assertIn("Good morning, boss", message)
        self.assertIn("FRIDAY is online", message)

    def test_night_wake_greeting_is_calm_and_ready(self) -> None:
        message = build_time_greeting(now=datetime(2026, 7, 13, 2, 15), event="wake")

        self.assertIn("I am awake, boss", message)
        self.assertIn("stay calm", message)


if __name__ == "__main__":
    unittest.main()
