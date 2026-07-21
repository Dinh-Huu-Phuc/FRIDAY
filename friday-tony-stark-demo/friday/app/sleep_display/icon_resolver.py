from __future__ import annotations

from datetime import datetime


DAY_ICON = "cloud-sun-solid-full.svg"
NIGHT_ICON = "moon-regular-full.svg"


def resolve_weather_icon(
    description: str,
    wind_kmh: float,
    *,
    now: datetime | None = None,
    sunrise: datetime | None = None,
    sunset: datetime | None = None,
) -> str:
    lowered = str(description or "").lower()
    current = now or datetime.now()
    daylight = _is_daylight(current, sunrise=sunrise, sunset=sunset)

    if any(token in lowered for token in ("thunder", "lightning", "storm")):
        return "cloud-bolt-solid-full.svg"
    if any(token in lowered for token in ("heavy rain", "shower", "downpour")):
        return "cloud-showers-heavy-solid-full.svg"
    if any(token in lowered for token in ("rain", "drizzle", "sleet", "snow")):
        return "cloud-sun-rain-solid-full.svg" if daylight else "cloud-moon-rain-solid-full.svg"
    if any(token in lowered for token in ("cloud", "overcast", "mist", "fog", "haze")):
        return "cloud-sun-solid-full.svg" if daylight else "cloud-moon-solid-full.svg"
    return DAY_ICON if daylight else NIGHT_ICON


def resolve_temperature_icon(temperature: float | str | None) -> str:
    try:
        value = float(temperature)
    except (TypeError, ValueError):
        return "temperature-half-solid-full.svg"
    if value <= 12:
        return "temperature-low-solid-full.svg"
    if value <= 20:
        return "temperature-quarter-solid-full.svg"
    if value <= 26:
        return "temperature-half-solid-full.svg"
    if value <= 31:
        return "temperature-three-quarters-solid-full.svg"
    return "temperature-high-solid-full.svg"


def _is_daylight(
    current: datetime,
    *,
    sunrise: datetime | None,
    sunset: datetime | None,
) -> bool:
    if sunrise is not None and sunset is not None:
        try:
            return sunrise <= current < sunset
        except TypeError:
            pass
    return 6 <= current.hour < 18
