from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from friday.app.power import initialize_power_state, record_power_activity
from friday.src.router.v1.runtime.routes import router
from friday.src.services.runtime.service import (
    get_auto_sleep_config,
    update_auto_sleep_config,
)


class AutoSleepRuntimeServiceTests(unittest.TestCase):
    def _environment(self, directory: str) -> dict[str, str]:
        return {
            "FRIDAY_POWER_STATE_PATH": str(Path(directory) / "power-state.json"),
            "FRIDAY_POWER_ACTIVITY_PATH": str(Path(directory) / "power-activity.json"),
            "FRIDAY_AUTO_SLEEP_SETTINGS_PATH": str(Path(directory) / "auto-sleep.json"),
            "FRIDAY_INITIAL_STATE": "active",
        }

    def test_apply_persists_minutes_and_restarts_idle_countdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = self._environment(directory)
            with patch.dict(os.environ, env, clear=False):
                initialize_power_state(source="test")
                record_power_activity(
                    source="old",
                    at=datetime.now(timezone.utc) - timedelta(minutes=10),
                )

                applied = update_auto_sleep_config(12)
                loaded = get_auto_sleep_config()

                self.assertEqual(applied["minutes"], 12)
                self.assertEqual(loaded["minutes"], 12)
                self.assertLess(float(loaded["inactive_seconds"]), 2)
                self.assertGreater(float(loaded["remaining_seconds"]), 710)

    def test_runtime_api_gets_and_applies_auto_sleep_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, self._environment(directory), clear=False):
                initialize_power_state(source="test")
                app = FastAPI()
                app.include_router(router, prefix="/runtime")
                client = TestClient(app)

                initial = client.get("/runtime/auto-sleep")
                applied = client.put("/runtime/auto-sleep", json={"minutes": 17})
                loaded = client.get("/runtime/auto-sleep")

                self.assertEqual(initial.status_code, 200)
                self.assertEqual(applied.status_code, 200)
                self.assertEqual(applied.json()["minutes"], 17)
                self.assertEqual(loaded.json()["minutes"], 17)


if __name__ == "__main__":
    unittest.main()
