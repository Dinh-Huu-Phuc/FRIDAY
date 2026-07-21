"""
Weather search helper powered by OpenWeatherMap.
"""

from __future__ import annotations

import asyncio
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .city_name import resolve_vietnam_city

_ENV_PATH = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _get_api_key() -> str:
    return (
        os.getenv("WEATHERMAP_API_KEY", "").strip()
        or os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
    )


def _normalize_text(value: str) -> str:
    return (value or "").strip().casefold()


def _is_vietnam_country(country: str) -> bool:
    normalized = _normalize_text(country)
    return normalized in {"", "vn", "vietnam", "viet nam"}


def _pick_best_location(results: list[dict[str, Any]], city: str, country: str) -> dict[str, Any]:
    if not results:
        return {}

    wanted_city = _normalize_text(city)
    wanted_country = _normalize_text(country)

    def score(item: dict[str, Any]) -> tuple[int, int]:
        name = _normalize_text(str(item.get("name", "")))
        state = _normalize_text(str(item.get("state", "")))
        country_code = _normalize_text(str(item.get("country", "")))
        local_names = item.get("local_names") or {}
        aliases = [_normalize_text(str(value)) for value in local_names.values()]

        city_score = 0
        if wanted_city and (name == wanted_city or wanted_city in aliases):
            city_score = 3
        elif wanted_city and wanted_city in name:
            city_score = 2

        country_score = 0
        if not wanted_country:
            country_score = 1
        elif wanted_country in {state, country_code}:
            country_score = 3
        elif wanted_country and wanted_country in " ".join([state, country_code] + aliases):
            country_score = 2

        return (city_score, country_score)

    return max(results, key=score)


def _format_location(place: dict[str, Any], fallback_city: str, fallback_country: str) -> str:
    parts = [place.get("name") or fallback_city]
    state = place.get("state")
    country = place.get("country") or fallback_country

    if state:
        parts.append(state)
    if country:
        parts.append(country)

    return ", ".join(str(part).strip() for part in parts if str(part).strip())


def _format_number(value: Any, digits: int = 1) -> str:
    if value is None:
        return "unknown"
    number = round(float(value), digits)
    if digits == 0 or number.is_integer():
        return str(int(number))
    return f"{number:.{digits}f}"


def _to_local_time(unix_ts: int, timezone_offset_seconds: int) -> str:
    tz = timezone(timedelta(seconds=timezone_offset_seconds))
    return datetime.fromtimestamp(unix_ts, tz=tz).strftime("%H:%M")


def _build_forecast_summary(forecast_items: list[dict[str, Any]], timezone_offset_seconds: int) -> str:
    if not forecast_items:
        return "Short-term forecast data is unavailable."

    snippets: list[str] = []
    for item in forecast_items[:3]:
        weather = (item.get("weather") or [{}])[0]
        main = item.get("main") or {}
        pop = item.get("pop")
        rain_text = ""
        if pop is not None and float(pop) >= 0.2:
            rain_text = f", {round(float(pop) * 100)}% chance of rain"

        snippets.append(
            f"{_to_local_time(int(item.get('dt', 0)), timezone_offset_seconds)}: "
            f"{weather.get('description', 'unknown weather')}, "
            f"{_format_number(main.get('temp'))} C{rain_text}"
        )

    return "; ".join(snippets)


def _build_daily_forecast(
    forecast_items: list[dict[str, Any]],
    timezone_offset_seconds: int,
    days_ahead: int,
) -> dict[str, str]:
    local_timezone = timezone(timedelta(seconds=timezone_offset_seconds))
    target_date = datetime.now(timezone.utc).astimezone(local_timezone).date() + timedelta(days=days_ahead)
    daily_items = [
        item
        for item in forecast_items
        if datetime.fromtimestamp(int(item.get("dt", 0)), tz=local_timezone).date() == target_date
    ]
    if not daily_items:
        return {}

    temperatures = [
        float((item.get("main") or {}).get("temp"))
        for item in daily_items
        if (item.get("main") or {}).get("temp") is not None
    ]
    descriptions = [
        str((item.get("weather") or [{}])[0].get("description") or "unknown weather")
        for item in daily_items
    ]
    rain_chance = max(float(item.get("pop") or 0) for item in daily_items)
    wind_kmh = max(float((item.get("wind") or {}).get("speed") or 0) * 3.6 for item in daily_items)
    common_description = Counter(descriptions).most_common(1)[0][0]

    return {
        "date": target_date.isoformat(),
        "description": common_description,
        "temp_min": _format_number(min(temperatures)) if temperatures else "unknown",
        "temp_max": _format_number(max(temperatures)) if temperatures else "unknown",
        "rain_chance": str(round(rain_chance * 100)),
        "wind_kmh": _format_number(wind_kmh),
    }


def _format_weather_error(exc: Exception) -> str:
    message = " ".join(str(part).strip() for part in exc.args if str(part).strip()) or str(exc).strip()
    lower = message.lower()

    if "401" in lower or "403" in lower or "invalid api key" in lower:
        return "Weather is unavailable because WEATHERMAP_API_KEY is invalid or lacks permission."

    if "timed out" in lower or "timeout" in lower:
        return "The weather service connection timed out."

    if (
        "10013" in lower
        or "forbidden by its access permissions" in lower
        or ("socket" in lower and "forbidden" in lower)
    ):
        return "Weather is unavailable because outbound network access is blocked."

    if (
        "getaddrinfo failed" in lower
        or "temporary failure in name resolution" in lower
        or "name or service not known" in lower
    ):
        return "Weather is unavailable because DNS resolution or internet access failed."

    return f"Weather data is unavailable right now: {message}"


async def get_weather_snapshot(
    city: str,
    country: str = "Vietnam",
    forecast_days_ahead: int = 0,
) -> dict[str, Any]:
    """Fetch structured current weather and short-term forecast data."""
    city = (city or "").strip()
    country = (country or "").strip()
    if not city:
        return {
            "ok": False,
            "location_text": "",
            "message": "No city was provided for the weather lookup.",
        }

    api_key = _get_api_key()
    if not api_key:
        return {
            "ok": False,
            "location_text": f"{city}, {country}" if country else city,
            "message": "WEATHERMAP_API_KEY is missing from .env, so weather is unavailable.",
        }

    query = city if not country else f"{city},{country}"
    place: dict[str, Any] | None = None
    lat = None
    lon = None

    if _is_vietnam_country(country):
        local_city = resolve_vietnam_city(city)
        if local_city:
            place = {
                "name": local_city.get("display_name") or local_city.get("name") or city,
                "state": local_city.get("state") or "",
                "country": local_city.get("country") or "VN",
            }
            lat = local_city.get("lat")
            lon = local_city.get("lon")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            if lat is None or lon is None:
                geo_response = await client.get(
                    GEOCODE_URL,
                    params={"q": query, "limit": 5, "appid": api_key},
                )
                geo_response.raise_for_status()
                geo_results = geo_response.json() or []

                if not geo_results and country:
                    geo_response = await client.get(
                        GEOCODE_URL,
                        params={"q": city, "limit": 5, "appid": api_key},
                    )
                    geo_response.raise_for_status()
                    geo_results = geo_response.json() or []

                if not geo_results:
                    return {
                        "ok": False,
                        "location_text": f"{city}, {country}" if country else city,
                        "message": f"I could not find '{city}' for the weather lookup.",
                    }

                geocoded_place = _pick_best_location(geo_results, city=city, country=country)
                lat = geocoded_place.get("lat")
                lon = geocoded_place.get("lon")
                if lat is None or lon is None:
                    return {
                        "ok": False,
                        "location_text": _format_location(
                            geocoded_place,
                            fallback_city=city,
                            fallback_country=country,
                        ),
                        "message": f"I found '{city}', but its coordinates are unavailable.",
                    }

                place = geocoded_place

            current_task = client.get(
                CURRENT_WEATHER_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": api_key,
                    "units": "metric",
                    "lang": "en",
                },
            )
            forecast_task = client.get(
                FORECAST_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": api_key,
                    "units": "metric",
                    "lang": "en",
                    "cnt": 16 if forecast_days_ahead else 3,
                },
            )
            current_response, forecast_response = await asyncio.gather(current_task, forecast_task)
            current_response.raise_for_status()
            forecast_response.raise_for_status()
    except Exception as exc:
        return {
            "ok": False,
            "location_text": _format_location(place or {}, fallback_city=city, fallback_country=country),
            "message": _format_weather_error(exc),
        }

    current_data = current_response.json() or {}
    forecast_data = forecast_response.json() or {}

    current_main = current_data.get("main") or {}
    current_weather = (current_data.get("weather") or [{}])[0]
    current_wind = current_data.get("wind") or {}
    current_system = current_data.get("sys") or {}
    location_text = _format_location(place or {}, fallback_city=city, fallback_country=country)
    timezone_offset = int(current_data.get("timezone") or forecast_data.get("city", {}).get("timezone") or 0)

    temp = _format_number(current_main.get("temp"))
    feels_like = _format_number(current_main.get("feels_like"))
    humidity = _format_number(current_main.get("humidity"), digits=0)
    wind_kmh = _format_number(float(current_wind.get("speed", 0)) * 3.6)
    description = current_weather.get("description", "unknown weather")
    sunrise_unix = int(current_system.get("sunrise") or 0)
    sunset_unix = int(current_system.get("sunset") or 0)
    forecast_items = forecast_data.get("list") or []
    forecast_summary = _build_forecast_summary(forecast_items, timezone_offset)
    daily_forecast = (
        _build_daily_forecast(forecast_items, timezone_offset, forecast_days_ahead)
        if forecast_days_ahead
        else {}
    )

    if forecast_days_ahead:
        if not daily_forecast:
            return {
                "ok": False,
                "location_text": location_text,
                "message": f"Forecast data for the requested day is unavailable for {location_text}.",
            }
        return {
            "ok": True,
            "location_text": location_text,
            "forecast_days_ahead": forecast_days_ahead,
            "daily_forecast": daily_forecast,
            "message": (
                f"Tomorrow's forecast for {location_text}: {daily_forecast['description']}, "
                f"{daily_forecast['temp_min']} to {daily_forecast['temp_max']} C, "
                f"rain chance up to {daily_forecast['rain_chance']}%, and wind around "
                f"{daily_forecast['wind_kmh']} km/h."
            ),
        }

    return {
        "ok": True,
        "location_text": location_text,
        "description": description,
        "temp": temp,
        "feels_like": feels_like,
        "humidity": humidity,
        "wind_kmh": wind_kmh,
        "timezone_offset": timezone_offset,
        "sunrise_unix": sunrise_unix,
        "sunset_unix": sunset_unix,
        "sunrise": _to_local_time(sunrise_unix, timezone_offset) if sunrise_unix else "--:--",
        "sunset": _to_local_time(sunset_unix, timezone_offset) if sunset_unix else "--:--",
        "forecast_summary": forecast_summary,
        "message": (
            f"Current weather in {location_text}: {description}, {temp} C, "
            f"feels like {feels_like} C, humidity {humidity}%, and wind around {wind_kmh} km/h. "
            f"Forecast for the next nine hours: {forecast_summary}."
        ),
    }


async def get_weather_report(city: str, country: str = "Vietnam") -> str:
    """
    Fetch current weather and short-term forecast using OpenWeatherMap.
    """
    snapshot = await get_weather_snapshot(city=city, country=country)
    return str(snapshot.get("message") or "").strip()
