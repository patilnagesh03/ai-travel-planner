import logging

from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.authentication.serializers.profile_serializer import (
    ProfileSerializer,
)
from backend.apps.authentication.services.profile_service import (
    ProfileService,
)


logger = logging.getLogger(__name__)


class ProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:
            if not request.user or not request.user.is_authenticated:
                raise NotAuthenticated(
                    "Authentication credentials were not provided."
                )

            user = ProfileService.get_profile(request.user)

            serializer = ProfileSerializer(user)

            return Response(
                {
                    "success": True,
                    "message": "Profile retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except NotAuthenticated:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while retrieving user profile."
            )

            return Response(
                {
                    "success": False,
                    "message": "Something went wrong while retrieving the profile.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )