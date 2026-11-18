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
    UnsupportedDestinationError,
)
from backend.apps.integrations.responses import (
    PROVIDER_ERRORS,
    provider_error_response,
    unsupported_input_response,
)
from backend.apps.integrations.serializers import (
    DestinationResolveSerializer,
    PlaceSearchSerializer,
    PlaceSerializer,
)
from backend.apps.integrations.services import (
    DestinationService,
    PlacesService,
)
from backend.apps.trips.services.trip_service import TripService


logger = logging.getLogger(__name__)


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

        except UnsupportedDestinationError as exc:
            return unsupported_input_response(exc)

        except PROVIDER_ERRORS as exc:
            return provider_error_response(exc, "places")

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


class DestinationResolveView(APIView):
    """Resolve a destination name to its centre and bounding box.

    The map and the forecast both need coordinates for a trip's free-text
    destination. Resolving here means the frontend does not have to
    duplicate the backend's spelling, alias and state rules.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = DestinationResolveSerializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        try:
            city = DestinationService.resolve_city(
                serializer.validated_data["destination"],
            )

        except UnsupportedDestinationError as exc:
            return unsupported_input_response(exc)

        return Response(
            {
                "success": True,
                "message": "Destination resolved successfully.",
                "data": {
                    "name": city.name,
                    "state": city.state,
                    "aliases": list(city.aliases),
                    "latitude": city.center[0],
                    "longitude": city.center[1],
                    "bbox": {
                        "south": city.south,
                        "west": city.west,
                        "north": city.north,
                        "east": city.east,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
