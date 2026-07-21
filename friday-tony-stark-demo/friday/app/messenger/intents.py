from __future__ import annotations

import re


_MESSENGER_REQUEST_PATTERNS = (
    r"\b(?:check|read|show|tell me about)\s+(?:my\s+)?(?:latest|newest|new|unread)?\s*"
    r"(?:facebook\s+)?messenger\s+(?:message|messages|inbox)\b",
    r"\b(?:check|read)\s+(?:my\s+)?(?:latest|newest|new|unread)\s+facebook\s+messages?\b",
    r"\b(?:do i have|are there)\s+(?:any\s+)?(?:new|unread)\s+"
    r"(?:facebook\s+)?messenger\s+messages?\b",
    r"\bcheck\s+(?:my\s+)?messenger\b",
)


def is_messenger_latest_request(message: str) -> bool:
    normalized = " ".join(str(message or "").lower().split())
    return any(re.search(pattern, normalized) for pattern in _MESSENGER_REQUEST_PATTERNS)
