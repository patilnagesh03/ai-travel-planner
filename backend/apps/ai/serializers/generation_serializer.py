"""
Serializers for the AI itinerary generation API.
"""

from rest_framework import serializers

from backend.apps.itinerary.enums import ActivityType


class ItineraryGenerationRequestSerializer(serializers.Serializer):
    """Validates the body of a generation request."""

    dry_run = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "Generate the plan and return it without saving anything."
        ),
    )

    replace = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "Allow an existing itinerary for this trip to be replaced."
        ),
    )


class GeneratedPlaceSerializer(serializers.Serializer):
    """The place an activity refers to, using our own data."""

    source_id = serializers.CharField()
    name = serializers.CharField()
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    address = serializers.CharField(allow_null=True)


class GeneratedItemSerializer(serializers.Serializer):
    """One activity inside a generated day."""

    title = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    start_time = serializers.TimeField(allow_null=True)
    end_time = serializers.TimeField(allow_null=True)
    activity_type = serializers.ChoiceField(
        choices=ActivityType.choices,
    )
    place = GeneratedPlaceSerializer()


class GeneratedDaySerializer(serializers.Serializer):
    """One day of a generated plan."""

    date = serializers.DateField()
    items = GeneratedItemSerializer(many=True)


class GeneratedPlanSerializer(serializers.Serializer):
    """A complete generated plan."""

    title = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    days = GeneratedDaySerializer(many=True)
