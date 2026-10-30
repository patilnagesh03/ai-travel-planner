"""
Serializers for the currency API.

Validation here is about *shape*: is the base a single value, is the
symbols list non-empty and short enough. Whether a well-formed code is a
currency the provider publishes is only known after the provider answers,
so that decision belongs to the service.
"""

from rest_framework import serializers

from backend.apps.integrations.config import MAX_CURRENCY_SYMBOLS
from backend.apps.integrations.services.currency_service import (
    DEFAULT_BASE_CURRENCY,
)


class CurrencyRatesSerializer(serializers.Serializer):
    """Validates the query parameters of a rates request."""

    base = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=3,
        default=DEFAULT_BASE_CURRENCY,
    )

    symbols = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=120,
    )

    def validate_base(self, value):
        return value.strip().upper()

    def validate_symbols(self, value):
        requested = [
            part.strip().upper()
            for part in value.split(",")
            if part.strip()
        ]

        if not requested:
            raise serializers.ValidationError(
                "Provide at least one target currency."
            )

        if len(requested) > MAX_CURRENCY_SYMBOLS:
            raise serializers.ValidationError(
                "Ask for at most {maximum} currencies at a time.".format(
                    maximum=MAX_CURRENCY_SYMBOLS,
                )
            )

        return requested


__all__ = ["CurrencyRatesSerializer"]
