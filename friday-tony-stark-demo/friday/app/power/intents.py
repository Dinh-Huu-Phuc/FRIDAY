"""Public intent-matching API for FRIDAY's background power state."""

from __future__ import annotations

from .name.matcher import match_power_phrase
from .types import PowerIntent, PowerIntentMatch


def match_power_intent(message: str) -> PowerIntentMatch:
    return match_power_phrase(message)


def detect_power_intent(message: str) -> PowerIntent:
    return match_power_intent(message).intent
