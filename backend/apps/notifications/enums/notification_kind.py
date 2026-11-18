from django.db import models


class NotificationKind(models.TextChoices):
    BUDGET_EXCEEDED = "budget_exceeded", "Budget exceeded"
    TRIP_SOON = "trip_soon", "Trip starting soon"
    TRIP_ENDED = "trip_ended", "Trip ended"
