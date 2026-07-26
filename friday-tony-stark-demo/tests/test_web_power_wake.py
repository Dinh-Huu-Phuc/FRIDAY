from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.power import initialize_power_state
from friday.src.services.agent.service import chat


class WebPowerWakeTests(unittest.TestCase):
    def _environment(self, directory: str, initial_state: str) -> dict[str, str]:
        return {
            "FRIDAY_POWER_STATE_PATH": str(Path(directory) / "power-state.json"),
            "FRIDAY_POWER_ACTIVITY_PATH": str(Path(directory) / "power-activity.json"),
            "FRIDAY_INITIAL_STATE": initial_state,
        }

    def _wake(self, initial_state: str) -> Mock:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                self._environment(directory, initial_state),
                clear=False,
            ):
                initialize_power_state(source="test")
                console = Mock()
                console.send_assistant_reply.return_value = {"ok": True}
                with (
                    patch(
                        "friday.src.services.agent.service.get_agent_console_service",
                        return_value=console,
                    ),
                    patch(
                        "friday.src.services.agent.service.restore_application_windows"
                    ) as restore,
                ):
                    result = asyncio.run(
                        chat(ConsoleChatRequest(message="FRIDAY wake up"))
                    )

                self.assertEqual(result, {"ok": True})
                return restore

    def test_wake_restores_sleep_display_when_sleeping(self) -> None:
        self._wake("sleeping").assert_called_once_with()

    def test_wake_retries_restore_when_state_is_already_active(self) -> None:
        self._wake("active").assert_called_once_with()

    def test_sleep_starts_the_sleep_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                self._environment(directory, "active"),
                clear=False,
            ):
                initialize_power_state(source="test")
                console = Mock()
                console.send_assistant_reply.return_value = {"ok": True}
                with (
                    patch(
                        "friday.src.services.agent.service.get_agent_console_service",
                        return_value=console,
                    ),
                    patch(
                        "friday.src.services.agent.service.minimize_application_windows"
                    ) as minimize,
                ):
                    result = asyncio.run(
                        chat(ConsoleChatRequest(message="FRIDAY sleep"))
                    )

                self.assertEqual(result, {"ok": True})
                minimize.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
