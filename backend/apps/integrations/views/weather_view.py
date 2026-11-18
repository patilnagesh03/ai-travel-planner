"""
API views for weather forecasts.

The provider is named in the message ("The weather provider ...") so the
caller can tell which integration is having trouble. Like the place views,
unexpected exceptions are allowed to propagate rather than being flattened
into a generic response.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.integrations.exceptions import (
    UnsupportedDestinationError,
)
from backend.apps.integrations.responses import (
    PROVIDER_ERRORS,
    provider_error_response,
    unsupported_input_response,
)
from backend.apps.integrations.services import WeatherService
from backend.apps.trips.services.trip_service import TripService


class TripWeatherView(APIView):
    """Daily forecast for the destination and dates of one trip."""

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        # Ownership is enforced by the service: a trip that does not exist,
        # or belongs to somebody else, is a 404 either way.
        trip = TripService.get_user_trip(
            user=request.user,
            trip_id=trip_id,
        )

        try:
            data = WeatherService.forecast_for_trip(trip)

        except UnsupportedDestinationError as exc:
            return unsupported_input_response(exc)

        except PROVIDER_ERRORS as exc:
            return provider_error_response(exc, "weather")

        return Response(
            {
                "success": True,
                "message": "Forecast retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


__all__ = ["TripWeatherView"]
