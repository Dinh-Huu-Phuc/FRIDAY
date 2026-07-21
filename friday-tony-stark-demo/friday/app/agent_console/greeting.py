from __future__ import annotations

from datetime import datetime

from friday.app.agent_console.greeting_engine import build_greeting_payload, build_weather_context
from friday.app.agent_console.schemas import ConsoleGreetingResponse
from friday.runtime_context import resolve_runtime_location
from friday.search import get_weather_snapshot


async def build_console_greeting() -> ConsoleGreetingResponse:
    now = datetime.now()
    location = resolve_runtime_location()

    try:
        snapshot = await get_weather_snapshot(city=location.city, country=location.country)
    except Exception:
        snapshot = {"ok": False}

    weather = build_weather_context(snapshot, fallback_location=location.display_name)
    greeting = build_greeting_payload(now=now, location=location, weather=weather)

    return ConsoleGreetingResponse(
        message=greeting.message,
        location=location.display_name,
        weather_summary=greeting.weather_summary,
        source="api",
    )
