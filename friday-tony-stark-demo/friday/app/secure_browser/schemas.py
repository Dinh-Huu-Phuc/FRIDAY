from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SecureBrowserAction(str, Enum):
    NONE = "none"
    OPEN = "open"
    NAVIGATE_CURRENT = "navigate_current"
    CLOSE_CURRENT = "close_current"
    CLOSE_ALL = "close_all"
    CLEAR_HISTORY = "clear_history"
    OPEN_SETTINGS = "open_settings"


@dataclass(frozen=True, slots=True)
class SecureBrowserIntent:
    action: SecureBrowserAction = SecureBrowserAction.NONE
    url: str = ""
    query: str = ""
    trigger_id: str = ""


@dataclass(frozen=True, slots=True)
class SecureBrowserRequest:
    action: SecureBrowserAction
    url: str = ""
    query: str = ""
    animate_query: bool = False


@dataclass(frozen=True, slots=True)
class SecureBrowserCommandResult:
    handled: bool
    accepted: bool = False
    action: SecureBrowserAction = SecureBrowserAction.NONE
    message: str = ""
