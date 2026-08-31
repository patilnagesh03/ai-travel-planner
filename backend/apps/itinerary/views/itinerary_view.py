import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from backend.apps.itinerary.serializers import ItinerarySerializer
from backend.apps.itinerary.services.itinerary_service import (
    ItineraryService,
)


logger = logging.getLogger(__name__)


class ItineraryView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id):

        try:
            serializer = ItinerarySerializer(
                data=request.data,
            )

            serializer.is_valid(
                raise_exception=True,
            )

            itinerary = ItineraryService.create_itinerary(
                user=request.user,
                trip_id=trip_id,
                validated_data=serializer.validated_data,
            )

            response_serializer = ItinerarySerializer(
                itinerary,
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Itinerary created successfully."
                    ),
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while creating itinerary."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while creating "
                        "the itinerary."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    def get(self, request, trip_id):

        try:
            itinerary = ItineraryService.get_itinerary(
                user=request.user,
                trip_id=trip_id,
            )

            serializer = ItinerarySerializer(
                itinerary,
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Itinerary retrieved successfully."
                    ),
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception(
                "Unexpected error while retrieving itinerary."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving "
                        "the itinerary."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )