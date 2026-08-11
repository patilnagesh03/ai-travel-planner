import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.authentication.serializers.change_password_serializer import (
    ChangePasswordSerializer,
)
from backend.apps.authentication.services.password_service import (
    PasswordService,
)


logger = logging.getLogger(__name__)


class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            serializer = ChangePasswordSerializer(
                data=request.data
            )

            serializer.is_valid(raise_exception=True)

            PasswordService.change_password(
                user=request.user,
                current_password=serializer.validated_data[
                    "current_password"
                ],
                new_password=serializer.validated_data[
                    "new_password"
                ],
            )

            return Response(
                {
                    "success": True,
                    "message": "Password changed successfully.",
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while changing password."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while changing "
                        "the password."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )