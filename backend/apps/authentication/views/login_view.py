import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from backend.apps.authentication.serializers.login_serializer import (
    LoginSerializer,
)
from backend.apps.authentication.services.auth_service import AuthService


logger = logging.getLogger(__name__)


class LoginView(APIView):

    permission_classes = []

    def post(self, request):
        try:
            serializer = LoginSerializer(
                data=request.data,
                context={"request": request},
            )

            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data["user"]

            result = AuthService.login(user)

            return Response(
                {
                    "success": True,
                    "message": "Login successful.",
                    "data": {
                        "user": {
                            "id": str(user.id),
                            "email": user.email,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                        },
                        "tokens": result["tokens"],
                    },
                },
                status=status.HTTP_200_OK,
            )
        
        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred during user login."
            )

            return Response(
                {
                    "success": False,
                    "message": "Something went wrong while logging in.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )