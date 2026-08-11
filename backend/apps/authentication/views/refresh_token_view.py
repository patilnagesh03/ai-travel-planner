import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.authentication.serializers.refresh_token_serializer import (
    RefreshTokenSerializer,
)


logger = logging.getLogger(__name__)


class RefreshTokenView(APIView):

    permission_classes = []

    def post(self, request):

        try:
            serializer = RefreshTokenSerializer(
                data=request.data
            )

            serializer.is_valid(raise_exception=True)

            return Response(
                {
                    "success": True,
                    "message": "Token refreshed successfully.",
                    "data": serializer.validated_data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error occurred while refreshing token."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while refreshing "
                        "the token."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )