from rest_framework import serializers

from backend.apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    trip_title = serializers.CharField(
        source="trip.title",
        read_only=True,
        allow_null=True,
    )

    is_read = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Notification

        fields = (
            "id",
            "kind",
            "title",
            "message",
            "trip",
            "trip_title",
            "is_read",
            "read_at",
            "created_at",
        )

        read_only_fields = fields
