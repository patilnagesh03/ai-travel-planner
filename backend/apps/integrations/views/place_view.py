"""
API views for place discovery.

Error handling here is deliberate. Every *expected* failure mode has its own
exception clause and its own HTTP status:

===============================  ======  ==============================
Failure                          Status  Meaning
===============================  ======  ==============================
Unsupported destination           400     The caller asked for something
                                          we cannot search.
Invalid query parameters         400     Standard DRF validation error.
Provider rejected the request    400     Our Overpass query was invalid.
Provider rate limited us         429     Too many requests.
Provider response unreadable     502     The provider misbehaved.
Provider unavailable / timeout   503     Come back later.
===============================  ======  ==============================

Anything else is genuinely unexpected. We let it propagate so that Django
logs the traceback and returns a generic 500, rather than pretending that an
unexpected bug is a normal, explainable outcome. In DEBUG the developer sees
the real traceback; in production the client only ever sees a generic error.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.integrations.exceptions import (
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    UnsupportedDestinationError,
)
from backend.apps.integrations.serializers import (
    PlaceSearchSerializer,
    PlaceSerializer,
)
from backend.apps.integrations.services import (
    DestinationService,
    PlacesService,
)
from backend.apps.trips.services.trip_service import TripService


logger = logging.getLogger(__name__)


# Used when the provider rate limits us but does not say for how long.
DEFAULT_RETRY_AFTER_SECONDS = 60

# Every failure mode this API knows how to explain to a caller.
EXPECTED_ERRORS = (
    UnsupportedDestinationError,
    IntegrationRateLimitError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    IntegrationRequestError,
    IntegrationResponseError,
)


def build_error_response(exc):
    """Map an expected integration failure onto an HTTP response."""

    if isinstance(exc, UnsupportedDestinationError):
        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrationRateLimitError):
        retry_after = exc.retry_after or DEFAULT_RETRY_AFTER_SECONDS

        response = Response(
            {
                "success": False,
                "message": (
                    "The places provider is rate limiting requests. "
                    "Please try again shortly."
                ),
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

        response["Retry-After"] = str(retry_after)

        return response

    if isinstance(exc, IntegrationTimeoutError):
        return Response(
            {
                "success": False,
                "message": (
                    "The places provider did not respond in time. "
                    "Please try again shortly."
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if isinstance(exc, IntegrationUnavailableError):
        return Response(
            {
                "success": False,
                "message": (
                    "The places provider is temporarily unavailable. "
                    "Please try again shortly."
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if isinstance(exc, IntegrationRequestError):
        return Response(
            {
                "success": False,
                "message": (
                    "The places provider rejected the request."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # IntegrationResponseError - the provider answered, but not usefully.
    return Response(
        {
            "success": False,
            "message": (
                "The places provider returned an unexpected response."
            ),
        },
        status=status.HTTP_502_BAD_GATEWAY,
    )


class BasePlaceSearchView(APIView):
    """Shared behaviour for the place search endpoints."""

    permission_classes = [IsAuthenticated]

    def run_search(self, serializer):
        """Resolve the area, search it and render the result."""

        try:
            bbox = DestinationService.resolve(
                destination=serializer.validated_data.get("destination"),
                latitude=serializer.validated_data.get("latitude"),
                longitude=serializer.validated_data.get("longitude"),
                radius_km=serializer.validated_data.get("radius_km"),
            )

            places = PlacesService.search_places(
                bbox=bbox,
                categories=serializer.get_categories(),
                limit=serializer.validated_data.get("limit"),
            )

        except EXPECTED_ERRORS as exc:
            return build_error_response(exc)

        place_serializer = PlaceSerializer(places, many=True)

        return Response(
            {
                "success": True,
                "message": "Places retrieved successfully.",
                "data": place_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PlaceSearchView(BasePlaceSearchView):
    """Search for places by destination name or by coordinates."""

    def get(self, request):
        serializer = PlaceSearchSerializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        return self.run_search(serializer)


class TripPlaceSearchView(BasePlaceSearchView):
    """Search for places around the destination of one of your trips."""

    def get(self, request, trip_id):
        # Ownership is enforced here: a user can only search the trips they
        # own. A trip that does not exist, or belongs to somebody else,
        # results in a 404 - we do not reveal whether it exists.
        trip = TripService.get_user_trip(
            user=request.user,
            trip_id=trip_id,
        )

        params = request.query_params.copy()

        # The trip's own destination always wins over a query parameter.
        params["destination"] = trip.destination

        serializer = PlaceSearchSerializer(data=params)

        serializer.is_valid(raise_exception=True)

        return self.run_search(serializer)


class SupportedDestinationsView(APIView):
    """List the destinations that can be searched by name."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        destinations = DestinationService.supported_destinations()

        return Response(
            {
                "success": True,
                "message": (
                    "Supported destinations retrieved successfully."
                ),
                "data": destinations,
            },
            status=status.HTTP_200_OK,
        )
