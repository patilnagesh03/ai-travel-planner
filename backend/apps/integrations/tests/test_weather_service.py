"""
Unit tests for the weather service.

The provider client is a double, so no test depends on the network. The
"today" value is injected, so no test depends on the clock either.
"""

from datetime import date, timedelta
from unittest.mock import Mock

from django.test import SimpleTestCase

from backend.apps.integrations.exceptions import (
    IntegrationResponseError,
    UnsupportedDestinationError,
)
from backend.apps.integrations.services import WeatherService
from backend.apps.integrations.tests.helpers import CacheClearingMixin
from backend.apps.trips.models import Trip


TODAY = date(2026, 10, 30)


def build_payload(start=TODAY, days=16):
    dates = [
        (start + timedelta(days=index)).isoformat()
        for index in range(days)
    ]

    return {
        "latitude": 26.915,
        "longitude": 75.795,
        "timezone": "Asia/Kolkata",
        "daily": {
            "time": dates,
            "weather_code": [0 + index for index in range(days)],
            "temperature_2m_max": [
                30.0 + index for index in range(days)
            ],
            "temperature_2m_min": [
                18.0 + index for index in range(days)
            ],
            "precipitation_probability_max": [
                index for index in range(days)
            ],
            "wind_speed_10m_max": [
                10.0 + index for index in range(days)
            ],
            "sunrise": [
                "{date}T06:24".format(date=value)
                for value in dates
            ],
            "sunset": [
                "{date}T17:52".format(date=value)
                for value in dates
            ],
        },
    }


def build_client(payload=None):
    client = Mock()
    client.fetch_daily_forecast.return_value = payload or build_payload()

    return client


def build_trip(start_date, end_date, destination="Jaipur"):
    return Trip(
        title="Test trip",
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        budget=50000,
    )


class WeatherForecastTests(CacheClearingMixin, SimpleTestCase):

    def test_forecast_for_a_trip_resolves_the_destination(self):
        trip = build_trip(
            start_date=date(2026, 10, 31),
            end_date=date(2026, 11, 2),
        )

        client = build_client()

        result = WeatherService.forecast_for_trip(
            trip,
            client=client,
            today=TODAY,
        )

        self.assertEqual(result["destination"]["name"], "Jaipur")
        self.assertEqual(result["destination"]["state"], "Rajasthan")
        self.assertAlmostEqual(
            result["destination"]["latitude"],
            26.915,
            places=3,
        )

        kwargs = client.fetch_daily_forecast.call_args.kwargs

        self.assertAlmostEqual(kwargs["latitude"], 26.915, places=3)
        self.assertAlmostEqual(kwargs["longitude"], 75.795, places=3)

    def test_only_the_trip_dates_inside_the_window_are_returned(self):
        trip = build_trip(
            start_date=date(2026, 10, 31),
            end_date=date(2026, 11, 2),
        )

        result = WeatherService.forecast_for_trip(
            trip,
            client=build_client(),
            today=TODAY,
        )

        self.assertEqual(result["covered_days"], 3)
        self.assertEqual(result["trip_days"], 3)

        self.assertEqual(
            [day["date"] for day in result["days"]],
            ["2026-10-31", "2026-11-01", "2026-11-02"],
        )

        first_day = result["days"][0]

        self.assertEqual(first_day["condition"], "Mainly clear")
        self.assertEqual(first_day["temperature_max"], 31.0)
        self.assertEqual(first_day["precipitation_probability"], 1)
        self.assertEqual(first_day["sunrise"], "2026-10-31T06:24")

    def test_a_trip_that_already_started_only_shows_the_remaining_days(self):
        trip = build_trip(
            start_date=date(2026, 10, 28),
            end_date=date(2026, 10, 31),
        )

        result = WeatherService.forecast_for_trip(
            trip,
            client=build_client(),
            today=TODAY,
        )

        self.assertEqual(
            [day["date"] for day in result["days"]],
            ["2026-10-30", "2026-10-31"],
        )

        self.assertIn("Past days", result["note"])

    def test_a_trip_beyond_the_window_has_no_days_but_a_clear_note(self):
        trip = build_trip(
            start_date=date(2026, 12, 20),
            end_date=date(2026, 12, 27),
        )

        result = WeatherService.forecast_for_trip(
            trip,
            client=build_client(),
            today=TODAY,
        )

        self.assertEqual(result["days"], [])
        self.assertEqual(result["covered_days"], 0)
        self.assertIn("outside the 16-day forecast window", result["note"])

    def test_a_trip_longer_than_the_window_says_where_coverage_stops(self):
        trip = build_trip(
            start_date=date(2026, 10, 30),
            end_date=date(2026, 11, 30),
        )

        result = WeatherService.forecast_for_trip(
            trip,
            client=build_client(),
            today=TODAY,
        )

        self.assertEqual(result["covered_days"], 16)
        self.assertIn("covers up to 14 Nov 2026", result["note"])

    def test_an_unsupported_destination_is_rejected(self):
        trip = build_trip(
            start_date=date(2026, 10, 31),
            end_date=date(2026, 11, 2),
            destination="Kumbakonam",
        )

        with self.assertRaises(UnsupportedDestinationError) as raised:
            WeatherService.forecast_for_trip(
                trip,
                client=build_client(),
                today=TODAY,
            )

        self.assertIn("Kumbakonam", str(raised.exception))

    def test_the_provider_payload_is_cached(self):
        trip = build_trip(
            start_date=date(2026, 10, 31),
            end_date=date(2026, 11, 2),
        )

        client = build_client()

        WeatherService.forecast_for_trip(trip, client=client, today=TODAY)
        WeatherService.forecast_for_trip(trip, client=client, today=TODAY)

        self.assertEqual(client.fetch_daily_forecast.call_count, 1)

    def test_a_payload_with_no_usable_days_is_a_provider_error(self):
        payload = build_payload()

        payload["daily"]["time"] = ["not-a-date"]

        client = build_client(payload)

        with self.assertRaises(IntegrationResponseError):
            WeatherService.forecast(
                latitude=26.9,
                longitude=75.8,
                start_date=date(2026, 10, 31),
                end_date=date(2026, 11, 2),
                client=client,
                today=TODAY,
            )

    def test_unknown_weather_codes_get_a_safe_label(self):
        payload = build_payload(days=1)

        payload["daily"]["weather_code"] = [12345]

        client = build_client(payload)

        result = WeatherService.forecast(
            latitude=26.9,
            longitude=75.8,
            start_date=TODAY,
            end_date=TODAY,
            client=client,
            today=TODAY,
        )

        self.assertEqual(
            result["days"][0]["condition"],
            "Unknown conditions",
        )

    def test_missing_values_stay_null_rather_than_becoming_zero(self):
        payload = build_payload(days=1)

        payload["daily"]["temperature_2m_max"] = [None]
        payload["daily"]["precipitation_probability_max"] = [None]

        client = build_client(payload)

        result = WeatherService.forecast(
            latitude=26.9,
            longitude=75.8,
            start_date=TODAY,
            end_date=TODAY,
            client=client,
            today=TODAY,
        )

        day = result["days"][0]

        self.assertIsNone(day["temperature_max"])
        self.assertIsNone(day["precipitation_probability"])

    def test_reversed_dates_are_a_programming_error(self):
        with self.assertRaises(ValueError):
            WeatherService.forecast(
                latitude=26.9,
                longitude=75.8,
                start_date=date(2026, 11, 2),
                end_date=date(2026, 10, 31),
                client=build_client(),
                today=TODAY,
            )

    def test_the_response_carries_units_and_attribution(self):
        trip = build_trip(
            start_date=date(2026, 10, 31),
            end_date=date(2026, 11, 2),
        )

        result = WeatherService.forecast_for_trip(
            trip,
            client=build_client(),
            today=TODAY,
        )

        self.assertEqual(result["units"]["temperature"], "°C")
        self.assertIn("Open-Meteo", result["attribution"])
