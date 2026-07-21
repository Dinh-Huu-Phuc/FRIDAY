from __future__ import annotations

from datetime import datetime

from friday.app.agent_console.greeting_engine import (
    GreetingPayload,
    build_greeting_payload,
    build_weather_context,
)
from friday.runtime_context import resolve_runtime_location
from friday.search import get_weather_snapshot


async def build_startup_greeting_payload() -> GreetingPayload:
    location = resolve_runtime_location()
    try:
        snapshot = await get_weather_snapshot(city=location.city, country=location.country)
    except Exception:
        snapshot = {"ok": False}

    weather = build_weather_context(snapshot, fallback_location=location.display_name)
    return build_greeting_payload(now=datetime.now(), location=location, weather=weather)


async def build_startup_greeting_message() -> str:
    return (await build_startup_greeting_payload()).message


async def build_startup_weather_summary() -> str:
    payload = await build_startup_greeting_payload()
    return payload.weather_summary or ""
