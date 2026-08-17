from __future__ import annotations

import re

from friday.app import is_social_open_request as _is_social_open_request

WINDOWS_APP_OPEN_INTENT_PATTERN = re.compile(r"\b(open|launch|start|run)\b", re.IGNORECASE)
WINDOWS_APP_CLEANUP_PATTERN = re.compile(
    r"\b(friday|firday|please|could\s+you|would\s+you|for\s+me|app|application)\b",
    re.IGNORECASE,
)
BROWSER_TARGET_PATTERN = re.compile(
    r"\b(browser|binance|youtube|tik\s*tok|website|webpage|url|new\s+tab|camera|webcam)\b",
    re.IGNORECASE,
)
DAILY_BRIEFING_PATTERN = re.compile(
    r"\b(briefing|daily\s+brief|quick\s+report|start\s+my\s+day|today'?s\s+summary|what'?s\s+new|unfinished\s+work)\b",
    re.IGNORECASE,
)
GMAIL_CHECK_PATTERN = re.compile(
    r"\b(check|read|review|scan)\s+(my\s+)?(email|emails|gmail|mail|inbox)\b|\b(unread|new)\s+(email|emails|mail)\b",
    re.IGNORECASE,
)


def is_social_open_request(text: str) -> bool:
    return _is_social_open_request(text)


def is_daily_briefing_request(text: str) -> bool:
    return bool(DAILY_BRIEFING_PATTERN.search(str(text or "").strip()))


def is_gmail_check_request(text: str) -> bool:
    return bool(GMAIL_CHECK_PATTERN.search(str(text or "").strip()))


def extract_windows_app_query(text: str) -> str:
    candidate = str(text or "").strip()
    if (
        not candidate
        or not WINDOWS_APP_OPEN_INTENT_PATTERN.search(candidate)
        or BROWSER_TARGET_PATTERN.search(candidate)
    ):
        return ""
    without_verb = WINDOWS_APP_OPEN_INTENT_PATTERN.sub(" ", candidate, count=1)
    cleaned = WINDOWS_APP_CLEANUP_PATTERN.sub(" ", without_verb)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.!?;:-")
    return cleaned or candidate
