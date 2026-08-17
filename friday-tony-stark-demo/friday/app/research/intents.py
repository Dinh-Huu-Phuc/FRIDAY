"""Routing rules for factual questions that require public web research."""

from __future__ import annotations

import re


_QUESTION_START = re.compile(
    r"^(?:who|what|when|where|why|how|which|whose|whom)\b",
    re.IGNORECASE,
)
_RESEARCH_START = re.compile(
    r"^(?:tell me(?: about)?|give me|explain|define|identify|look up|find information about|"
    r"do you know|latest|current|recent)\b",
    re.IGNORECASE,
)
_FRIDAY_PREFIX = re.compile(r"^friday[\s,.:;-]*", re.IGNORECASE)
_COURTESY_PREFIX = re.compile(
    r"^(?:(?:please|kindly)[\s,]+)?"
    r"(?:(?:can|could|would|will)\s+you[\s,]+)?",
    re.IGNORECASE,
)
_POLITE_PREFIX = re.compile(
    r"^(?:(?:please|kindly)[\s,]+)?"
    r"(?:(?:can|could|would|will)\s+you[\s,]+)?"
    r"(?:(?:please\s+)?(?:tell|give)\s+me(?:\s+about)?\s+|"
    r"i(?:'d| would)?\s+like\s+to\s+know(?:\s+about)?\s+)",
    re.IGNORECASE,
)
_ACTION_START = re.compile(
    r"^(?:open|launch|start|close|stop|send|write|create|delete|remove|"
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
_FRESHNESS_SIGNAL = re.compile(
    r"\b(?:today(?:'s)?|tonight|now|right now|currently|current|latest|recent|"
    r"live|as of|this (?:week|month|year)|yesterday)\b",
    re.IGNORECASE,
)
_VOLATILE_FACT_SIGNAL = re.compile(
    r"\b(?:price|worth|exchange rate|market cap|stock price|crypto price|"
    r"score|result|standings|schedule|availability|release date|version)\b",
    re.IGNORECASE,
)


def build_research_query(message: str) -> str:
    candidate = _FRIDAY_PREFIX.sub("", str(message or "").strip())
    candidate = _POLITE_PREFIX.sub("", candidate)
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate.strip(" \t\r\n.,!?;:\"'")[:300]


def is_web_research_request(message: str) -> bool:
    routed_candidate = _FRIDAY_PREFIX.sub("", str(message or "").strip())
    action_candidate = _COURTESY_PREFIX.sub("", routed_candidate)
    has_research_lead_in = bool(
        _RESEARCH_START.match(routed_candidate) or _POLITE_PREFIX.match(routed_candidate)
    )
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
    if _ACTION_START.match(query) or _ACTION_START.match(action_candidate):
        return False
    if "news" in lowered or "headline" in lowered:
        return True
    if _FRESHNESS_SIGNAL.search(query) or _VOLATILE_FACT_SIGNAL.search(query):
        return True
    return bool(
        has_research_lead_in
        or _QUESTION_START.match(query)
        or _RESEARCH_START.match(query)
    )
