import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.trips.serializers.trip_serializer import TripSerializer
from backend.apps.trips.services.trip_service import TripService


logger = logging.getLogger(__name__)


class TripView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            serializer = TripSerializer(
                data=request.data
            )

            serializer.is_valid(
                raise_exception=True
            )

            trip = TripService.create_trip(
                user=request.user,
                validated_data=serializer.validated_data,
            )

            response_serializer = TripSerializer(trip)

            return Response(
                {
                    "success": True,
                    "message": "Trip created successfully.",
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while creating trip."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while creating the trip."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    def get(self, request):

        try:
            trips = TripService.get_user_trips(
                user=request.user
            )

            serializer = TripSerializer(
                trips,
                many=True,
            )

            return Response(
                {
                    "success": True,
                    "message": "Trips retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while retrieving user trips."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving trips."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )