from __future__ import annotations

import re
from typing import Any

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer|password|passwd|secret|token)\b"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_URL_CREDENTIALS = re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/\s]+:)([^@\s]+)(@)")
_WHITESPACE = re.compile(r"\s+")


def sanitize_neural_summary(value: Any, *, maximum: int = 150) -> str:
    text = _WHITESPACE.sub(" ", str(value or "")).strip()
    text = _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", text)
    text = _URL_CREDENTIALS.sub(r"\1[REDACTED]\3", text)
    if len(text) <= maximum:
        return text
    return f"{text[: max(1, maximum - 3)].rstrip()}..."

