"""
Serializers for the accommodation discovery API.

`HotelSerializer` extends the existing place payload with the one field the
hotel endpoint adds: the distance from the destination centre.
"""

from rest_framework import serializers

from backend.apps.integrations.config import MAX_PLACES_PER_SEARCH
from backend.apps.integrations.serializers.place_serializer import (
    PlaceSerializer,
)


class HotelSerializer(PlaceSerializer):

    distance_km = serializers.FloatField(read_only=True)

    class Meta(PlaceSerializer.Meta):
        fields = PlaceSerializer.Meta.fields + ("distance_km",)


class HotelSearchSerializer(serializers.Serializer):
    """Validates the optional ``limit`` query parameter."""

    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_PLACES_PER_SEARCH,
    )


class HotelDestinationSerializer(serializers.Serializer):

    name = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)


__all__ = [
    "HotelDestinationSerializer",
    "HotelSearchSerializer",
    "HotelSerializer",
]
