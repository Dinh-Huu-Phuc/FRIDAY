"""Voice and text intent parsing for local Windows application launches."""

from __future__ import annotations

import re

_LAUNCH_PATTERN = re.compile(
    r"^\s*"
    r"(?:(?:hey\s+)?friday[\s,:-]*)?"
    r"(?:please\s+)?"
    r"(?P<verb>open|launch|start|run)\s+"
    r"(?P<target>.+?)"
    r"(?:\s+(?:for\s+me|please|now))?"
    r"\s*[.!?]*\s*$",
    re.IGNORECASE,
)
_NON_APPLICATION_TARGETS = {
    "a cycle",
    "all monitors",
    "all my monitors",
    "all my screens",
    "browser search",
    "camera",
    "camera window",
    "code map",
    "cycle",
    "live search",
    "my day",
    "neural network",
    "new tab",
    "the code map",
    "the neural network",
    "webcam",
}
_BROWSER_ACTION_WORDS = {
    "binance",
    "browser",
    "search",
    "tiktok",
    "url",
    "webpage",
    "website",
    "youtube",
}


def extract_windows_app_query(message: str) -> str | None:
    """Return an app name only for an explicit local launch command."""

    match = _LAUNCH_PATTERN.match(str(message or ""))
    if match is None:
        return None

    target = " ".join(match.group("target").split())
    target = re.sub(
        r"\s+(?:for\s+me|please|now)$",
        "",
        target,
        flags=re.IGNORECASE,
    ).strip(" \t\r\n.,!?;:'\"")
    target = re.sub(r"^(?:the|app|application)\s+", "", target, flags=re.IGNORECASE)
    normalized = target.casefold()

    if not target or normalized in _NON_APPLICATION_TARGETS:
        return None
    if any(re.search(rf"\b{word}\b", normalized) for word in _BROWSER_ACTION_WORDS):
        return None
    if re.search(r"\b(?:tab|screen|monitor)\b", normalized):
        return None
    return target
