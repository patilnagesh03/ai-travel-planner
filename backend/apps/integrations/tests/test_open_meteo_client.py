"""
Unit tests for the Open-Meteo client.

Every test mocks ``requests.get``, so the suite never touches the real
weather provider and never depends on network availability.
"""

from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from backend.apps.integrations.clients import OpenMeteoClient
from backend.apps.integrations.exceptions import (
    IntegrationError,
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


GET_TARGET = "backend.apps.integrations.clients.open_meteo_client.requests.get"


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


def build_payload(days=("2026-10-30", "2026-10-31")):
    return {
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone": "Asia/Kolkata",
        "daily": {
            "time": list(days),
            "weather_code": [3, 61],
            "temperature_2m_max": [31.2, 29.0],
            "temperature_2m_min": [18.4, 17.9],
            "precipitation_probability_max": [10, 70],
            "wind_speed_10m_max": [12.3, 20.1],
            "sunrise": [
                "2026-10-30T06:24",
                "2026-10-31T06:25",
            ],
            "sunset": [
                "2026-10-30T17:52",
                "2026-10-31T17:51",
            ],
        },
    }


class OpenMeteoClientTests(SimpleTestCase):

    def test_requests_the_expected_daily_fields(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=build_payload()),
        ) as mocked_get:
            OpenMeteoClient().fetch_daily_forecast(
                latitude=26.9124,
                longitude=75.7873,
                forecast_days=16,
            )

        params = mocked_get.call_args.kwargs["params"]

        self.assertEqual(params["latitude"], 26.9124)
        self.assertEqual(params["longitude"], 75.7873)
        self.assertEqual(params["forecast_days"], 16)
        self.assertEqual(params["timezone"], "auto")
        self.assertEqual(params["temperature_unit"], "celsius")
        self.assertEqual(params["wind_speed_unit"], "kmh")
        self.assertIn("weather_code", params["daily"])
        self.assertIn("precipitation_probability_max", params["daily"])

    def test_returns_the_provider_payload(self):
        payload = build_payload()

        with patch(
            GET_TARGET,
            return_value=build_response(payload=payload),
        ):
            result = OpenMeteoClient().fetch_daily_forecast(
                latitude=26.9124,
                longitude=75.7873,
                forecast_days=2,
            )

        self.assertEqual(result, payload)

    def test_timeout_raises_a_timeout_error(self):
        with patch(GET_TARGET, side_effect=requests.exceptions.Timeout):
            with self.assertRaises(IntegrationTimeoutError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_connection_error_raises_an_unavailable_error(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.ConnectionError,
        ):
            with self.assertRaises(IntegrationUnavailableError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_unexpected_request_error_raises_the_base_error(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.TooManyRedirects,
        ):
            with self.assertRaises(IntegrationError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_rate_limit_captures_retry_after(self):
        with patch(
            GET_TARGET,
            return_value=build_response(
                status_code=429,
                headers={"Retry-After": "30"},
            ),
        ):
            with self.assertRaises(IntegrationRateLimitError) as raised:
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

        self.assertEqual(raised.exception.retry_after, 30)

    def test_temporary_status_is_reported_as_unavailable(self):
        for status_code in (500, 502, 503, 504):
            with self.subTest(status_code=status_code):
                with patch(
                    GET_TARGET,
                    return_value=build_response(status_code=status_code),
                ):
                    with self.assertRaises(
                        IntegrationUnavailableError,
                    ):
                        OpenMeteoClient().fetch_daily_forecast(
                            latitude=1,
                            longitude=2,
                            forecast_days=3,
                        )

    def test_client_error_is_reported_as_a_rejected_request(self):
        with patch(
            GET_TARGET,
            return_value=build_response(status_code=400),
        ):
            with self.assertRaises(IntegrationRequestError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_invalid_json_is_reported_as_an_unreadable_response(self):
        response = build_response()
        response.json.side_effect = ValueError("not json")

        with patch(GET_TARGET, return_value=response):
            with self.assertRaises(IntegrationResponseError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_a_payload_without_a_daily_block_is_rejected(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload={"timezone": "UTC"}),
        ):
            with self.assertRaises(IntegrationResponseError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_a_daily_block_without_a_time_list_is_rejected(self):
        payload = build_payload()

        payload["daily"].pop("time")

        with patch(
            GET_TARGET,
            return_value=build_response(payload=payload),
        ):
            with self.assertRaises(IntegrationResponseError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )

    def test_a_non_object_payload_is_rejected(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=[1, 2, 3]),
        ):
            with self.assertRaises(IntegrationResponseError):
                OpenMeteoClient().fetch_daily_forecast(
                    latitude=1,
                    longitude=2,
                    forecast_days=3,
                )
