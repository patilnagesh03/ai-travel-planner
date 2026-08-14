import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.trips.models.trip_models import Trip
from backend.apps.trips.serializers.trip_serializer import TripSerializer
from backend.apps.trips.services.trip_service import TripService


logger = logging.getLogger(__name__)


class TripDetailView(APIView):

    permission_classes = [IsAuthenticated]

    # RETRIEVE PERTICULAR TRIP DETAIL
    def get(self, request, trip_id):

        try:
            trip = TripService.get_trip(
                user=request.user,
                trip_id=trip_id,
            )

            serializer = TripSerializer(trip)

            return Response(
                {
                    "success": True,
                    "message": "Trip retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Trip.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Trip not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.exception(
                "Unexpected error occurred while retrieving trip."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving the trip."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
    # UPDATE TRIP DETAILS
    def patch(self, request, trip_id):

        try:
            trip = TripService.get_trip(
                user=request.user,
                trip_id=trip_id,
            )

            serializer = TripSerializer(
                trip,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(
                raise_exception=True
            )

            updated_trip = TripService.update_trip(
                user=request.user,
                trip_id=trip_id,
                validated_data=serializer.validated_data,
            )

            response_serializer = TripSerializer(updated_trip)

            return Response(
                {
                    "success": True,
                    "message": "Trip updated successfully.",
                    "data": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Trip.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Trip not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while updating trip."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while updating the trip."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # DELETE TRIP DETAILS
    def delete(self, request, trip_id):

        try:
            TripService.delete_trip(
                user=request.user,
                trip_id=trip_id,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        except Trip.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Trip not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.exception(
                "Unexpected error occurred while deleting trip."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while deleting the trip."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )