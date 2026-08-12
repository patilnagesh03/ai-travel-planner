from django.db import transaction
from backend.apps.trips.models import Trip


class TripService:

    @staticmethod
    @transaction.atomic
    def create_trip(user, validated_data):
        trip = Trip.objects.create(
            user=user,
            **validated_data,
        )

        return trip

    @staticmethod
    def get_user_trips(user):
        return (
            Trip.objects
            .filter(user=user)
            .order_by("-created_at")
        )