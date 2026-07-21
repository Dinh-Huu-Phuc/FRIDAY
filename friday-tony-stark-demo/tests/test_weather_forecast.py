from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from friday.search.weather.weather import _build_daily_forecast
from friday.src.services.agent.service import _extract_weather_location


class WeatherForecastTests(unittest.TestCase):
    def test_tomorrow_is_not_part_of_location(self) -> None:
        city, display = _extract_weather_location("will there be heavy rain in Dallas tomorrow")
        self.assertEqual(city, "dallas")
        self.assertEqual(display, "Dallas")

    def test_weather_description_is_not_part_of_vietnam_location(self) -> None:
        city, display = _extract_weather_location("Will there be heavy rain in Da Lat tomorrow?")
        self.assertEqual(city, "Da Lat")
        self.assertEqual(display, "Da Lat")

    def test_vietnam_location_still_resolves(self) -> None:
        city, display = _extract_weather_location("weather in Da Lat tomorrow")
        self.assertTrue(city)
        self.assertEqual(display, "Da Lat")

    def test_daily_forecast_aggregates_tomorrow(self) -> None:
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        items = []
        for hour, temp, rain in ((3, 24.5, 0.4), (12, 33.8, 1.0), (21, 28.0, 0.7)):
            timestamp = int(datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            items.append({
                "dt": timestamp + hour * 3600,
                "main": {"temp": temp},
                "weather": [{"description": "light rain"}],
                "pop": rain,
                "wind": {"speed": 3.0},
            })

        forecast = _build_daily_forecast(items, timezone_offset_seconds=0, days_ahead=1)
        self.assertEqual(forecast["temp_min"], "24.5")
        self.assertEqual(forecast["temp_max"], "33.8")
        self.assertEqual(forecast["rain_chance"], "100")


if __name__ == "__main__":
    unittest.main()
