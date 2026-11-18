"""
Custom exceptions raised by the AI layer.

The hierarchy is deliberately its own, not a copy of the integrations one.
A local model fails in ways a REST API does not: the model may not be
pulled, the daemon may not be running, or the model may return something
that is not valid JSON at all.
"""


class AIError(Exception):
    """Base exception for AI layer failures."""

    def __init__(self, message=None):
        super().__init__(message)


class AIProviderUnavailableError(AIError):
    """The AI provider could not be reached or is not running."""


class AIProviderTimeoutError(AIError):
    """The AI provider did not finish within the allowed time."""


class AIModelError(AIError):
    """The requested model is not available on the provider."""


class AIResponseError(AIError):
    """The provider answered, but not with something we can use."""


class AIValidationError(AIError):
    """The generated plan did not pass validation.

    The raw model output is never exposed to API clients. It is logged
    server-side so that it can be diagnosed.
    """
