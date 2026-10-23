"""
Custom exceptions raised by external service integrations.

These exceptions describe *meaningful* integration failures so that the layer
above (views) can map them onto sensible HTTP status codes without having to
know anything about the provider's internals.

Raw provider responses are never embedded in these exceptions. Anything
provider-specific belongs in the server-side log, not in an API response.
"""


class IntegrationsError(Exception):
    """Base class for every error raised by the integrations app.

    It gives callers a single root to catch, while still keeping provider
    failures (`IntegrationError`) separate from caller input problems
    (`UnsupportedDestinationError`).
    """


class IntegrationError(IntegrationsError):
    """Base exception for external integration failures."""

    def __init__(self, message=None, retry_after=None):
        super().__init__(message)

        # Seconds the provider asked us to wait, taken from the `Retry-After`
        # response header. `None` means the provider did not supply one.
        #
        # The initial implementation deliberately does NOT retry
        # automatically. This value exists so that a caller (or a future
        # retry layer) can honour the provider's advice.
        self.retry_after = retry_after


class UnsupportedDestinationError(IntegrationsError):
    """The requested destination could not be resolved to a search area.

    This is a problem with the *caller's* input, not a provider failure, so
    it is deliberately NOT a subclass of `IntegrationError`. A caller that
    catches `IntegrationError` to report "the provider is having trouble"
    must not accidentally report this one.
    """


class IntegrationTimeoutError(IntegrationError):
    """The external provider did not respond within the allowed time."""


class IntegrationRateLimitError(IntegrationError):
    """The external provider rate-limited the request."""


class IntegrationUnavailableError(IntegrationError):
    """The external provider is temporarily unavailable."""


class IntegrationRequestError(IntegrationError):
    """The external provider rejected the request."""


class IntegrationResponseError(IntegrationError):
    """The external provider returned an invalid or unexpected response."""
