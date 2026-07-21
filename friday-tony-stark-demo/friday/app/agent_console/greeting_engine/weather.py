from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

WeatherMood = Literal["rainy", "hot", "cold", "pleasant", "cloudy", "unknown"]

RAIN_KEYWORDS = ("rain", "drizzle", "thunderstorm", "storm", "shower")
CLEAR_KEYWORDS = ("clear", "sunny")
CLOUDY_KEYWORDS = ("cloud", "overcast")


@dataclass(frozen=True, slots=True)
class WeatherContext:
    mood: WeatherMood
    summary: str | None
    location_text: str
    description: str
    temperature_c: float | None


def _parse_temperature(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ".").strip())
        except ValueError:
            return None
    return None


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    normalized = value.lower()
    return any(keyword in normalized for keyword in keywords)


def _resolve_weather_mood(description: str, temperature_c: float | None) -> WeatherMood:
    if _contains_any(description, RAIN_KEYWORDS):
        return "rainy"
    if temperature_c is not None and temperature_c >= 32:
        return "hot"
    if temperature_c is not None and temperature_c <= 18:
        return "cold"
    if temperature_c is not None and 22 <= temperature_c <= 29:
        return "pleasant"
    if _contains_any(description, CLEAR_KEYWORDS):
        return "pleasant"
    if _contains_any(description, CLOUDY_KEYWORDS):
        return "cloudy"
    return "unknown"


def build_weather_context(snapshot: dict[str, Any], fallback_location: str) -> WeatherContext:
    if not bool(snapshot.get("ok")):
        return WeatherContext("unknown", None, fallback_location, "unknown weather", None)

    location_text = str(snapshot.get("location_text") or fallback_location)
    description = str(snapshot.get("description") or "unknown weather")
    raw_temp = snapshot.get("temp")
    temperature_c = _parse_temperature(raw_temp)
    temp_text = str(raw_temp if raw_temp is not None else "unknown")
    return WeatherContext(
        mood=_resolve_weather_mood(description, temperature_c),
        summary=f"Current weather in {location_text}: {description}, {temp_text} C.",
        location_text=location_text,
        description=description,
        temperature_c=temperature_c,
    )
