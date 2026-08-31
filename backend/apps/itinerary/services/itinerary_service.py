from django.db import transaction
from django.shortcuts import get_object_or_404
from backend.apps.itinerary.models import Itinerary
from backend.apps.trips.models import Trip


class ItineraryService:

    @staticmethod
    @transaction.atomic
    def create_itinerary(user, trip_id, validated_data):

        trip = get_object_or_404(
            Trip,
            id=trip_id,
            user=user,
        )

        if hasattr(trip, "itinerary"):
            raise ValueError(
                "An itinerary already exists for this trip."
            )

        itinerary = Itinerary.objects.create(
            trip=trip,
            **validated_data,
        )

        return itinerary

    @staticmethod
    def get_itinerary(user, trip_id):

        trip = get_object_or_404(
            Trip,
            id=trip_id,
            user=user,
        )

        return get_object_or_404(
            Itinerary,
            trip=trip,
        )