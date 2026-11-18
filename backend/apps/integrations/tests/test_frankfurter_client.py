"""
Unit tests for the Frankfurter currency client.

Every test mocks ``requests.get``. The provider is never called.
"""

from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from backend.apps.integrations.clients import FrankfurterClient
from backend.apps.integrations.exceptions import (
    IntegrationError,
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    UnsupportedCurrencyError,
)


GET_TARGET = (
    "backend.apps.integrations.clients.frankfurter_client.requests.get"
)


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


SAMPLE_PAYLOAD = {
    "amount": 1.0,
    "base": "INR",
    "date": "2026-10-29",
    "rates": {"USD": 0.0113, "EUR": 0.0094},
}


class FrankfurterClientTests(SimpleTestCase):

    def test_requests_latest_rates_for_the_requested_symbols(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_get:
            FrankfurterClient().fetch_latest(
                base="INR",
                symbols=["USD", "EUR"],
            )

        url = mocked_get.call_args.args[0]

        self.assertEqual(url, "https://api.frankfurter.dev/v1/latest")

        params = mocked_get.call_args.kwargs["params"]

        self.assertEqual(params["base"], "INR")
        self.assertEqual(params["symbols"], "USD,EUR")

    def test_a_trailing_slash_in_the_configured_url_is_tolerated(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_get:
            FrankfurterClient(
                api_url="https://example.test/v1/",
            ).fetch_latest(base="INR", symbols=["USD"])

        self.assertEqual(
            mocked_get.call_args.args[0],
            "https://example.test/v1/latest",
        )

    def test_returns_the_provider_payload(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ):
            result = FrankfurterClient().fetch_latest(
                base="INR",
                symbols=["USD"],
            )

        self.assertEqual(result, SAMPLE_PAYLOAD)

    def test_an_unknown_currency_is_not_reported_as_an_outage(self):
        for status_code in (404, 422):
            with self.subTest(status_code=status_code):
                with patch(
                    GET_TARGET,
                    return_value=build_response(status_code=status_code),
                ):
                    with self.assertRaises(UnsupportedCurrencyError):
                        FrankfurterClient().fetch_latest(
                            base="INR",
                            symbols=["XYZ"],
                        )

    def test_timeout_raises_a_timeout_error(self):
        with patch(GET_TARGET, side_effect=requests.exceptions.Timeout):
            with self.assertRaises(IntegrationTimeoutError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_connection_error_raises_an_unavailable_error(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.ConnectionError,
        ):
            with self.assertRaises(IntegrationUnavailableError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_unexpected_request_error_raises_the_base_error(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.TooManyRedirects,
        ):
            with self.assertRaises(IntegrationError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_rate_limit_captures_retry_after(self):
        with patch(
            GET_TARGET,
            return_value=build_response(
                status_code=429,
                headers={"Retry-After": "15"},
            ),
        ):
            with self.assertRaises(IntegrationRateLimitError) as raised:
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

        self.assertEqual(raised.exception.retry_after, 15)

    def test_temporary_status_is_reported_as_unavailable(self):
        with patch(
            GET_TARGET,
            return_value=build_response(status_code=503),
        ):
            with self.assertRaises(IntegrationUnavailableError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_other_client_error_is_reported_as_a_rejected_request(self):
        with patch(
            GET_TARGET,
            return_value=build_response(status_code=400),
        ):
            with self.assertRaises(IntegrationRequestError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_invalid_json_is_reported_as_an_unreadable_response(self):
        response = build_response()
        response.json.side_effect = ValueError("not json")

        with patch(GET_TARGET, return_value=response):
            with self.assertRaises(IntegrationResponseError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_a_payload_without_rates_is_rejected(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload={"base": "INR"}),
        ):
            with self.assertRaises(IntegrationResponseError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )

    def test_empty_rates_are_rejected(self):
        payload = {"base": "INR", "date": "2026-10-29", "rates": {}}

        with patch(
            GET_TARGET,
            return_value=build_response(payload=payload),
        ):
            with self.assertRaises(IntegrationResponseError):
                FrankfurterClient().fetch_latest(
                    base="INR",
                    symbols=["USD"],
                )
