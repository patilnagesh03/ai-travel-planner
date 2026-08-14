import uuid

from django.conf import settings
from django.db import models


class Trip(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trips",
    )

    title = models.CharField(
        max_length=150,
    )

    destination = models.CharField(
        max_length=255,
    )

    start_date = models.DateField()

    end_date = models.DateField()

    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="INR",
    )

    travelers = models.PositiveIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "trips"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.destination}"