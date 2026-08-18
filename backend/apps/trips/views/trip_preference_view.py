import logging

from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.trips.models import Trip, TripPreference
from backend.apps.trips.serializers.trip_preferences_serializer import (
    TripPreferenceSerializer,
)
from backend.apps.trips.services.trip_preference_service import (
    TripPreferenceService,
)


logger = logging.getLogger(__name__)


class TripPreferenceView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id):

        try:
            trip = get_object_or_404(
                Trip,
                id=trip_id,
                user=request.user,
            )

            if hasattr(trip, "preferences"):
                raise ValidationError(
                    {
                        "trip": (
                            "Preferences already exist for this trip."
                            )
                    }
                )
            
            serializer = TripPreferenceSerializer(
                data=request.data,
            )

            serializer.is_valid(
                raise_exception=True,
            )

            preferences = (
                TripPreferenceService.create_preferences(
                    trip=trip,
                    validated_data=serializer.validated_data,
                )
            )

            response_serializer = TripPreferenceSerializer(
                preferences,
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Trip preferences created successfully."
                    ),
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while creating trip preferences."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while creating "
                        "trip preferences."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request, trip_id):

        try:
            trip = get_object_or_404(
                Trip,
                id=trip_id,
                user=request.user,
            )

            preferences = (
                TripPreferenceService.get_preferences(
                    trip,
                )
            )

            serializer = TripPreferenceSerializer(
                preferences,
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Trip preferences retrieved successfully."
                    ),
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except TripPreference.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Trip preferences not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.exception(
                "Unexpected error while retrieving trip preferences."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving "
                        "trip preferences."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, trip_id):

        try:
            trip = get_object_or_404(
                Trip,
                id=trip_id,
                user=request.user,
            )

            preferences = (
                TripPreferenceService.get_preferences(
                    trip,
                )
            )

            serializer = TripPreferenceSerializer(
                preferences,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(
                raise_exception=True,
            )

            updated_preferences = (
                TripPreferenceService.update_preferences(
                    preferences=preferences,
                    validated_data=serializer.validated_data,
                )
            )

            response_serializer = TripPreferenceSerializer(
                updated_preferences,
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Trip preferences updated successfully."
                    ),
                    "data": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except TripPreference.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Trip preferences not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while updating trip preferences."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while updating "
                        "trip preferences."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, trip_id):

        try:
            trip = get_object_or_404(
                Trip,
                id=trip_id,
                user=request.user,
            )

            preferences = (
                TripPreferenceService.get_preferences(
                    trip,
                )
            )

            TripPreferenceService.delete_preferences(
                preferences,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        except TripPreference.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Trip preferences not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.exception(
                "Unexpected error while deleting trip preferences."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while deleting "
                        "trip preferences."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )