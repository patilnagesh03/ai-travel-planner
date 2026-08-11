import logging

from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, ValidationError
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
        

    def patch(self, request):

        try:
            serializer = ProfileSerializer(
                request.user,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(raise_exception=True)

            user = ProfileService.update_profile(
                request.user,
                serializer.validated_data,
            )

            response_serializer = ProfileSerializer(user)

            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully.",
                    "data": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while updating user profile."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while updating the profile."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )