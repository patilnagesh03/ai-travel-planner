"""
Application-level service for exchange rates.

The provider speaks in three-letter ISO codes and returns one rate per
requested currency. This service validates the codes, de-duplicates them,
caches the result and normalizes the payload for the API.

Rates are reference rates, not a quote from a bank or a card network. The
API response says so through its attribution field, and the frontend
repeats that next to the numbers.
"""

import logging
import re

from django.core.cache import cache

from backend.apps.integrations.clients import FrankfurterClient
from backend.apps.integrations.config import (
    CURRENCY_CACHE_TIMEOUT,
    MAX_CURRENCY_SYMBOLS,
)
from backend.apps.integrations.exceptions import (
    IntegrationResponseError,
    UnsupportedCurrencyError,
)


logger = logging.getLogger(__name__)


CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")

DEFAULT_BASE_CURRENCY = "INR"

ATTRIBUTION = "Rates from the European Central Bank via Frankfurter"


class CurrencyService:

    @staticmethod
    def get_rates(base, symbols, client=None):
        """Return the latest rates for ``base`` against ``symbols``."""

        base = CurrencyService.normalize_code(base)

        requested = CurrencyService.normalize_symbols(symbols)

        if base in requested:
            raise UnsupportedCurrencyError(
                "The base currency cannot also be a target currency."
            )

        cache_key = CurrencyService.cache_key(base, requested)

        cached = CurrencyService.read_cache(cache_key)

        if cached is not None:
            logger.info(
                "Serving %s rate(s) for %s from cache.",
                len(cached["rates"]),
                base,
            )

            return cached

        payload = (client or FrankfurterClient()).fetch_latest(
            base=base,
            symbols=requested,
        )

        result = CurrencyService.normalize_payload(
            payload=payload,
            base=base,
            symbols=requested,
        )

        CurrencyService.write_cache(cache_key, result)

        return result

    @staticmethod
    def normalize_code(value):
        """Validate and upper-case one three-letter currency code."""

        if not isinstance(value, str):
            raise UnsupportedCurrencyError(
                "Currency codes must be three letters, for example INR "
                "or USD."
            )

        code = value.strip().upper()

        if not CURRENCY_CODE_PATTERN.match(code):
            raise UnsupportedCurrencyError(
                "'{value}' is not a valid currency code. Use a "
                "three-letter ISO code such as INR or USD.".format(
                    value=value,
                )
            )

        return code

    @staticmethod
    def normalize_symbols(symbols):
        """Validate, upper-case and de-duplicate the requested codes."""

        if not symbols:
            raise UnsupportedCurrencyError(
                "Provide at least one target currency."
            )

        if isinstance(symbols, str):
            symbols = [symbols]

        requested = []

        for value in symbols:
            code = CurrencyService.normalize_code(value)

            if code not in requested:
                requested.append(code)

        if len(requested) > MAX_CURRENCY_SYMBOLS:
            raise UnsupportedCurrencyError(
                "Ask for at most {maximum} currencies at a time.".format(
                    maximum=MAX_CURRENCY_SYMBOLS,
                )
            )

        return requested

    @staticmethod
    def normalize_payload(payload, base, symbols):
        """Turn the provider payload into the API's response shape.

        The provider answers 200 and silently omits symbols it does not
        publish when at least one requested symbol is known (it answers 404
        only when every symbol is unknown). A partial response therefore
        means "these currencies are not supported", not "the provider is
        broken", and is reported as caller input.
        """

        rates = payload.get("rates") if isinstance(payload, dict) else None

        if not isinstance(rates, dict):
            raise IntegrationResponseError(
                "The currency provider returned an unexpected response."
            )

        normalized_rates = {}

        missing = []

        for code in symbols:
            value = rates.get(code)

            if value is None:
                missing.append(code)

                continue

            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise IntegrationResponseError(
                    "The currency provider did not return a usable rate "
                    "for {code}.".format(code=code)
                )

            normalized_rates[code] = float(value)

        if missing:
            if len(missing) == len(symbols):
                raise IntegrationResponseError(
                    "The currency provider returned an unexpected response."
                )

            raise UnsupportedCurrencyError(
                "The rates provider does not publish {codes}. Try a "
                "different currency.".format(
                    codes=", ".join(missing),
                )
            )

        provider_date = payload.get("date")

        return {
            "base": base,
            "date": (
                provider_date
                if isinstance(provider_date, str)
                else None
            ),
            "rates": normalized_rates,
            "attribution": ATTRIBUTION,
        }

    @staticmethod
    def cache_key(base, symbols):
        return "currency:v1:{base}:{symbols}".format(
            base=base,
            symbols="-".join(sorted(symbols)),
        )

    @staticmethod
    def read_cache(cache_key):
        if CURRENCY_CACHE_TIMEOUT <= 0:
            return None

        return cache.get(cache_key)

    @staticmethod
    def write_cache(cache_key, result):
        if CURRENCY_CACHE_TIMEOUT <= 0:
            return

        cache.set(
            cache_key,
            result,
            timeout=CURRENCY_CACHE_TIMEOUT,
        )


__all__ = [
    "CurrencyService",
    "DEFAULT_BASE_CURRENCY",
    "CURRENCY_CODE_PATTERN",
]
