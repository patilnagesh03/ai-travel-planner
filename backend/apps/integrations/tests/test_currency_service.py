"""
Unit tests for the currency service.

The provider client is a double, so no test depends on the network.
"""

from unittest.mock import Mock

from django.test import SimpleTestCase

from backend.apps.integrations.exceptions import (
    IntegrationResponseError,
    UnsupportedCurrencyError,
)
from backend.apps.integrations.services import CurrencyService
from backend.apps.integrations.tests.helpers import CacheClearingMixin


SAMPLE_PAYLOAD = {
    "amount": 1.0,
    "base": "INR",
    "date": "2026-10-29",
    "rates": {"USD": 0.0113, "EUR": 0.0094},
}


def build_client(payload=None):
    client = Mock()
    client.fetch_latest.return_value = payload or SAMPLE_PAYLOAD

    return client


class CurrencyServiceTests(CacheClearingMixin, SimpleTestCase):

    def test_rates_are_normalized_for_the_api(self):
        result = CurrencyService.get_rates(
            base="INR",
            symbols=["USD", "EUR"],
            client=build_client(),
        )

        self.assertEqual(result["base"], "INR")
        self.assertEqual(result["date"], "2026-10-29")
        self.assertEqual(result["rates"], {"USD": 0.0113, "EUR": 0.0094})
        self.assertIn("Frankfurter", result["attribution"])

    def test_codes_are_upper_cased_and_de_duplicated(self):
        client = build_client(
            {
                "base": "INR",
                "date": "2026-10-29",
                "rates": {"USD": 0.0113},
            },
        )

        result = CurrencyService.get_rates(
            base="inr",
            symbols=["usd", "USD", " usd "],
            client=client,
        )

        self.assertEqual(result["base"], "INR")
        self.assertEqual(result["rates"], {"USD": 0.0113})

        self.assertEqual(
            client.fetch_latest.call_args.kwargs,
            {"base": "INR", "symbols": ["USD"]},
        )

    def test_the_provider_payload_is_cached(self):
        client = build_client()

        CurrencyService.get_rates("INR", ["USD"], client=client)
        CurrencyService.get_rates("INR", ["USD"], client=client)

        self.assertEqual(client.fetch_latest.call_count, 1)

    def test_the_cache_key_ignores_symbol_order(self):
        client = build_client()

        CurrencyService.get_rates("INR", ["USD", "EUR"], client=client)
        CurrencyService.get_rates("INR", ["EUR", "USD"], client=client)

        self.assertEqual(client.fetch_latest.call_count, 1)

    def test_the_base_cannot_also_be_a_target(self):
        with self.assertRaises(UnsupportedCurrencyError):
            CurrencyService.get_rates(
                "INR",
                ["INR", "USD"],
                client=build_client(),
            )

    def test_an_invalid_code_is_rejected_before_the_provider_is_called(self):
        client = build_client()

        with self.assertRaises(UnsupportedCurrencyError):
            CurrencyService.get_rates("INR", ["US"], client=client)

        client.fetch_latest.assert_not_called()

    def test_an_empty_symbol_list_is_rejected(self):
        with self.assertRaises(UnsupportedCurrencyError):
            CurrencyService.get_rates("INR", [], client=build_client())

    def test_too_many_symbols_are_rejected(self):
        symbols = [
            "USD",
            "EUR",
            "GBP",
            "AED",
            "SGD",
            "AUD",
            "CAD",
            "CHF",
            "JPY",
            "THB",
            "MYR",
            "LKR",
            "NPR",
        ]

        with self.assertRaises(UnsupportedCurrencyError):
            CurrencyService.get_rates(
                "INR",
                symbols,
                client=build_client(),
            )

    def test_a_rate_the_provider_omits_is_reported_as_unsupported(self):
        # Frankfurter answers 200 with only the symbols it publishes when a
        # request mixes known and unknown codes.
        client = build_client(
            {
                "base": "INR",
                "date": "2026-10-29",
                "rates": {"USD": 0.0113},
            },
        )

        with self.assertRaises(UnsupportedCurrencyError) as raised:
            CurrencyService.get_rates("INR", ["USD", "EUR"], client=client)

        self.assertIn("EUR", str(raised.exception))

    def test_a_payload_with_none_of_the_requested_rates_is_a_provider_error(
        self,
    ):
        client = build_client(
            {
                "base": "INR",
                "date": "2026-10-29",
                "rates": {"GBP": 0.0078},
            },
        )

        with self.assertRaises(IntegrationResponseError):
            CurrencyService.get_rates("INR", ["USD"], client=client)

    def test_a_non_numeric_rate_is_a_provider_error(self):
        client = build_client(
            {
                "base": "INR",
                "date": "2026-10-29",
                "rates": {"USD": "not-a-number"},
            },
        )

        with self.assertRaises(IntegrationResponseError):
            CurrencyService.get_rates("INR", ["USD"], client=client)

    def test_a_missing_provider_date_stays_null(self):
        client = build_client({"base": "INR", "rates": {"USD": 0.0113}})

        result = CurrencyService.get_rates(
            "INR",
            ["USD"],
            client=client,
        )

        self.assertIsNone(result["date"])
