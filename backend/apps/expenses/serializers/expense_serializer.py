from decimal import Decimal

from rest_framework import serializers

from backend.apps.expenses.models import Expense


class ExpenseSerializer(serializers.ModelSerializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    class Meta:
        model = Expense

        fields = (
            "id",
            "trip",
            "title",
            "category",
            "amount",
            "spent_on",
            "notes",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "trip",
            "created_at",
            "updated_at",
        )

        extra_kwargs = {
            "spent_on": {"required": False},
            "notes": {"required": False, "allow_null": True},
        }

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Title cannot be empty."
            )

        return value
