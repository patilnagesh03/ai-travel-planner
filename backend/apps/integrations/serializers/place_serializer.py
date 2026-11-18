"""
Serializers for the place discovery API.

These are the only place where the internal `Place` structure becomes JSON.
Nothing above this layer ever sees a raw provider element.
"""

from rest_framework import serializers

from backend.apps.integrations.config import MAX_PLACES_PER_SEARCH
from backend.apps.integrations.schemas import Place, PlaceCategory
from backend.apps.integrations.services.destination_service import (
    MAX_SEARCH_RADIUS_KM,
)


class PlaceSerializer(serializers.Serializer):
    """Serializes a normalized `Place` for an API response."""

    source = serializers.CharField(read_only=True)
    source_id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    category = serializers.ChoiceField(
        choices=PlaceCategory.choices,
        read_only=True,
    )
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    address = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    opening_hours = serializers.CharField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        # Not a ModelSerializer, but the Meta block keeps the field list
        # discoverable in the same way as the rest of the project.
        fields = (
            "source",
            "source_id",
            "name",
            "category",
            "latitude",
            "longitude",
            "address",
            "opening_hours",
        )


class PlaceSearchSerializer(serializers.Serializer):
    """Validates the query parameters of a place search.

    A search needs either a destination name or a full latitude/longitude
    pair. Coordinates take precedence, so they act as an override.
    """

    destination = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=255,
    )

    latitude = serializers.FloatField(
        required=False,
        min_value=-90,
        max_value=90,
    )

    longitude = serializers.FloatField(
        required=False,
        min_value=-180,
        max_value=180,
    )

    radius_km = serializers.FloatField(
        required=False,
        min_value=0.1,
        max_value=MAX_SEARCH_RADIUS_KM,
    )

    categories = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_PLACES_PER_SEARCH,
    )

    def validate(self, attrs):
        has_destination = bool(attrs.get("destination"))
        has_latitude = attrs.get("latitude") is not None
        has_longitude = attrs.get("longitude") is not None

        if has_latitude != has_longitude:
            raise serializers.ValidationError(
                {
                    "coordinates": (
                        "Provide both latitude and longitude, or neither."
                    )
                }
            )

        if not has_destination and not has_latitude:
            raise serializers.ValidationError(
                {
                    "destination": (
                        "Provide a destination name, or a latitude and "
                        "longitude pair."
                    )
                }
            )

        return attrs

    def get_categories(self):
        """Return the requested categories as `PlaceCategory` members."""

        raw_categories = self.validated_data.get("categories")

        if not raw_categories:
            return None

        requested = [
            value.strip()
            for value in raw_categories.split(",")
            if value.strip()
        ]

        if not requested:
            return None

        categories = []

        for value in requested:
            try:
                category = PlaceCategory(value)
            except ValueError:
                try:
                    category = PlaceCategory[value.upper()]
                except KeyError as exc:
                    raise serializers.ValidationError(
                        {
                            "categories": (
                                "'{value}' is not a supported category. "
                                "Supported categories: {supported}."
                            ).format(
                                value=value,
                                supported=", ".join(
                                    choice.value
                                    for choice in PlaceCategory
                                    if choice != PlaceCategory.OTHER
                                ),
                            )
                        }
                    ) from exc

            if category not in categories:
                categories.append(category)

        return categories
