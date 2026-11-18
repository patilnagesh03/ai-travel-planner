from decimal import Decimal

from rest_framework import serializers


def validate_budget(value):
    if value <= Decimal("0"):
        raise serializers.ValidationError(
            "Budget must be greater than zero."
        )

    return value


def validate_travelers(value):
    if value < 1:
        raise serializers.ValidationError(
            "There must be at least one traveler."
        )

    return value


def validate_currency(value):
    value = value.upper()

    if len(value) != 3 or not value.isalpha():
        raise serializers.ValidationError(
            "Currency must be a valid 3-letter currency code."
        )

    return value