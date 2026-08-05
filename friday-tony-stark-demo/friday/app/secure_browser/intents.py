from __future__ import annotations

import re

from friday.app.secure_browser.navigation import FRIDAY_HOME_URL, navigation_url
from friday.app.secure_browser.schemas import SecureBrowserAction, SecureBrowserIntent

_PREFIX = r"^(?:friday[\s,.:;-]*)?(?:please\s+)?"
_FRIDAY_PREFIX = r"^friday[\s,.:;-]*(?:please\s+)?"
_BROWSER_NAME = r"(?:the\s+)?(?:friday\s+)?(?:secure\s+)?browser(?:\s+window)?"
_END = r"\s*[.!?]*\s*$"

_CLOSE_CURRENT_PATTERN = re.compile(
    _PREFIX
    + r"(?:close|hide|exit)\s+(?:this|the\s+current|current)\s+"
    + r"(?:friday\s+)?(?:secure\s+)?browser(?:\s+window)?"
    + _END,
    re.IGNORECASE,
)
_CLOSE_ALL_PATTERN = re.compile(
    _PREFIX
    + r"(?:close|hide|exit|shut\s+down)\s+all\s+"
    + r"(?:the\s+)?(?:friday\s+)?(?:secure\s+)?browser\s+windows?"
    + _END,
    re.IGNORECASE,
)
_CLOSE_PATTERN = re.compile(
    _PREFIX + r"(?:close|hide|exit|shut\s+down)\s+" + _BROWSER_NAME + _END,
    re.IGNORECASE,
)
_CLEAR_HISTORY_PATTERN = re.compile(
    _PREFIX
    + r"(?:clear|delete|erase)\s+(?:the\s+)?(?:browser|browsing)\s+history"
    + _END,
    re.IGNORECASE,
)
_OPEN_SETTINGS_PATTERN = re.compile(
    _PREFIX
    + r"(?:open|show)\s+(?:the\s+)?(?:friday\s+)?browser\s+settings"
    + _END,
    re.IGNORECASE,
)
_OPEN_HOME_PATTERN = re.compile(
    _PREFIX + r"(?:open|launch|show|start)\s+(?:a\s+)?" + _BROWSER_NAME + _END,
    re.IGNORECASE,
)
_OPEN_SEARCH_PATTERN = re.compile(
    _PREFIX
    + r"(?:open|launch|show|start)\s+(?:a\s+)?"
    + _BROWSER_NAME
    + r"\s*(?:and\s+)?(?:search|find|look\s+up)(?:\s+(?:for|about))?\s+"
    + r"(?P<query>.+?)"
    + _END,
    re.IGNORECASE,
)
_SEARCH_IN_BROWSER_PATTERN = re.compile(
    _PREFIX
    + r"(?:search|find|look\s+up)(?:\s+(?:for|about))?\s+"
    + r"(?P<query>.+?)\s+(?:in|using|with)\s+"
    + _BROWSER_NAME
    + _END,
    re.IGNORECASE,
)
_DIRECT_SEARCH_PATTERN = re.compile(
    _FRIDAY_PREFIX
    + r"(?:search|find|look\s+up)(?:\s+(?:for|about))?\s+"
    + r"(?P<query>.+?)"
    + _END,
    re.IGNORECASE,
)
_OPEN_TARGET_PATTERN = re.compile(
    _PREFIX
    + r"(?:open|launch|show|start)\s+(?:a\s+)?"
    + _BROWSER_NAME
    + r"\s+(?:to|at|on)\s+(?P<target>.+?)"
    + _END,
    re.IGNORECASE,
)


def _clean_target(value: str) -> str:
    return " ".join(str(value or "").split()).strip(" \t\r\n.,!?;:\"'")


def match_secure_browser_intent(message: str) -> SecureBrowserIntent:
    candidate = str(message or "").strip()
    if not candidate:
        return SecureBrowserIntent()

    if _CLOSE_CURRENT_PATTERN.fullmatch(candidate):
        return SecureBrowserIntent(
            action=SecureBrowserAction.CLOSE_CURRENT,
            trigger_id="close_current_browser",
        )

    if _CLOSE_ALL_PATTERN.fullmatch(candidate):
        return SecureBrowserIntent(
            action=SecureBrowserAction.CLOSE_ALL,
            trigger_id="close_all_browsers",
        )

    if _CLOSE_PATTERN.fullmatch(candidate):
        return SecureBrowserIntent(
            action=SecureBrowserAction.CLOSE_CURRENT,
            trigger_id="close_browser",
        )

    if _CLEAR_HISTORY_PATTERN.fullmatch(candidate):
        return SecureBrowserIntent(
            action=SecureBrowserAction.CLEAR_HISTORY,
            trigger_id="clear_browser_history",
        )

    if _OPEN_SETTINGS_PATTERN.fullmatch(candidate):
        return SecureBrowserIntent(
            action=SecureBrowserAction.OPEN_SETTINGS,
            trigger_id="open_browser_settings",
        )

    for pattern, trigger_id in (
        (_OPEN_SEARCH_PATTERN, "open_and_search"),
        (_SEARCH_IN_BROWSER_PATTERN, "search_in_browser"),
        (_DIRECT_SEARCH_PATTERN, "direct_search"),
    ):
        match = pattern.fullmatch(candidate)
        if match:
            query = _clean_target(match.group("query"))
            if query and len(query) <= 300:
                return SecureBrowserIntent(
                    action=SecureBrowserAction.OPEN,
                    url=navigation_url(query),
                    query=query,
                    trigger_id=trigger_id,
                )
            return SecureBrowserIntent()

    target_match = _OPEN_TARGET_PATTERN.fullmatch(candidate)
    if target_match:
        target = _clean_target(target_match.group("target"))
        if target and len(target) <= 500:
            return SecureBrowserIntent(
                action=SecureBrowserAction.OPEN,
                url=navigation_url(target),
                trigger_id="open_target",
            )
        return SecureBrowserIntent()

    if _OPEN_HOME_PATTERN.fullmatch(candidate):
        return SecureBrowserIntent(
            action=SecureBrowserAction.OPEN,
            url=FRIDAY_HOME_URL,
            trigger_id="open_home",
        )

    return SecureBrowserIntent()
