import uuid

from django.conf import settings
from django.db import models

from backend.apps.notifications.enums import NotificationKind


class Notification(models.Model):
    """An in-app message about a trip.

    Notifications are created from the current state of the data rather than
    by a background worker: `NotificationService.sync_for_user` compares each
    trip's expenses and dates with the rules and inserts anything missing.

    `dedupe_key` is what keeps that sync idempotent. It encodes the state the
    message describes (for example the trip's budget or start date), so
    calling sync on every request never duplicates a message, while a change
    to the underlying state produces one new message.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )

    kind = models.CharField(
        max_length=30,
        choices=NotificationKind.choices,
    )

    title = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    dedupe_key = models.CharField(
        max_length=160,
    )

    read_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                name="unique_notification_per_user",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "read_at"],
                name="notification_user_read_idx",
            ),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return self.title
