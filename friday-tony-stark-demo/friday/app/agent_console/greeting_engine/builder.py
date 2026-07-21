from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from friday.runtime_context import RuntimeLocation

from .periods import resolve_day_period
from .suggestions import get_lifestyle_suggestion, get_meal_suggestion, get_schedule_question
from .weather import WeatherContext


@dataclass(frozen=True, slots=True)
class GreetingPayload:
    message: str
    weather_summary: str | None


def build_greeting_payload(
    *, now: datetime, location: RuntimeLocation, weather: WeatherContext
) -> GreetingPayload:
    period = resolve_day_period(now.time())
    parts = [
        f"Good {period.label}, boss.",
        f"It is {now.hour:02d}:{now.minute:02d}.",
        f"I am ready for this session. Your current location context is {location.display_name}.",
        weather.summary
        or "Detailed weather is unavailable right now, so I will keep today's plan flexible.",
        get_schedule_question(period.name),
        get_lifestyle_suggestion(period.name, weather.mood),
        get_meal_suggestion(period.name),
    ]
    return GreetingPayload(message=" ".join(parts), weather_summary=weather.summary)
