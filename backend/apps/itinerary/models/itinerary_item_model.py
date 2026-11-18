import uuid
from django.db import models
from backend.apps.itinerary.enums import ActivityType


class ItineraryItem(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    itinerary = models.ForeignKey(
        "Itinerary",
        on_delete=models.CASCADE,
        related_name="items",
    )

    date = models.DateField()

    start_time = models.TimeField(
        blank=True,
        null=True,
    )

    end_time = models.TimeField(
        blank=True,
        null=True,
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    location_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    location_address = models.TextField(
        blank=True,
        null=True,
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.OTHER,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "itinerary_items"
        ordering = ["date", "order", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "itinerary",
                    "date",
                    "order",
                ],
                name="unique_itinerary_item_order_per_date",
            ),
        ]

    def __str__(self):
        return f"{self.date} - {self.title}"