from rest_framework import serializers


class ExpenseCategoryTotalSerializer(serializers.Serializer):
    """One row of the by-category breakdown."""

    category = serializers.CharField()
    label = serializers.CharField()
    total = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    count = serializers.IntegerField()


class ExpenseSummarySerializer(serializers.Serializer):
    """Budget versus actual spending for one trip.

    `remaining` is deliberately allowed to be negative: going over budget is a
    normal state, and clamping it to zero would hide how far over the trip is.
    """

    currency = serializers.CharField()
    budget = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    total_spent = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    remaining = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    over_budget = serializers.BooleanField()
    expense_count = serializers.IntegerField()
    by_category = ExpenseCategoryTotalSerializer(many=True)
