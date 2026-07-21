from __future__ import annotations

from datetime import datetime

from .periods import DayPeriodName, resolve_day_period


_STARTUP_MESSAGES: dict[DayPeriodName, str] = {
    "morning": "Good morning, boss. FRIDAY is online. Let us make a calm, focused start.",
    "noon": "Good afternoon, boss. FRIDAY is online. Take a breath, and we will set the right pace for the afternoon.",
    "afternoon": "Good afternoon, boss. FRIDAY is online and ready to help you finish the day well.",
    "evening": "Good evening, boss. FRIDAY is online. Let us keep things clear and unhurried.",
    "night": "It is late, boss. FRIDAY is online. Take a breath, stay calm, and tell me what you need.",
}

_WAKE_MESSAGES: dict[DayPeriodName, str] = {
    "morning": "Good morning, boss. I am awake and ready. Let us begin with a clear mind.",
    "noon": "Good afternoon, boss. I am awake. Take a breath, and we will continue at a steady pace.",
    "afternoon": "Good afternoon, boss. I am awake and ready to continue where we left off.",
    "evening": "Good evening, boss. I am awake. Let us keep things calm and focused.",
    "night": "I am awake, boss. It is late, so take a breath, stay calm, and tell me what you need.",
}


def build_time_greeting(*, now: datetime | None = None, event: str = "startup") -> str:
    current = now or datetime.now()
    period = resolve_day_period(current.time())
    messages = _WAKE_MESSAGES if event == "wake" else _STARTUP_MESSAGES
    return messages[period.name]
