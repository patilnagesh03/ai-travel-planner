"""
API views for AI itinerary generation.

Error handling follows the same rule as the places API: every *expected*
failure has its own status code, and genuinely unexpected exceptions are
left to propagate rather than being flattened into a generic 500.

===============================  ======  ==============================
Failure                          Status  Meaning
===============================  ======  ==============================
Unsupported destination           400     The trip's destination cannot be
                                          searched.
Invalid request body             400     Standard DRF validation error.
Trip already has an itinerary    409     Send `replace=true` to allow it.
Places provider rate limited      429     Too many requests.
Provider returned an error       502     The model produced no usable
                                          plan.
Model timed out                  504     The model was too slow.
Model / provider unavailable      503     Come back later.
===============================  ======  ==============================
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.ai.clients import OllamaClient
from backend.apps.ai.config import (
    AI_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from backend.apps.ai.exceptions import (
    AIModelError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseError,
    AIValidationError,
)
from backend.apps.ai.serializers import (
    GeneratedPlanSerializer,
    ItineraryGenerationRequestSerializer,
)
from backend.apps.ai.services import (
    ItineraryExistsError,
    ItineraryGenerationService,
)
from backend.apps.integrations.exceptions import (
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    UnsupportedDestinationError,
)
from backend.apps.trips.services.trip_service import TripService


logger = logging.getLogger(__name__)


class ItineraryGenerationView(APIView):
    """Generate an itinerary for one of your trips."""

    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id):
        # Ownership is enforced: only the owner of a trip can generate an
        # itinerary for it.
        trip = TripService.get_user_trip(
            user=request.user,
            trip_id=trip_id,
        )

        request_serializer = ItineraryGenerationRequestSerializer(
            data=request.data,
        )

        request_serializer.is_valid(raise_exception=True)

        try:
            result = ItineraryGenerationService.generate(
                trip=trip,
                preferences=ItineraryGenerationService.get_preferences(
                    trip
                ),
                dry_run=request_serializer.validated_data["dry_run"],
                replace=request_serializer.validated_data["replace"],
            )

        except UnsupportedDestinationError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ItineraryExistsError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        except IntegrationRateLimitError as exc:
            retry_after = exc.retry_after or 60

            response = Response(
                {
                    "success": False,
                    "message": (
                        "The places provider is rate limiting requests. "
                        "Please try again shortly."
                    ),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

            response["Retry-After"] = str(retry_after)

            return response

        except IntegrationRequestError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The places provider rejected the request."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except IntegrationResponseError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The places provider returned an unexpected "
                        "response."
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except (
            IntegrationTimeoutError,
            IntegrationUnavailableError,
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "The places provider is temporarily unavailable. "
                        "Please try again shortly."
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except AIModelError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except AIProviderTimeoutError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The AI model took too long to respond. "
                        "Please try again."
                    ),
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        except AIProviderUnavailableError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The AI provider is unavailable. Please check that "
                        "it is running and try again."
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except (AIResponseError, AIValidationError):
            # The raw model output is never sent to the client. It is in the
            # server log, where it can be diagnosed.
            logger.warning(
                "The AI provider did not produce a usable plan."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "The AI model did not produce a usable plan. "
                        "Please try again."
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Itinerary generated successfully."
                    if result["persisted"]
                    else "Itinerary generated successfully. "
                    "Nothing was saved."
                ),
                "data": {
                    "itinerary_id": (
                        str(result["itinerary_id"])
                        if result["itinerary_id"]
                        else None
                    ),
                    "persisted": result["persisted"],
                    "plan": GeneratedPlanSerializer(
                        result["plan"]
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )


class AIStatusView(APIView):
    """Report whether the configured AI provider is usable."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        client = OllamaClient()

        return Response(
            {
                "success": True,
                "message": "AI provider status retrieved successfully.",
                "data": {
                    "provider": AI_PROVIDER,
                    "model": OLLAMA_MODEL,
                    "base_url": OLLAMA_BASE_URL,
                    "available": client.is_available(),
                },
            },
            status=status.HTTP_200_OK,
        )
