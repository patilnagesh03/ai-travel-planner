"""
API view for deterministic flight search links.

No provider is called, so the only expected failure is a trip without an
origin. That is caller data, not an outage, and it maps to a 400 with a
message explaining how to fix it.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.integrations.exceptions import MissingTripOriginError
from backend.apps.integrations.responses import unsupported_input_response
from backend.apps.integrations.serializers import FlightLinksSerializer
from backend.apps.integrations.services import FlightService
from backend.apps.trips.services.trip_service import TripService


class TripFlightLinksView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        # Ownership is enforced by the lookup: a missing trip and another
        # user's trip both produce a 404.
        trip = TripService.get_user_trip(
            user=request.user,
            trip_id=trip_id,
        )

        try:
            links = FlightService.build_links(trip)

        except MissingTripOriginError as exc:
            return unsupported_input_response(exc)

        serializer = FlightLinksSerializer(links)

        return Response(
            {
                "success": True,
                "message": "Flight links retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
