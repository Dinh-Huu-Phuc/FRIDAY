"""Rotating spoken responses for allowlisted power commands."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock


POWER_RESPONSES: dict[str, tuple[str, ...]] = {
    "sleep_direct": (
        "Understood, Boss. Entering sleep mode.",
        "Of course, Boss. I'll remain quiet until you call me.",
        "Going to sleep now, Boss. Call me when you need me.",
    ),
    "sleep_standby": (
        "Understood, Boss. Entering standby mode.",
        "Powering down my active systems, Boss. I'll stay on standby.",
        "Standing by, Boss. Wake me when you're ready.",
    ),
    "sleep_thanks": (
        "You're welcome, Boss. I'll be here when you need me.",
        "Anytime, Boss. I'll go quiet for now.",
        "My pleasure, Boss. Call me when you need me again.",
    ),
    "sleep_goodbye": (
        "Good night, Boss. I'll be here when you call.",
        "Rest well, Boss. FRIDAY is entering sleep mode.",
        "Understood, Boss. I'll see you when you wake me.",
    ),
    "wake_presence": (
        "I'm here, Boss. What do you need help with?",
        "Right here, Boss. How can I help?",
        "I'm with you, Boss. What do you need?",
    ),
    "wake_online": (
        "FRIDAY is online, Boss. Systems are ready.",
        "Online and ready, Boss. What is our next move?",
        "All systems are available, Boss. How can I help?",
    ),
    "wake_resume": (
        "I'm back, Boss. Ready when you are.",
        "Active again, Boss. What should we do next?",
        "Resuming operations, Boss. I'm ready.",
    ),
    "wake_summon": (
        "Yes, Boss. I'm listening.",
        "I'm here, Boss. How can I help?",
        "At your service, Boss. What do you need?",
    ),
    "already_sleeping": (
        "I'm already in sleep mode, Boss.",
        "Still on standby, Boss. Say FRIDAY wake up when you need me.",
    ),
    "already_awake": (
        "I'm already awake, Boss.",
        "Online and listening, Boss.",
    ),
}

_response_positions: defaultdict[str, int] = defaultdict(int)
_response_lock = Lock()


def select_power_response(group: str) -> str:
    responses = POWER_RESPONSES.get(group, ())
    if not responses:
        return ""
    with _response_lock:
        position = _response_positions[group]
        _response_positions[group] = position + 1
    return responses[position % len(responses)]


def _reset_response_rotation_for_tests() -> None:
    with _response_lock:
        _response_positions.clear()

