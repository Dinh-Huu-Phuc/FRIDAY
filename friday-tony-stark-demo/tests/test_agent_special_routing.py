from __future__ import annotations

import asyncio
import unittest
from unittest.mock import Mock, patch

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.browser_automation.schemas import BrowserAutomationResult
from friday.src.services.agent.service import chat


class AgentSpecialRoutingTests(unittest.TestCase):
    def test_web_self_intro_sends_non_empty_prepared_response(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        with patch(
            "friday.src.services.agent.service.get_agent_console_service",
            return_value=console,
        ):
            result = asyncio.run(
                chat(ConsoleChatRequest(message="Please introduce yourself"))
            )

        self.assertEqual(result, {"ok": True})
        content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
        self.assertTrue(content)
        self.assertIn("I am FRIDAY", content)

    def test_binance_route_runs_before_general_browser_search(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        binance_result = BrowserAutomationResult(
            True,
            "BTC",
            "I opened Binance Markets and the BTC/USDT trading page.",
        )
        with (
            patch(
                "friday.src.services.agent.service.get_agent_console_service",
                return_value=console,
            ),
            patch(
                "friday.src.services.agent.service.run_binance_market",
                return_value=binance_result,
            ) as run_binance,
            patch(
                "friday.src.services.agent.service.run_browser_search"
            ) as run_search,
        ):
            result = asyncio.run(
                chat(
                    ConsoleChatRequest(
                        message="Show me the Binance platform for Bitcoin certificates."
                    )
                )
            )

        self.assertEqual(result, {"ok": True})
        run_binance.assert_called_once()
        run_search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
