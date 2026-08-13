from rest_framework import serializers

from backend.apps.trips.models import Trip
from backend.apps.trips.validators import (
    validate_budget,
    validate_currency,
    validate_travelers,
)


class TripSerializer(serializers.ModelSerializer):

    budget = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[validate_budget],
    )

    travelers = serializers.IntegerField(
        validators=[validate_travelers],
    )

    currency = serializers.CharField(
        max_length=3,
        validators=[validate_currency],
    )

    class Meta:
        model = Trip

        fields = (
            "id",
            "title",
            "destination",
            "start_date",
            "end_date",
            "budget",
            "currency",
            "travelers",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Title cannot be empty."
            )

        return value

    def validate_destination(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Destination cannot be empty."
            )

        return value

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            self.instance.start_date if self.instance else None,
        )
        end_date = attrs.get(
            "end_date",
            self.instance.end_date if self.instance else None,
            )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {
                    "end_date": (
                        "End date must be greater than or equal "
                        "to the start date."
                    )
                }
            )

        return attrs