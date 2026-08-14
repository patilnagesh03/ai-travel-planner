from django.db import transaction
from backend.apps.trips.models.trip_models import Trip


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

    @staticmethod
    def get_trip(user, trip_id):
        return Trip.objects.get(
            id=trip_id,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def update_trip(user, trip_id, validated_data):
        trip = Trip.objects.get(
            id=trip_id,
            user=user,
        )

        for field, value in validated_data.items():
            setattr(trip, field, value)

        trip.save()

        return trip

    @staticmethod
    @transaction.atomic
    def delete_trip(user, trip_id):
        trip = Trip.objects.get(
            id=trip_id,
            user=user,
        )

        trip.delete()