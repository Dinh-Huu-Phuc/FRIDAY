from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from friday.app.browser_automation.binance import get_binance_urls
from friday.app.browser_automation.controller import BrowserControlError, ChromeController
from friday.app.browser_automation.intents import (
    is_binance_market_request,
    is_browser_search_request,
    is_platform_video_search_request,
    parse_binance_market_command,
    parse_browser_search_command,
    parse_platform_video_search_command,
)
from friday.app.browser_automation.reader import BingResearchProvider, extract_article_excerpt, is_safe_public_url
from friday.app.browser_automation.schemas import WebSearchResult
from friday.app.browser_automation.service import (
    run_binance_market,
    run_browser_search,
    run_platform_video_search,
)


class FakeChromeBackend:
    def __init__(self, *, focus_states: list[bool] | None = None) -> None:
        self.events: list[tuple] = []
        self.focus_states = list(focus_states or [])

    def ensure_chrome(self) -> bool:
        self.events.append(("ensure",))
        return True

    def is_chrome_active(self) -> bool:
        return self.focus_states.pop(0) if self.focus_states else True

    def hotkey(self, *keys: str) -> None:
        self.events.append(("hotkey", *keys))

    def type_text(self, text: str, interval: float) -> None:
        self.events.append(("type", text, interval))

    def press(self, key: str) -> None:
        self.events.append(("press", key))

    def wait(self, seconds: float) -> None:
        self.events.append(("wait", seconds))


class FakeResearchProvider:
    def first_result(self, query: str) -> WebSearchResult | None:
        return WebSearchResult(
            title="Iron Man - Example Encyclopedia",
            url="https://example.com/iron-man",
            snippet="Iron Man is a fictional armored superhero.",
        )

    def read_excerpt(self, url: str) -> str:
        return "Iron Man is a fictional superhero who uses advanced powered armor."


class BlockingPageResearchProvider(FakeResearchProvider):
    def read_excerpt(self, url: str) -> str:
        raise RuntimeError("Page blocks backend readers")


class MultipleResultResearchProvider(FakeResearchProvider):
    def search_results(self, query: str, *, limit: int = 5) -> list[WebSearchResult]:
        return [
            WebSearchResult("Blocked result", "https://example.com/blocked"),
            WebSearchResult("Readable result", "https://example.org/readable"),
        ]

    def read_excerpt(self, url: str) -> str:
        if "blocked" in url:
            raise RuntimeError("Page blocks backend readers")
        return "The second safe result contains a readable and verifiable paragraph about the requested subject."


class FakeHttpResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class FakeHttpClient:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def get(self, *args, **kwargs) -> FakeHttpResponse:
        return FakeHttpResponse(self.content)


class BrowserIntentTests(unittest.TestCase):
    def test_parses_binance_coin_requests_before_general_search(self) -> None:
        samples = {
            "Show me the Binance platform for Bitcoin certificates.": ("BTC", "Bitcoin"),
            "Friday, show me Binance for BNB": ("BNB", "BNB"),
            "Open Binance and select Ethereum": ("ETH", "Ethereum"),
            "Open Binance for AVAX": ("AVAX", "AVAX"),
        }
        for sample, expected in samples.items():
            with self.subTest(sample=sample):
                command = parse_binance_market_command(sample)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual((command.symbol, command.asset_name), expected)
                self.assertTrue(is_binance_market_request(sample))

    def test_parses_requested_spoken_forms(self) -> None:
        samples = (
            "Friday new tab chrome and search Iron Man",
            "Friday, open a new Chrome tab and search for Iron Man",
            "new tab in Chrome and look up Iron Man and read the first result",
            "Show me the Binance platform for Bitcoin certificates.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                command = parse_browser_search_command(sample)
                self.assertIsNotNone(command)
                expected = (
                    "Binance platform for Bitcoin certificates"
                    if "Binance" in sample
                    else "Iron Man"
                )
                self.assertEqual(command.query, expected)

    def test_does_not_claim_unrelated_search_commands(self) -> None:
        self.assertFalse(is_browser_search_request("open YouTube and search for Iron Man"))
        self.assertFalse(is_browser_search_request("search for Iron Man"))
        self.assertFalse(is_browser_search_request("Show me what I am looking at on this screen"))
        self.assertFalse(is_browser_search_request("Show me my current screen"))

    def test_parses_youtube_and_tiktok_video_search_commands(self) -> None:
        samples = {
            "FRIDAY open youtube and search Tony Stark": ("youtube", "Tony Stark"),
            "Friday open TikTok and search for Tony Stark": ("tiktok", "Tony Stark"),
            "open tik tok and look up Iron Man": ("tiktok", "Iron Man"),
        }
        for sample, expected in samples.items():
            with self.subTest(sample=sample):
                command = parse_platform_video_search_command(sample)
                self.assertIsNotNone(command)
                assert command is not None
                self.assertEqual((command.platform, command.query), expected)
                self.assertTrue(is_platform_video_search_request(sample))

    def test_video_search_intent_requires_platform_open_action_and_query(self) -> None:
        self.assertFalse(is_platform_video_search_request("open YouTube"))
        self.assertFalse(is_platform_video_search_request("search Tony Stark"))
        self.assertFalse(is_platform_video_search_request("open Facebook and search Tony Stark"))


class ChromeControllerTests(unittest.TestCase):
    def test_binance_opens_overview_clicks_coin_and_opens_trade_tab(self) -> None:
        backend = FakeChromeBackend()
        controller = ChromeController(
            backend=backend,
            type_interval=0.06,
            step_delay=0,
            page_delay=0,
            platform_load_delay=0,
        )

        controller.open_binance_market(
            overview_url="https://www.binance.com/vi/markets/overview",
            trade_url="https://www.binance.com/vi/trade/BNB_USDT?_from=markets",
            symbol="BNB",
            asset_name="BNB",
        )

        typed = [event[1] for event in backend.events if event[0] == "type"]
        self.assertEqual(backend.events.count(("hotkey", "ctrl", "t")), 2)
        self.assertIn("https://www.binance.com/vi/markets/overview", typed)
        self.assertIn("https://www.binance.com/vi/trade/BNB_USDT?_from=markets", typed)
        self.assertTrue(any(value.startswith("javascript:") and "BNB" in value for value in typed))

    def test_binance_trade_url_replaces_only_the_asset_pair(self) -> None:
        env = {
            "BINANCE_URL_VI_MARKET_OVERVIEW": "https://www.binance.com/vi/markets/overview",
            "BINANCE_URL": "https://www.binance.com/vi/trade/BTC_USDT?_from=markets",
        }
        with patch.dict(os.environ, env, clear=False):
            overview, trade = get_binance_urls("BNB")

        self.assertEqual(overview, env["BINANCE_URL_VI_MARKET_OVERVIEW"])
        self.assertEqual(
            trade,
            "https://www.binance.com/vi/trade/BNB_USDT?_from=markets",
        )

    def test_binance_service_uses_the_dedicated_controller_workflow(self) -> None:
        controller = Mock()
        with patch(
            "friday.app.browser_automation.service.get_binance_urls",
            return_value=(
                "https://www.binance.com/vi/markets/overview",
                "https://www.binance.com/vi/trade/BTC_USDT?_from=markets",
            ),
        ):
            result = run_binance_market(
                "Show me the Binance platform for Bitcoin certificates.",
                controller=controller,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.query, "BTC")
        controller.open_binance_market.assert_called_once()

    def test_search_and_open_are_visible_keyboard_sequences(self) -> None:
        backend = FakeChromeBackend()
        controller = ChromeController(
            backend=backend,
            type_interval=0.06,
            step_delay=0,
            page_delay=0,
        )

        controller.search_in_new_tab("Iron Man")
        controller.open_url("https://example.com/iron-man")

        self.assertIn(("hotkey", "ctrl", "t"), backend.events)
        self.assertIn(("type", "Iron Man", 0.06), backend.events)
        self.assertIn(("hotkey", "ctrl", "l"), backend.events)
        self.assertEqual([event for event in backend.events if event[0] == "press"], [("press", "enter"), ("press", "enter")])

    def test_stops_if_chrome_loses_focus(self) -> None:
        backend = FakeChromeBackend(focus_states=[True, False])
        controller = ChromeController(backend=backend, step_delay=0, page_delay=0)

        with self.assertRaises(BrowserControlError):
            controller.search_in_new_tab("Iron Man")

        self.assertFalse(any(event[0] == "type" for event in backend.events))

    def test_youtube_search_types_query_and_selects_from_first_three(self) -> None:
        backend = FakeChromeBackend()
        controller = ChromeController(
            backend=backend,
            type_interval=0.06,
            step_delay=0,
            page_delay=0,
            platform_load_delay=0,
            result_delay=0,
        )

        result = run_platform_video_search(
            "FRIDAY open YouTube and search Tony Stark",
            controller=controller,
            result_index=1,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.selected_rank, 2)
        self.assertIn(("press", "esc"), backend.events)
        self.assertIn(("type", "/", 0.0), backend.events)
        self.assertIn(("hotkey", "ctrl", "a"), backend.events)
        self.assertIn(("type", "Tony Stark", 0.06), backend.events)
        scripts = [event[1] for event in backend.events if event[0] == "type" and event[1].startswith("javascript:")]
        self.assertEqual(len(scripts), 1)
        self.assertIn("ytd-video-renderer", scripts[0])
        self.assertIn("slice(0,3)", scripts[0])
        self.assertIn("a[1%a.length]", scripts[0])

    def test_tiktok_search_focuses_input_then_types_and_selects_video(self) -> None:
        backend = FakeChromeBackend()
        controller = ChromeController(
            backend=backend,
            type_interval=0.06,
            step_delay=0,
            page_delay=0,
            platform_load_delay=0,
            result_delay=0,
        )

        result = run_platform_video_search(
            "Friday open TikTok and search for Tony Stark",
            controller=controller,
            result_index=2,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.selected_rank, 3)
        typed = [event for event in backend.events if event[0] == "type"]
        query_event_index = typed.index(("type", "Tony Stark", 0.06))
        self.assertTrue(typed[query_event_index - 1][1].startswith("javascript:"))
        self.assertIn("input[type='search']", typed[query_event_index - 1][1])
        self.assertIn("main a[href*='/video/']", typed[-1][1])
        self.assertIn("slice(0,3)", typed[-1][1])


class BrowserWorkflowTests(unittest.TestCase):
    def test_dry_run_opens_result_and_returns_readable_excerpt(self) -> None:
        backend = FakeChromeBackend()
        controller = ChromeController(backend=backend, step_delay=0, page_delay=0)

        result = run_browser_search(
            "Friday new tab Chrome and search Iron Man",
            controller=controller,
            research=FakeResearchProvider(),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.query, "Iron Man")
        self.assertEqual(result.url, "https://example.com/iron-man")
        self.assertIn("Here is a short passage", result.message)
        self.assertIn("advanced powered armor", result.message)

    def test_reader_extracts_paragraph_and_ignores_navigation(self) -> None:
        html = """
        <html><body>
          <nav><p>This navigation paragraph must never be spoken even though it is deliberately long.</p></nav>
          <main><p>Iron Man is a fictional superhero appearing in American comic books published by Marvel Comics.</p></main>
        </body></html>
        """

        excerpt = extract_article_excerpt(html)

        self.assertIn("fictional superhero", excerpt)
        self.assertNotIn("navigation", excerpt)

    def test_unreadable_page_does_not_fall_back_to_search_snippet(self) -> None:
        controller = ChromeController(
            backend=FakeChromeBackend(),
            step_delay=0,
            page_delay=0,
        )

        result = run_browser_search(
            "Friday new tab Chrome and search Iron Man",
            controller=controller,
            research=BlockingPageResearchProvider(),
        )

        self.assertFalse(result.ok)
        self.assertIn("none provided readable public content", result.message)

    def test_research_tries_the_next_safe_result_when_first_is_unreadable(self) -> None:
        backend = FakeChromeBackend()
        controller = ChromeController(backend=backend, step_delay=0, page_delay=0)

        result = run_browser_search(
            "Friday new tab Chrome and search Iron Man",
            controller=controller,
            research=MultipleResultResearchProvider(),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.title, "Readable result")
        typed_urls = [event[1] for event in backend.events if event[0] == "type"]
        self.assertIn("https://example.com/blocked", typed_urls)
        self.assertIn("https://example.org/readable", typed_urls)

    def test_url_guard_blocks_local_and_download_targets(self) -> None:
        self.assertTrue(is_safe_public_url("https://example.com/article"))
        self.assertFalse(is_safe_public_url("http://127.0.0.1/private"))
        self.assertFalse(is_safe_public_url("https://example.com/tool.exe"))

    def test_search_prefers_readable_reference_over_video(self) -> None:
        rss = b"""<?xml version="1.0" encoding="utf-8"?>
        <rss><channel>
          <item><title>Iron Man Full Movie</title><link>https://www.youtube.com/watch?v=123</link><description>Video</description></item>
          <item><title>Iron Man (2008) - IMDb</title><link>https://www.imdb.com/title/tt0371746/</link><description>Movie page</description></item>
          <item><title>Iron Man - Wikipedia</title><link>https://en.wikipedia.org/wiki/Iron_Man</link><description>Reference article</description></item>
        </channel></rss>"""
        provider = BingResearchProvider(client=FakeHttpClient(rss))

        result = provider.first_result("Iron Man")

        self.assertIsNotNone(result)
        self.assertEqual(result.url, "https://en.wikipedia.org/wiki/Iron_Man")

    def test_latest_query_prefers_a_news_result_over_static_reference(self) -> None:
        rss = b"""<?xml version="1.0" encoding="utf-8"?>
        <rss><channel>
          <item><title>FIFA World Cup</title><link>https://en.wikipedia.org/wiki/FIFA_World_Cup</link><description>Reference</description></item>
          <item><title>Latest World Cup update</title><link>https://www.reuters.com/sports/world-cup-update</link><description>Current report</description></item>
        </channel></rss>"""
        provider = BingResearchProvider(client=FakeHttpClient(rss))

        result = provider.first_result("latest World Cup news")

        self.assertIsNotNone(result)
        self.assertEqual(
            result.url,
            "https://www.reuters.com/sports/world-cup-update",
        )

    def test_news_search_unwraps_bing_redirect_to_the_publisher(self) -> None:
        rss = b"""<?xml version="1.0" encoding="utf-8"?>
        <rss><channel><item>
          <title>Latest OpenAI report</title>
          <link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fexample.com%2Fopenai-news</link>
          <description>OpenAI released an update.</description>
          <pubDate>Thu, 16 Jul 2026 05:13:00 GMT</pubDate>
        </item></channel></rss>"""
        provider = BingResearchProvider(client=FakeHttpClient(rss))

        result = provider.first_result("OpenAI news latest")

        self.assertIsNotNone(result)
        self.assertEqual(result.url, "https://example.com/openai-news")
        self.assertIn("Published:", result.snippet)


if __name__ == "__main__":
    unittest.main()
