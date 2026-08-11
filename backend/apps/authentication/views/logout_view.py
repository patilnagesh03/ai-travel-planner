import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.authentication.serializers.logout_serializer import (
    LogoutSerializer,
)
from backend.apps.authentication.services.logout_service import (
    LogoutService,
)


logger = logging.getLogger(__name__)


class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            serializer = LogoutSerializer(
                data=request.data
            )

            serializer.is_valid(raise_exception=True)

            refresh_token = serializer.validated_data["refresh"]

            token = RefreshToken(refresh_token)

            token_user_id = str(
                token.payload.get("user_id")
            )

            current_user_id = str(request.user.id)

            if token_user_id != current_user_id:
                raise ValidationError(
                    {
                        "refresh": (
                            "The refresh token does not belong "
                            "to the authenticated user."
                        )
                    }
                )

            LogoutService.logout(refresh_token)

            return Response(
                {
                    "success": True,
                    "message": "Logout successful.",
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError:
            raise

        except TokenError:
            raise ValidationError(
                {
                    "refresh": (
                        "Invalid or expired refresh token."
                    )
                }
            )

        except Exception:
            logger.exception(
                "Unexpected error occurred during logout."
            )

            return Response(
                {
                    "success": False,
                    "message": "Something went wrong during logout.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )