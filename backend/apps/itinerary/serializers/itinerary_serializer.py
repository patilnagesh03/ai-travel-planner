from rest_framework import serializers
from backend.apps.itinerary.models import Itinerary


class ItinerarySerializer(serializers.ModelSerializer):

    class Meta:
        model = Itinerary

        fields = (
            "id",
            "trip",
            "title",
            "description",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "trip",
            "created_at",
            "updated_at",
        )

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Itinerary title cannot be empty."
            )

        return value

    def validate_description(self, value):
        if value is None:
            return value

        value = value.strip()

        return value