import uuid
from django.db import models


class Itinerary(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    trip = models.OneToOneField(
        "trips.Trip",
        on_delete=models.CASCADE,
        related_name="itinerary",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "itineraries"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title