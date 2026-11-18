"""Serializers for resolving a destination name to coordinates."""

from rest_framework import serializers


class DestinationResolveSerializer(serializers.Serializer):
    """Validates the single query parameter of the resolve endpoint."""

    destination = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=255,
    )


__all__ = ["DestinationResolveSerializer"]
