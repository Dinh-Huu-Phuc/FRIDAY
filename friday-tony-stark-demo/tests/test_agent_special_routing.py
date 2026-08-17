from __future__ import annotations

import asyncio
import unittest
from unittest.mock import Mock, patch

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.browser_automation.schemas import BrowserAutomationResult
from friday.app.code_map import CodeMapAction, get_code_map_command_bus
from friday.app.neural_visual import (
    NeuralVisualAction,
    get_neural_visual_command_bus,
)
from friday.app.perception.window import (
    CameraWindowAction,
    get_camera_window_command_bus,
)
from friday.app.research.schemas import LiveSearchResult
from friday.app.secure_browser import (
    SecureBrowserAction,
    get_secure_browser_command_bus,
)
from friday.app.windows_launcher.schemas import AppLaunchResponse, AppMatch
from friday.news.schemas import NewsArticle, NewsQuery, NewsServiceResult
from friday.src.services.agent.service import chat


class AgentSpecialRoutingTests(unittest.TestCase):
    def test_camera_window_route_dispatches_before_windows_launcher(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        received: list[CameraWindowAction] = []
        unsubscribe = get_camera_window_command_bus().subscribe(received.append)
        try:
            with (
                patch(
                    "friday.src.services.agent.service.get_agent_console_service",
                    return_value=console,
                ),
                patch("friday.src.services.agent.service.open_app") as open_app,
            ):
                result = asyncio.run(
                    chat(ConsoleChatRequest(message="FRIDAY, open camera."))
                )
        finally:
            unsubscribe()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(received, [CameraWindowAction.OPEN])
        open_app.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
        self.assertIn("Opening the Camera Window", content)

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

    def test_code_map_route_dispatches_before_browser_search(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        received: list[CodeMapAction] = []
        unsubscribe = get_code_map_command_bus().subscribe(received.append)
        try:
            with (
                patch(
                    "friday.src.services.agent.service.get_agent_console_service",
                    return_value=console,
                ),
                patch("friday.src.services.agent.service.run_browser_search") as run_search,
                ):
                result = asyncio.run(
                    chat(
                        ConsoleChatRequest(
                            message="Friday, could you please open the code map?"
                        )
                    )
                )
        finally:
            unsubscribe()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(received, [CodeMapAction.OPEN])
        run_search.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
        self.assertIn("Opening the Code Map", content)

    def test_neural_visual_route_supports_voice_before_browser_search(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        received: list[NeuralVisualAction] = []
        unsubscribe = get_neural_visual_command_bus().subscribe(received.append)
        try:
            with (
                patch(
                    "friday.src.services.agent.service.get_agent_console_service",
                    return_value=console,
                ),
                patch("friday.src.services.agent.service.run_browser_search") as run_search,
            ):
                result = asyncio.run(
                    chat(
                        ConsoleChatRequest(
                            message="FRIDAY open Neural Network",
                            channel="voice",
                        )
                    )
                )
        finally:
            unsubscribe()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(received, [NeuralVisualAction.OPEN])
        run_search.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
        self.assertIn("Opening the Neural Network", content)

    def test_friday_browser_search_runs_research_workflow(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        browser_result = BrowserAutomationResult(
            True,
            "Tony Stark technology",
            "I opened a safe result in FRIDAY Browser. Here is a summary.",
        )
        with (
            patch(
                "friday.src.services.agent.service.get_agent_console_service",
                return_value=console,
            ),
            patch(
                "friday.src.services.agent.service.run_browser_search",
                return_value=browser_result,
            ) as run_search,
        ):
            result = asyncio.run(
                chat(
                    ConsoleChatRequest(
                        message=(
                            "FRIDAY open browser and search "
                            "Tony Stark technology"
                        ),
                        channel="voice",
                    )
                )
            )

        self.assertEqual(result, {"ok": True})
        run_search.assert_called_once()
        content = console.send_assistant_reply.call_args.kwargs[
            "assistant_content"
        ]
        self.assertIn("Here is a summary", content)

    def test_open_the_browser_with_punctuation_never_reaches_windows_launcher(
        self,
    ) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        received = []
        unsubscribe = get_secure_browser_command_bus().subscribe(received.append)
        try:
            with (
                patch(
                    "friday.src.services.agent.service.get_agent_console_service",
                    return_value=console,
                ),
                patch("friday.src.services.agent.service.open_app") as open_app,
            ):
                result = asyncio.run(
                    chat(ConsoleChatRequest(message="Friday, open the browser."))
                )
        finally:
            unsubscribe()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].action, SecureBrowserAction.OPEN)
        open_app.assert_not_called()

    def test_news_update_uses_news_service_result_instead_of_llm_denial(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        news_result = NewsServiceResult(
            is_news_intent=True,
            status="ok",
            query=NewsQuery(country="vn", language="en", limit=6),
            articles=[
                NewsArticle(
                    title="Saturday technology briefing",
                    description="The latest verified technology developments.",
                    source_id="friday-news",
                    source_name="FRIDAY News",
                    pub_date="2026-07-25",
                    link="https://example.com/news",
                )
            ],
        )
        with (
            patch(
                "friday.src.services.agent.service.get_agent_console_service",
                return_value=console,
            ),
            patch(
                "friday.src.services.agent.service._get_news_result",
                return_value=news_result,
            ) as get_news,
            patch(
                "friday.src.services.agent.service._build_llm_client"
            ) as build_llm,
        ):
            result = asyncio.run(
                chat(
                    ConsoleChatRequest(
                        message="Friday, Saturday's news update."
                    )
                )
            )

        self.assertEqual(result, {"ok": True})
        get_news.assert_called_once_with("Friday, Saturday's news update.")
        build_llm.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs[
            "assistant_content"
        ]
        self.assertIn("Saturday technology briefing", content)
        self.assertIn("FRIDAY News", content)
        self.assertNotIn("don't have access", content)

    def test_news_failure_uses_live_search_then_returns_honest_fallback(
        self,
    ) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        console.get_snapshot.return_value = {"messages": []}
        news_result = NewsServiceResult(
            is_news_intent=True,
            status="error",
            query=NewsQuery(country="vn", language="en", limit=6),
            fallback_message=(
                "The news feed is unstable, boss. "
                "I will retry when the connection improves."
            ),
            error="network_error",
        )
        live_search_result = LiveSearchResult(
            ok=False,
            query="Saturday news update",
            message="Live Search could not reach the public search service.",
        )
        with (
            patch(
                "friday.src.services.agent.service.get_agent_console_service",
                return_value=console,
            ),
            patch(
                "friday.src.services.agent.service._get_news_result",
                return_value=news_result,
            ),
            patch(
                "friday.src.services.agent.service.research_public_web",
                return_value=live_search_result,
            ) as live_search,
            patch(
                "friday.src.services.agent.service._build_llm_client"
            ) as build_llm,
        ):
            result = asyncio.run(
                chat(
                    ConsoleChatRequest(
                        message="Friday, Saturday's news update."
                    )
                )
            )

        self.assertEqual(result, {"ok": True})
        live_search.assert_called_once()
        build_llm.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs[
            "assistant_content"
        ]
        self.assertIn("news feed is unstable", content)
        self.assertNotIn("don't have access", content)

    def test_live_crypto_price_returns_grounded_answer_without_llm_guessing(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        console.get_snapshot.return_value = {"messages": []}
        market_search_result = LiveSearchResult(
            ok=True,
            query="today's Bitcoin price",
            message="Live cryptocurrency market data is available.",
            direct_answer=(
                "Bitcoin is currently trading at approximately 67,234.13 USDT "
                "on Binance Spot."
            ),
        )
        with (
            patch(
                "friday.src.services.agent.service.get_agent_console_service",
                return_value=console,
            ),
            patch(
                "friday.src.services.agent.service._get_news_result",
                return_value=None,
            ),
            patch(
                "friday.src.services.agent.service.research_public_web",
                return_value=market_search_result,
            ) as live_search,
            patch(
                "friday.src.services.agent.service._build_llm_client"
            ) as build_llm,
        ):
            result = asyncio.run(
                chat(
                    ConsoleChatRequest(
                        message="Please tell me today's Bitcoin price."
                    )
                )
            )

        self.assertEqual(result, {"ok": True})
        live_search.assert_called_once()
        build_llm.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
        self.assertIn("67,234.13 USDT", content)
        self.assertNotIn("don't have real-time access", content)

    def test_launch_visual_studio_code_uses_windows_launcher(self) -> None:
        console = Mock()
        console.send_assistant_reply.return_value = {"ok": True}
        launched = AppLaunchResponse(
            ok=True,
            message="Launched Visual Studio Code.",
            selected=AppMatch(
                name="Visual Studio Code",
                source="start_menu",
                score=1.0,
                path="Visual Studio Code.lnk",
            ),
        )
        with (
            patch(
                "friday.src.services.agent.service.get_agent_console_service",
                return_value=console,
            ),
            patch(
                "friday.src.services.agent.service._get_news_result",
                return_value=None,
            ),
            patch(
                "friday.src.services.agent.service.open_app",
                return_value=launched,
            ) as open_windows_app,
            patch(
                "friday.src.services.agent.service._build_llm_client"
            ) as build_llm,
        ):
            result = asyncio.run(
                chat(
                    ConsoleChatRequest(
                        message="FRIDAY, launch Visual Studio Code."
                    )
                )
            )

        self.assertEqual(result, {"ok": True})
        open_windows_app.assert_called_once_with(query="Visual Studio Code")
        build_llm.assert_not_called()
        content = console.send_assistant_reply.call_args.kwargs[
            "assistant_content"
        ]
        self.assertEqual(content, "Launched Visual Studio Code.")


if __name__ == "__main__":
    unittest.main()
