from __future__ import annotations

import secrets
from dataclasses import replace

from friday.app.browser_automation.controller import BrowserControlError, ChromeController
from friday.app.browser_automation.binance import get_binance_urls
from friday.app.browser_automation.intents import (
    parse_binance_market_command,
    parse_browser_search_command,
    parse_platform_video_search_command,
)
from friday.app.browser_automation.reader import BingResearchProvider, ResearchProvider
from friday.app.browser_automation.schemas import (
    BrowserAutomationResult,
    PlatformVideoSearchResult,
)


def run_platform_video_search(
    message: str,
    *,
    controller: ChromeController | None = None,
    result_index: int | None = None,
) -> PlatformVideoSearchResult:
    command = parse_platform_video_search_command(message)
    if command is None:
        return PlatformVideoSearchResult(
            False,
            "",
            "",
            0,
            "That is not a supported YouTube or TikTok video search command.",
        )

    selected_index = (
        secrets.randbelow(3) if result_index is None else max(0, min(2, result_index))
    )
    try:
        (controller or ChromeController()).search_platform_videos(
            platform=command.platform,
            query=command.query,
            result_index=selected_index,
        )
    except BrowserControlError as exc:
        return PlatformVideoSearchResult(
            False,
            command.platform,
            command.query,
            selected_index + 1,
            str(exc),
        )
    except Exception:
        return PlatformVideoSearchResult(
            False,
            command.platform,
            command.query,
            selected_index + 1,
            f"I opened {command.platform.title()}, but could not select a video result.",
        )

    display_name = "YouTube" if command.platform == "youtube" else "TikTok"
    return PlatformVideoSearchResult(
        True,
        command.platform,
        command.query,
        selected_index + 1,
        f"Playing one of the first three {display_name} results for {command.query}.",
    )


def run_binance_market(
    message: str,
    *,
    controller: ChromeController | None = None,
) -> BrowserAutomationResult:
    command = parse_binance_market_command(message)
    if command is None:
        return BrowserAutomationResult(
            False,
            "",
            "Tell me which supported coin you want to open on Binance.",
        )
    try:
        overview_url, trade_url = get_binance_urls(command.symbol)
        (controller or ChromeController()).open_binance_market(
            overview_url=overview_url,
            trade_url=trade_url,
            symbol=command.symbol,
            asset_name=command.asset_name,
        )
    except (BrowserControlError, ValueError) as exc:
        return BrowserAutomationResult(False, command.symbol, str(exc))
    except Exception:
        return BrowserAutomationResult(
            False,
            command.symbol,
            f"I could not finish opening {command.asset_name} on Binance.",
        )
    return BrowserAutomationResult(
        True,
        command.symbol,
        f"I opened Binance Markets and the {command.symbol}/USDT trading page.",
        title=f"Binance {command.symbol}/USDT",
        url=trade_url,
    )


def run_browser_search(
    message: str,
    *,
    controller: ChromeController | None = None,
    research: ResearchProvider | None = None,
) -> BrowserAutomationResult:
    command = parse_browser_search_command(message)
    if command is None:
        return BrowserAutomationResult(False, "", "That is not a Chrome new-tab search command.")

    result = run_browser_research(
        command.query,
        controller=controller,
        research=research,
    )
    if not result.ok:
        return result
    return replace(
        result,
        message=(
            f"I opened {result.title}. Here is a short passage: {result.excerpt}"
        ),
    )


def run_browser_research(
    query: str,
    *,
    controller: ChromeController | None = None,
    research: ResearchProvider | None = None,
) -> BrowserAutomationResult:
    normalized_query = str(query or "").strip()
    if not normalized_query or len(normalized_query) > 300:
        return BrowserAutomationResult(False, "", "The research query is empty or too long.")

    active_controller = controller or ChromeController()
    active_research = research or BingResearchProvider()
    try:
        active_controller.search_in_new_tab(normalized_query)
        search_results = getattr(active_research, "search_results", None)
        if callable(search_results):
            candidates = search_results(normalized_query, limit=5)
        else:
            first_result = active_research.first_result(normalized_query)
            candidates = [first_result] if first_result is not None else []
        if not candidates:
            return BrowserAutomationResult(
                False,
                normalized_query,
                f"I searched for {normalized_query}, but I could not select a safe public result to open.",
            )

        last_result = candidates[0]
        for result in candidates:
            last_result = result
            active_controller.open_url(result.url)
            try:
                excerpt = active_research.read_excerpt(result.url)
            except Exception:
                excerpt = ""
            if excerpt:
                return BrowserAutomationResult(
                    True,
                    normalized_query,
                    f"I opened {result.title} and read the page.",
                    title=result.title,
                    url=result.url,
                    excerpt=excerpt,
                )

        return BrowserAutomationResult(
            False,
            normalized_query,
            "I opened the available results, but none provided readable public content.",
            title=last_result.title,
            url=last_result.url,
        )
    except BrowserControlError as exc:
        return BrowserAutomationResult(False, normalized_query, str(exc))
    except Exception:
        return BrowserAutomationResult(
            False,
            normalized_query,
            "I started the Chrome search but could not read a safe public page.",
        )
