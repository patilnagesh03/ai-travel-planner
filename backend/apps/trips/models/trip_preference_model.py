import uuid
from django.db import models

from backend.apps.trips.enums.trip_preference_enums import (
    AccommodationType,
    TravelPace,
    TravelStyle,
)


class TripPreference(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    trip = models.OneToOneField(
        "Trip",
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    travel_style = models.CharField(
        max_length=20,
        choices=TravelStyle.choices,
        default=TravelStyle.BALANCED,
    )

    accommodation = models.CharField(
        max_length=20,
        choices=AccommodationType.choices,
        blank=True,
        null=True,
    )

    pace = models.CharField(
        max_length=20,
        choices=TravelPace.choices,
        default=TravelPace.MODERATE,
    )

    interests = models.ManyToManyField(
        "Interest",
        related_name="trip_preferences",
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "trip_preferences"

    def __str__(self):
        return f"Preferences for {self.trip.title}"