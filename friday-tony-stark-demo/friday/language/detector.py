from __future__ import annotations

import re

from .constants import LANGUAGE_ALIASES
from .schemas import LanguageDetectionResult

_PERSISTENT_PATTERNS = (
    re.compile(r"\bfrom now on\b", re.IGNORECASE),
    re.compile(r"\balways answer\b", re.IGNORECASE),
)
_SWITCH_PATTERNS = (
    re.compile(r"\bswitch to english\b", re.IGNORECASE),
    re.compile(r"\banswer in english\b", re.IGNORECASE),
)


def detect_language_switch(user_text: str) -> LanguageDetectionResult:
    text = user_text.strip()
    if not text:
        return LanguageDetectionResult(should_switch=False)
    lowered = text.lower()
    persistent = any(pattern.search(text) for pattern in _PERSISTENT_PATTERNS)
    if any(pattern.search(text) for pattern in _SWITCH_PATTERNS):
        return LanguageDetectionResult(should_switch=True, language="en", persistent=persistent)
    for token, target in LANGUAGE_ALIASES.items():
        if target == "en" and token in lowered and any(word in lowered for word in ("switch", "answer")):
            return LanguageDetectionResult(should_switch=True, language="en", persistent=persistent)
    return LanguageDetectionResult(should_switch=False)
