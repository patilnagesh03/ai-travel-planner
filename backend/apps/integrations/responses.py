"""
HTTP responses shared by the external-integration views.

Every integration (places, weather, currency) has the same expected failure
modes, and every one of them should be explained to the caller the same way.
Keeping the mapping here means the three views cannot drift apart, and it
keeps the provider's name out of the status-code logic.

The provider is named in the message ("The weather provider ...") so a
failure is actionable without exposing URLs, response bodies or stack
traces.
"""

from rest_framework import status
from rest_framework.response import Response

from backend.apps.integrations.exceptions import (
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


# Used when the provider rate limits us but does not say for how long.
DEFAULT_RETRY_AFTER_SECONDS = 60

# Failures that mean "the provider let us down", as opposed to bad input.
PROVIDER_ERRORS = (
    IntegrationRateLimitError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    IntegrationRequestError,
    IntegrationResponseError,
)


def unsupported_input_response(exc):
    """Return a 400 for a destination or currency we cannot handle.

    These are the caller's mistakes, so the exception's own message is
    already written for them and can be passed through unchanged.
    """

    return Response(
        {
            "success": False,
            "message": str(exc),
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def provider_error_response(exc, provider):
    """Map an expected provider failure onto an HTTP response.

    ``provider`` is a lower-case noun used in the message, for example
    ``"places"`` or ``"weather"``.
    """

    label = "The {provider} provider".format(provider=provider)

    if isinstance(exc, IntegrationRateLimitError):
        retry_after = exc.retry_after or DEFAULT_RETRY_AFTER_SECONDS

        response = Response(
            {
                "success": False,
                "message": (
                    "{label} is rate limiting requests. "
                    "Please try again shortly.".format(label=label)
                ),
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

        response["Retry-After"] = str(retry_after)

        return response

    if isinstance(exc, IntegrationTimeoutError):
        return Response(
            {
                "success": False,
                "message": (
                    "{label} did not respond in time. "
                    "Please try again shortly.".format(label=label)
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if isinstance(exc, IntegrationUnavailableError):
        return Response(
            {
                "success": False,
                "message": (
                    "{label} is temporarily unavailable. "
                    "Please try again shortly.".format(label=label)
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if isinstance(exc, IntegrationRequestError):
        return Response(
            {
                "success": False,
                "message": (
                    "{label} rejected the request.".format(label=label)
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # IntegrationResponseError - the provider answered, but not usefully.
    return Response(
        {
            "success": False,
            "message": (
                "{label} returned an unexpected response.".format(
                    label=label,
                )
            ),
        },
        status=status.HTTP_502_BAD_GATEWAY,
    )


__all__ = [
    "DEFAULT_RETRY_AFTER_SECONDS",
    "PROVIDER_ERRORS",
    "provider_error_response",
    "unsupported_input_response",
]
