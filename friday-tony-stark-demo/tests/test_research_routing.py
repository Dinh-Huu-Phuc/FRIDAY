from __future__ import annotations

import unittest
import threading
import time

from friday.app.browser_automation import is_browser_search_request
from friday.app.browser_automation.schemas import WebSearchResult
from friday.app.research import (
    LiveSearchResult,
    LiveSearchSource,
    SEARCH_ACKNOWLEDGEMENT,
    build_research_query,
    build_web_research_context,
    is_web_research_request,
    optimize_search_query,
    search_public_web,
    should_announce_search,
)
from friday.news import is_news_query
from friday.news.world.region import DEFAULT_WORLD_QUERY, build_world_query_text


class ResearchRoutingTests(unittest.TestCase):
    def test_search_routes_receive_an_immediate_spoken_acknowledgement(self) -> None:
        search_samples = (
            "Latest World Cup news",
            "What is the latest OpenAI news?",
            "Show me the latest OpenAI news.",
            "Who is the current CEO of OpenAI?",
            "How does a transformer model work?",
            "FRIDAY, start my day.",
        )
        for sample in search_samples:
            with self.subTest(sample=sample):
                self.assertTrue(should_announce_search(sample))

        self.assertEqual(
            SEARCH_ACKNOWLEDGEMENT,
            "Give me search Boss, let me check.",
        )

    def test_non_search_routes_do_not_receive_the_acknowledgement(self) -> None:
        samples = (
            "What is the weather in Da Lat?",
            "Check my Messenger",
            "What am I looking at?",
            "FRIDAY wake up",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertFalse(should_announce_search(sample))

    def test_daily_briefing_aliases_are_news_requests(self) -> None:
        for sample in ("What's new?", "Give me a daily briefing", "Start my day"):
            with self.subTest(sample=sample):
                self.assertTrue(is_news_query(sample))

    def test_visible_browser_commands_remain_separate_from_live_search_questions(self) -> None:
        self.assertTrue(is_browser_search_request("Show me the latest OpenAI news"))
        self.assertTrue(is_web_research_request("What is the latest OpenAI news?"))
        self.assertFalse(is_browser_search_request("What is the latest OpenAI news?"))

    def test_world_cup_is_preserved_as_a_specific_news_subject(self) -> None:
        query = build_world_query_text(user_text="Latest World Cup news")

        self.assertEqual(query, '("FIFA World Cup" OR "World Cup")')

    def test_generic_world_news_keeps_the_broad_world_query(self) -> None:
        samples = (
            "Latest world news",
            "What's happening in the world?",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(
                    build_world_query_text(user_text=sample),
                    DEFAULT_WORLD_QUERY,
                )

    def test_factual_questions_are_routed_to_public_research(self) -> None:
        samples = (
            "Who is Robert Downey Jr?",
            "What is a black hole?",
            "Tell me about tomato plants",
            "Latest World Cup news",
            "Who invented email?",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(is_web_research_request(sample))

    def test_dedicated_services_and_actions_keep_their_existing_routes(self) -> None:
        samples = (
            "What is the weather in Da Lat?",
            "Open YouTube",
            "Do you know what I am looking at on this screen?",
            "What am I looking at?",
            "Check my Gmail",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertFalse(is_web_research_request(sample))

    def test_research_query_removes_only_the_friday_prefix(self) -> None:
        self.assertEqual(
            build_research_query("FRIDAY, what is a black hole?"),
            "what is a black hole",
        )

    def test_context_requires_content_read_from_an_opened_page(self) -> None:
        readable = LiveSearchResult(
            ok=True,
            query="black hole",
            message="opened",
            sources=(
                LiveSearchSource(
                    title="Black hole",
                    url="https://example.org/black-hole",
                    excerpt="A black hole is an astronomical object with extremely strong gravity.",
                ),
            ),
        )
        unreadable = LiveSearchResult(
            ok=False,
            query="black hole",
            message="unreadable",
        )

        context = build_web_research_context(readable)
        self.assertIn("[WEB_RESEARCH_CONTEXT]", context)
        self.assertIn("https://example.org/black-hole", context)
        self.assertEqual(build_web_research_context(unreadable), "")

    def test_live_search_reads_multiple_sources_without_browser_automation(self) -> None:
        class FakeProvider:
            def search_results(self, query: str, *, limit: int = 5):
                return [
                    WebSearchResult("Official example", "https://example.com/official"),
                    WebSearchResult("Blocked example", "https://example.com/blocked"),
                    WebSearchResult("Independent example", "https://example.org/report"),
                ]

            def first_result(self, query: str):
                return self.search_results(query, limit=1)[0]

            def read_excerpt(self, url: str) -> str:
                if url.endswith("blocked"):
                    raise RuntimeError("blocked")
                return f"Readable evidence from {url} with enough information to summarize."

        result = search_public_web(
            "current example information",
            provider=FakeProvider(),
            max_sources=3,
        )

        self.assertTrue(result.ok)
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(result.candidate_count, 3)
        self.assertEqual(
            [source.title for source in result.sources],
            ["Official example", "Independent example"],
        )

    def test_live_search_reads_source_pages_in_parallel(self) -> None:
        class ParallelProvider:
            def __init__(self) -> None:
                self.active = 0
                self.max_active = 0
                self.lock = threading.Lock()

            def search_results(self, query: str, *, limit: int = 5):
                return [
                    WebSearchResult(f"Topic source {index}", f"https://example{index}.com/topic")
                    for index in range(3)
                ]

            def first_result(self, query: str):
                return self.search_results(query, limit=1)[0]

            def read_excerpt(self, url: str) -> str:
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                time.sleep(0.04)
                with self.lock:
                    self.active -= 1
                return f"Current topic evidence from {url}."

        provider = ParallelProvider()
        result = search_public_web(
            "current topic information",
            provider=provider,
            max_sources=3,
        )

        self.assertTrue(result.ok)
        self.assertEqual(len(result.sources), 3)
        self.assertGreater(provider.max_active, 1)

    def test_live_search_optimizes_temporal_queries_around_the_subject(self) -> None:
        self.assertEqual(
            optimize_search_query("What is the latest OpenAI news?"),
            "OpenAI news latest",
        )
        self.assertEqual(
            optimize_search_query("Who is the current CEO of OpenAI?"),
            "OpenAI current CEO",
        )
        self.assertEqual(
            optimize_search_query("Latest World Cup news"),
            "World Cup news latest",
        )


if __name__ == "__main__":
    unittest.main()
