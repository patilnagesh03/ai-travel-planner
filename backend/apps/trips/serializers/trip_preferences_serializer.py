from rest_framework import serializers

from backend.apps.trips.enums import (
    AccommodationType,
    TravelPace,
    TravelStyle,
)
from backend.apps.trips.models import Interest, TripPreference


class TripPreferenceSerializer(serializers.ModelSerializer):

    interest_ids = serializers.PrimaryKeyRelatedField(
        source="interests",
        queryset=Interest.objects.all(),
        many=True,
        required=False,
    )

    travel_style = serializers.ChoiceField(
        choices=TravelStyle.choices,
        required=False,
        default=TravelStyle.BALANCED,
    )

    accommodation = serializers.ChoiceField(
        choices=AccommodationType.choices,
        required=False,
        allow_null=True,
    )

    pace = serializers.ChoiceField(
        choices=TravelPace.choices,
        required=False,
        default=TravelPace.MODERATE,
    )

    class Meta:
        model = TripPreference

        fields = (
            "id",
            "trip",
            "travel_style",
            "accommodation",
            "pace",
            "interest_ids",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "trip",
            "created_at",
            "updated_at",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["interests"] = [
            {
                "id": str(interest.id),
                "name": interest.name,
            }
            for interest in instance.interests.all()
        ]

        representation.pop("interest_ids", None)

        return representation