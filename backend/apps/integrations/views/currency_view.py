"""
API views for currency conversion.

Rates are public information, but the endpoint still requires
authentication: it is part of the traveller's trip-planning surface, and
an authenticated-only rule keeps the provider call budget tied to real
users rather than to anonymous traffic.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.integrations.exceptions import UnsupportedCurrencyError
from backend.apps.integrations.responses import (
    PROVIDER_ERRORS,
    provider_error_response,
    unsupported_input_response,
)
from backend.apps.integrations.serializers import CurrencyRatesSerializer
from backend.apps.integrations.services import CurrencyService


class CurrencyRatesView(APIView):
    """Latest reference rates for a base currency."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrencyRatesSerializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        try:
            data = CurrencyService.get_rates(
                base=serializer.validated_data["base"],
                symbols=serializer.validated_data["symbols"],
            )

        except UnsupportedCurrencyError as exc:
            return unsupported_input_response(exc)

        except PROVIDER_ERRORS as exc:
            return provider_error_response(exc, "currency")

        return Response(
            {
                "success": True,
                "message": "Rates retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


__all__ = ["CurrencyRatesView"]
