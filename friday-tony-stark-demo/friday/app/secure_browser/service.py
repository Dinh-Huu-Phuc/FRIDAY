from __future__ import annotations

from friday.app.secure_browser.command_bus import get_secure_browser_command_bus
from friday.app.secure_browser.intents import match_secure_browser_intent
from friday.app.secure_browser.navigation import google_search_url
from friday.app.secure_browser.schemas import (
    SecureBrowserAction,
    SecureBrowserCommandResult,
    SecureBrowserRequest,
)
from friday.app.secure_browser.settings import get_secure_browser_settings


def open_secure_browser_url(
    url: str,
    *,
    query: str = "",
) -> SecureBrowserCommandResult:
    settings = get_secure_browser_settings()
    if not settings.enabled:
        return SecureBrowserCommandResult(
            handled=True,
            action=SecureBrowserAction.OPEN,
            message="The FRIDAY Browser is disabled in local settings, Boss.",
        )

    request = SecureBrowserRequest(
        action=SecureBrowserAction.OPEN,
        url=str(url or settings.home_url),
        query=str(query or "").strip(),
    )
    accepted = get_secure_browser_command_bus().dispatch(request)
    if not accepted:
        return SecureBrowserCommandResult(
            handled=True,
            action=SecureBrowserAction.OPEN,
            message=(
                "The FRIDAY Browser is available when the desktop interface "
                "is running, Boss."
            ),
        )

    return SecureBrowserCommandResult(
        handled=True,
        accepted=True,
        action=SecureBrowserAction.OPEN,
        message=(
            f"Opening a new FRIDAY Browser window for {query}, Boss."
            if query
            else "Opening a new FRIDAY Browser window, Boss."
        ),
    )


def open_secure_browser_search(query: str) -> SecureBrowserCommandResult:
    normalized_query = " ".join(str(query or "").split()).strip()
    if not normalized_query:
        return SecureBrowserCommandResult(
            handled=True,
            action=SecureBrowserAction.OPEN,
            message="Tell me what you want to search for, Boss.",
        )

    settings = get_secure_browser_settings()
    if not settings.enabled:
        return SecureBrowserCommandResult(
            handled=True,
            action=SecureBrowserAction.OPEN,
            message="The FRIDAY Browser is disabled in local settings, Boss.",
        )

    accepted = get_secure_browser_command_bus().dispatch(
        SecureBrowserRequest(
            action=SecureBrowserAction.OPEN,
            url=google_search_url(normalized_query),
            query=normalized_query,
            animate_query=True,
        )
    )
    return SecureBrowserCommandResult(
        handled=True,
        accepted=accepted,
        action=SecureBrowserAction.OPEN,
        message=(
            f"Searching for {normalized_query} in FRIDAY Browser, Boss."
            if accepted
            else (
                "The FRIDAY Browser is available when the desktop interface "
                "is running, Boss."
            )
        ),
    )


def navigate_current_browser_url(url: str) -> SecureBrowserCommandResult:
    target = str(url or "").strip()
    if not target:
        return SecureBrowserCommandResult(
            handled=True,
            action=SecureBrowserAction.NAVIGATE_CURRENT,
            message="The selected browser result did not provide a URL, Boss.",
        )
    accepted = get_secure_browser_command_bus().dispatch(
        SecureBrowserRequest(
            action=SecureBrowserAction.NAVIGATE_CURRENT,
            url=target,
        )
    )
    return SecureBrowserCommandResult(
        handled=True,
        accepted=accepted,
        action=SecureBrowserAction.NAVIGATE_CURRENT,
        message=(
            "Opening the selected result in FRIDAY Browser, Boss."
            if accepted
            else (
                "The FRIDAY Browser is available when the desktop interface "
                "is running, Boss."
            )
        ),
    )


def handle_secure_browser_message(message: str) -> SecureBrowserCommandResult:
    intent = match_secure_browser_intent(message)
    if intent.action == SecureBrowserAction.NONE:
        return SecureBrowserCommandResult(handled=False)

    settings = get_secure_browser_settings()
    if not settings.enabled:
        return SecureBrowserCommandResult(
            handled=True,
            action=intent.action,
            message="The FRIDAY Browser is disabled in local settings, Boss.",
        )

    if intent.action == SecureBrowserAction.OPEN:
        return open_secure_browser_url(
            intent.url or settings.home_url,
            query=intent.query,
        )

    request = SecureBrowserRequest(
        action=intent.action,
        url=intent.url or settings.home_url,
        query=intent.query,
    )
    accepted = get_secure_browser_command_bus().dispatch(request)
    if not accepted:
        return SecureBrowserCommandResult(
            handled=True,
            action=intent.action,
            message=(
                "The FRIDAY Browser is available when the desktop interface "
                "is running, Boss."
            ),
        )

    replies = {
        SecureBrowserAction.CLOSE_CURRENT: (
            "Closing the current FRIDAY Browser window, Boss."
        ),
        SecureBrowserAction.CLOSE_ALL: (
            "Closing all FRIDAY Browser windows, Boss."
        ),
        SecureBrowserAction.CLEAR_HISTORY: (
            "FRIDAY Browser history has been cleared, Boss."
        ),
        SecureBrowserAction.OPEN_SETTINGS: (
            "Opening FRIDAY Browser settings, Boss."
        ),
    }
    return SecureBrowserCommandResult(
        handled=True,
        accepted=True,
        action=intent.action,
        message=replies[intent.action],
    )
