import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.authentication.serializers.register_serializer import (
    RegisterSerializer,
)
from backend.apps.authentication.services.auth_service import AuthService


logger = logging.getLogger(__name__)


class RegisterView(APIView):

    permission_classes = []

    def post(self, request):
        try:
            # 1. Validate request data
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 2. Execute business logic
            user = AuthService.register(serializer.validated_data)

            # 3. Return successful response
            return Response(
                {
                    "success": True,
                    "message": "User registered successfully.",
                    "data": {
                        "id": str(user.id),
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError:
            # Validation errors are safe to return to the client.
            raise

        except Exception:
            # Log the actual error for debugging/monitoring.
            logger.exception("Unexpected error occurred during user registration.")

            # Never expose internal exception details to the client.
            return Response(
                {
                    "success": False,
                    "message": "Something went wrong while registering the user.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )