"""
API view for accommodation discovery.

Hotels are read from the same Overpass pipeline as every other place, so the
failure modes are identical to the place search: an unsupported destination
is a 400 and a provider problem is mapped by the shared response helper.
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
from backend.apps.integrations.serializers import (
    HotelDestinationSerializer,
    HotelSearchSerializer,
    HotelSerializer,
)
from backend.apps.integrations.services import HotelService
from backend.apps.trips.services.trip_service import TripService


class TripHotelSearchView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        trip = TripService.get_user_trip(
            user=request.user,
            trip_id=trip_id,
        )

        serializer = HotelSearchSerializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        try:
            result = HotelService.search_hotels(
                trip=trip,
                limit=serializer.validated_data.get("limit"),
            )

        except UnsupportedDestinationError as exc:
            return unsupported_input_response(exc)

        except PROVIDER_ERRORS as exc:
            return provider_error_response(exc, "accommodation")

        return Response(
            {
                "success": True,
                "message": "Hotels retrieved successfully.",
                "data": {
                    "destination": HotelDestinationSerializer(
                        result["destination"],
                    ).data,
                    "hotels": HotelSerializer(
                        result["hotels"],
                        many=True,
                    ).data,
                    "booking_url": result["booking_url"],
                    "attribution": result["attribution"],
                },
            },
            status=status.HTTP_200_OK,
        )
