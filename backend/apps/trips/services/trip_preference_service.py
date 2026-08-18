from django.db import transaction
from backend.apps.trips.models import TripPreference


class TripPreferenceService:

    @staticmethod
    @transaction.atomic
    def create_preferences(trip, validated_data):

        interests = validated_data.pop(
            "interests",
            [],
        )

        preferences = TripPreference.objects.create(
            trip=trip,
            **validated_data,
        )

        if interests:
            preferences.interests.set(interests)

        return preferences

    @staticmethod
    def get_preferences(trip):
        return trip.preferences

    @staticmethod
    @transaction.atomic
    def update_preferences(
        preferences,
        validated_data,
    ):

        interests = validated_data.pop(
            "interests",
            None,
        )

        for field, value in validated_data.items():
            setattr(
                preferences,
                field,
                value,
            )

        preferences.save()

        if interests is not None:
            preferences.interests.set(interests)

        return preferences

    @staticmethod
    @transaction.atomic
    def delete_preferences(preferences):
        preferences.delete()