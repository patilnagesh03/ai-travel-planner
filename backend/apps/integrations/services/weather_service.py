"""
Application-level service for daily weather forecasts.

The provider returns a fixed 16-day window starting today. A trip,
however, has its own dates: it may be in the past, far in the future, or
longer than the forecast window. This service reconciles the two and says
plainly which days it could and could not cover, instead of pretending
that a three-week trip has weather for every day.

Only the days that overlap both the trip and the forecast window are
returned. Nothing is persisted: a forecast has no value after the fact.
"""

import logging
from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone

from backend.apps.integrations.clients import OpenMeteoClient
from backend.apps.integrations.config import (
    WEATHER_CACHE_TIMEOUT,
    WEATHER_FORECAST_DAYS,
)
from backend.apps.integrations.data import INDIA_CITIES
from backend.apps.integrations.exceptions import (
    IntegrationResponseError,
    UnsupportedDestinationError,
)
from backend.apps.integrations.services.destination_service import (
    DestinationService,
)


logger = logging.getLogger(__name__)


# WMO weather interpretation codes, as documented by Open-Meteo.
# The frontend never sees this table; it receives a ready-made label.
WMO_CONDITIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

UNKNOWN_CONDITION = "Unknown conditions"

# The provider's published maximum. A configured value above this is
# clamped rather than rejected, so a typo in `.env` cannot break the API.
PROVIDER_MAX_FORECAST_DAYS = 16

UNITS = {
    "temperature": "°C",
    "wind_speed": "km/h",
    "precipitation_probability": "%",
}

ATTRIBUTION = "Weather data by Open-Meteo.com"


class WeatherService:

    @staticmethod
    def forecast_for_trip(trip, client=None, today=None):
        """Return the forecast for a trip's destination and dates."""

        city = DestinationService.find_city(trip.destination)

        if city is None:
            raise UnsupportedDestinationError(
                "'{value}' is not a destination we can forecast. We "
                "currently support {count} curated Indian cities.".format(
                    value=str(trip.destination).strip(),
                    count=len(INDIA_CITIES),
                )
            )

        latitude, longitude = city.center

        return WeatherService.forecast(
            latitude=latitude,
            longitude=longitude,
            start_date=trip.start_date,
            end_date=trip.end_date,
            destination={
                "name": city.name,
                "state": city.state,
                "latitude": latitude,
                "longitude": longitude,
            },
            client=client,
            today=today,
        )

    @staticmethod
    def forecast(
        latitude,
        longitude,
        start_date,
        end_date,
        destination=None,
        client=None,
        today=None,
    ):
        """Return the forecast for an area, filtered to a date range.

        ``today`` is injectable so the tests do not depend on the clock.
        """

        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise ValueError("start_date and end_date must be dates.")

        if start_date > end_date:
            raise ValueError("start_date must not be after end_date.")

        today = today or timezone.localdate()

        forecast_days = WeatherService._resolve_forecast_days()

        window_end = today + timedelta(days=forecast_days - 1)

        covered_start = max(start_date, today)
        covered_end = min(end_date, window_end)

        payload = WeatherService._load_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            client=client,
        )

        days = [
            day
            for day in payload["days"]
            if covered_start <= date.fromisoformat(day["date"]) <= covered_end
        ]

        trip_days = (end_date - start_date).days + 1

        return {
            "destination": destination or {
                "name": None,
                "state": None,
                "latitude": latitude,
                "longitude": longitude,
            },
            "timezone": payload["timezone"],
            "units": dict(UNITS),
            "forecast_window": {
                "starts_on": today.isoformat(),
                "ends_on": window_end.isoformat(),
            },
            "trip_days": trip_days,
            "covered_days": len(days),
            "days": days,
            "note": WeatherService._build_note(
                start_date=start_date,
                end_date=end_date,
                today=today,
                window_end=window_end,
                covered_days=len(days),
                forecast_days=forecast_days,
            ),
            "attribution": ATTRIBUTION,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _load_forecast(latitude, longitude, forecast_days, client=None):
        """Return ``{"timezone": ..., "days": [...]}``, cached when possible."""

        cache_key = WeatherService.cache_key(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
        )

        cached = WeatherService.read_cache(cache_key)

        if cached is not None:
            logger.info("Serving the daily forecast from cache.")

            return cached

        raw_payload = (client or OpenMeteoClient()).fetch_daily_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
        )

        payload = {
            "timezone": raw_payload.get("timezone"),
            "days": WeatherService.normalize_daily(raw_payload),
        }

        if not payload["days"]:
            # A payload with no usable days is a provider problem, not an
            # empty forecast: Open-Meteo always returns its full window.
            raise IntegrationResponseError(
                "The weather provider returned no usable forecast days."
            )

        WeatherService.write_cache(cache_key, payload)

        return payload

    @staticmethod
    def normalize_daily(payload):
        """Turn the provider's column-oriented payload into day objects."""

        daily = payload.get("daily") if isinstance(payload, dict) else None

        if not isinstance(daily, dict):
            raise IntegrationResponseError(
                "The weather provider returned an unexpected response."
            )

        times = daily.get("time")

        if not isinstance(times, list):
            raise IntegrationResponseError(
                "The weather provider returned an unexpected response."
            )

        days = []

        for index, raw_date in enumerate(times):
            if not isinstance(raw_date, str):
                continue

            try:
                date.fromisoformat(raw_date)
            except ValueError:
                # A malformed date is provider noise, not a reason to fail
                # the whole request.
                logger.warning(
                    "Skipping a forecast day with an invalid date (%r).",
                    raw_date,
                )
                continue

            weather_code = WeatherService._integer(
                WeatherService._column(daily, "weather_code", index),
            )

            days.append(
                {
                    "date": raw_date,
                    "weather_code": weather_code,
                    "condition": WMO_CONDITIONS.get(
                        weather_code,
                        UNKNOWN_CONDITION,
                    ),
                    "temperature_max": WeatherService._number(
                        WeatherService._column(
                            daily,
                            "temperature_2m_max",
                            index,
                        ),
                    ),
                    "temperature_min": WeatherService._number(
                        WeatherService._column(
                            daily,
                            "temperature_2m_min",
                            index,
                        ),
                    ),
                    "precipitation_probability": WeatherService._integer(
                        WeatherService._column(
                            daily,
                            "precipitation_probability_max",
                            index,
                        ),
                    ),
                    "wind_speed_max": WeatherService._number(
                        WeatherService._column(
                            daily,
                            "wind_speed_10m_max",
                            index,
                        ),
                    ),
                    "sunrise": WeatherService._text(
                        WeatherService._column(daily, "sunrise", index),
                    ),
                    "sunset": WeatherService._text(
                        WeatherService._column(daily, "sunset", index),
                    ),
                }
            )

        return days

    @staticmethod
    def _build_note(
        start_date,
        end_date,
        today,
        window_end,
        covered_days,
        forecast_days,
    ):
        """Explain any gap between the trip and what the provider covers."""

        if covered_days == 0:
            return (
                "This trip is outside the {days}-day forecast window. "
                "Weather will appear closer to the travel dates.".format(
                    days=forecast_days,
                )
            )

        notes = []

        if start_date < today:
            notes.append("Past days of this trip are not shown.")

        if end_date > window_end:
            notes.append(
                "The forecast currently covers up to {date}; later days "
                "will appear closer to the date.".format(
                    date=window_end.strftime("%d %b %Y"),
                )
            )

        return " ".join(notes) or None

    @staticmethod
    def cache_key(latitude, longitude, forecast_days):
        return "weather:v1:{latitude:.4f}:{longitude:.4f}:{days}".format(
            latitude=float(latitude),
            longitude=float(longitude),
            days=forecast_days,
        )

    @staticmethod
    def read_cache(cache_key):
        if WEATHER_CACHE_TIMEOUT <= 0:
            return None

        return cache.get(cache_key)

    @staticmethod
    def write_cache(cache_key, payload):
        if WEATHER_CACHE_TIMEOUT <= 0:
            return

        cache.set(
            cache_key,
            payload,
            timeout=WEATHER_CACHE_TIMEOUT,
        )

    @staticmethod
    def _resolve_forecast_days():
        days = int(WEATHER_FORECAST_DAYS)

        return max(1, min(days, PROVIDER_MAX_FORECAST_DAYS))

    @staticmethod
    def _column(daily, key, index):
        values = daily.get(key)

        if not isinstance(values, list) or index >= len(values):
            return None

        return values[index]

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            return None

        if not isinstance(value, (int, float)):
            return None

        return float(value)

    @staticmethod
    def _integer(value):
        number = WeatherService._number(value)

        if number is None:
            return None

        return int(number)

    @staticmethod
    def _text(value):
        if not isinstance(value, str) or not value.strip():
            return None

        return value


__all__ = [
    "WeatherService",
    "WMO_CONDITIONS",
    "UNKNOWN_CONDITION",
]
