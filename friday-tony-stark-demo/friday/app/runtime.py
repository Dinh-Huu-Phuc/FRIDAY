"""High-level runtime entrypoints for social website open commands."""

from __future__ import annotations

from friday.app.common.browser import BrowserManager
from friday.app.common.messages import OPEN_FAILED_MESSAGE, UNKNOWN_PLATFORM_MESSAGE
from friday.app.registry import build_social_search_url, get_platform_service, parse_social_command


def open_social_platform(
    command: str,
    *,
    browser_manager: BrowserManager | None = None,
) -> str:
    parsed = parse_social_command(command)
    if parsed is None:
        return UNKNOWN_PLATFORM_MESSAGE

    if parsed.query:
        active_browser = browser_manager or BrowserManager()
        result = active_browser.open_url(
            platform_name=parsed.platform_name,
            url=build_social_search_url(parsed.platform_name, parsed.query),
        )
        if not result.opened_in_new_tab:
            return OPEN_FAILED_MESSAGE
        display_name = parsed.platform_name.upper() if parsed.platform_name == "x" else parsed.platform_name.title()
        return f"Opened {display_name} search results for {parsed.query}, boss."

    service = get_platform_service(parsed.platform_name, browser_manager=browser_manager)
    response = service.open_platform_homepage()
    return response.message
