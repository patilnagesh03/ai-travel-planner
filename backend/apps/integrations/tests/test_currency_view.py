"""
API tests for the currency rates endpoint.

The provider is mocked, so these tests never call Frankfurter.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.integrations.tests.helpers import CacheClearingMixin


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


class CurrencyRatesApiTests(CacheClearingMixin, APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="currency@example.com",
            password="TestPass123!",
            first_name="Currency",
            last_name="Tester",
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("currency-rates")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url, {"symbols": "USD"})

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_rates_are_returned_with_inr_as_the_default_base(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_get:
            response = self.client.get(
                self.url,
                {"symbols": "usd,eur"},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        data = response.data["data"]

        self.assertEqual(data["base"], "INR")
        self.assertEqual(data["date"], "2026-10-29")
        self.assertEqual(data["rates"], {"USD": 0.0113, "EUR": 0.0094})

        params = mocked_get.call_args.kwargs["params"]

        self.assertEqual(params["base"], "INR")
        self.assertEqual(params["symbols"], "USD,EUR")

    def test_an_explicit_base_is_used(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_get:
            self.client.get(
                self.url,
                {"base": "usd", "symbols": "INR"},
            )

        self.assertEqual(
            mocked_get.call_args.kwargs["params"]["base"],
            "USD",
        )

    def test_missing_symbols_are_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_an_empty_symbol_list_is_rejected(self):
        response = self.client.get(self.url, {"symbols": " , "})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_a_malformed_code_is_rejected_without_calling_the_provider(self):
        with patch(GET_TARGET) as mocked_get:
            response = self.client.get(
                self.url,
                {"symbols": "US"},
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("US", response.data["message"])

        mocked_get.assert_not_called()

    def test_the_base_cannot_be_requested_as_a_target(self):
        response = self.client.get(
            self.url,
            {"base": "INR", "symbols": "INR,USD"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("base currency", response.data["message"])

    def test_an_unsupported_currency_returns_a_clear_400(self):
        with patch(
            GET_TARGET,
            return_value=build_response(status_code=404),
        ):
            response = self.client.get(
                self.url,
                {"symbols": "XYZ"},
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("not supported", response.data["message"])

    def test_a_partially_unknown_symbol_list_returns_a_clear_400(self):
        # The provider returns 200 with only the symbols it publishes.
        partial_payload = {
            "amount": 1.0,
            "base": "INR",
            "date": "2026-10-29",
            "rates": {"USD": 0.0113},
        }

        with patch(
            GET_TARGET,
            return_value=build_response(payload=partial_payload),
        ):
            response = self.client.get(
                self.url,
                {"symbols": "USD,AED"},
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("AED", response.data["message"])

    def test_a_provider_outage_returns_503(self):
        with patch(
            GET_TARGET,
            return_value=build_response(status_code=503),
        ):
            response = self.client.get(self.url, {"symbols": "USD"})

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertIn("currency provider", response.data["message"])

    def test_a_rate_limited_provider_returns_429_and_retry_after(self):
        with patch(
            GET_TARGET,
            return_value=build_response(
                status_code=429,
                headers={"Retry-After": "20"},
            ),
        ):
            response = self.client.get(self.url, {"symbols": "USD"})

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.assertEqual(response["Retry-After"], "20")

    def test_an_unusable_provider_payload_returns_502(self):
        with patch(
            GET_TARGET,
            return_value=build_response(payload={"base": "INR"}),
        ):
            response = self.client.get(self.url, {"symbols": "USD"})

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )
        self.assertIn("currency provider", response.data["message"])
