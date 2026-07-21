"""Routing rules for factual questions that require public web research."""

from __future__ import annotations

import re


_QUESTION_START = re.compile(
    r"^(?:who|what|when|where|why|how|which|whose|whom)\b",
    re.IGNORECASE,
)
_RESEARCH_START = re.compile(
    r"^(?:tell me about|explain|define|identify|look up|find information about|"
    r"do you know|latest|current|recent)\b",
    re.IGNORECASE,
)
_FRIDAY_PREFIX = re.compile(r"^friday[\s,.:;-]*", re.IGNORECASE)
_ACTION_START = re.compile(
    r"^(?:open|launch|start|close|stop|check|send|write|create|delete|remove|"
    r"play|pause|call|message|email)\b",
    re.IGNORECASE,
)
_LOCAL_ONLY_SIGNALS = (
    "this screen",
    "my screen",
    "what am i looking at",
    "what are we looking at",
    "this code",
    "my code",
    "this file",
    "my file",
    "my computer",
    "my account",
)
_DEDICATED_SERVICE_SIGNALS = (
    "weather",
    "forecast",
    "temperature",
    "humidity",
)
_PRIVATE_SERVICE_SIGNALS = ("my email", "my gmail", "my messenger", "my inbox", "unread email")


def build_research_query(message: str) -> str:
    candidate = _FRIDAY_PREFIX.sub("", str(message or "").strip())
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate.strip(" \t\r\n.,!?;:\"'")[:300]


def is_web_research_request(message: str) -> bool:
    query = build_research_query(message)
    if len(query) < 3:
        return False
    lowered = query.lower()
    if any(signal in lowered for signal in _LOCAL_ONLY_SIGNALS):
        return False
    if any(signal in lowered for signal in _DEDICATED_SERVICE_SIGNALS):
        return False
    if any(signal in lowered for signal in _PRIVATE_SERVICE_SIGNALS):
        return False
    if _ACTION_START.match(query):
        return False
    if "news" in lowered or "headline" in lowered:
        return True
    return bool(_QUESTION_START.match(query) or _RESEARCH_START.match(query))
