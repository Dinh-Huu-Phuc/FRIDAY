"""Shared browser, env, and runtime messages for social app modules."""

from friday.app.common.browser import BrowserGateway, BrowserManager, DefaultBrowserGateway, TabOpenResult
from friday.app.common.messages import OPEN_SUCCESS_MESSAGE, UNKNOWN_PLATFORM_MESSAGE

__all__ = [
    "BrowserGateway",
    "BrowserManager",
    "DefaultBrowserGateway",
    "OPEN_SUCCESS_MESSAGE",
    "TabOpenResult",
    "UNKNOWN_PLATFORM_MESSAGE",
]
