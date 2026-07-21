"""Browser abstraction used by social services to open platform homepages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import webbrowser

from friday.app.common.messages import OPEN_FAILED_MESSAGE, OPEN_SUCCESS_MESSAGE


@dataclass(slots=True, frozen=True)
class TabOpenResult:
    platform_name: str
    url: str
    opened_in_new_tab: bool
    message: str = OPEN_SUCCESS_MESSAGE


class BrowserGateway(Protocol):
    def open_new_tab(self, url: str) -> bool:
        """Open the given URL in a browser tab."""


class DefaultBrowserGateway:
    """Default browser gateway backed by the stdlib webbrowser module."""

    def open_new_tab(self, url: str) -> bool:
        return bool(webbrowser.open_new_tab(url))


class BrowserManager:
    """Thin manager around the active browser gateway."""

    def __init__(self, gateway: BrowserGateway | None = None) -> None:
        self.gateway = gateway or DefaultBrowserGateway()

    def open_url(self, *, platform_name: str, url: str) -> TabOpenResult:
        opened = bool(self.gateway.open_new_tab(url))
        return TabOpenResult(
            platform_name=platform_name,
            url=url,
            opened_in_new_tab=opened,
            message=OPEN_SUCCESS_MESSAGE if opened else OPEN_FAILED_MESSAGE,
        )
