from rest_framework import serializers

from backend.apps.trips.models import Interest


class InterestSerializer(serializers.ModelSerializer):
    """Read-only representation of a trip interest."""

    class Meta:
        model = Interest

        fields = (
            "id",
            "name",
        )

        read_only_fields = (
            "id",
            "name",
        )
