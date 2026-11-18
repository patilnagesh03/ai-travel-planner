"""
Configuration for the AI provider.

The AI layer talks to Groq, which serves open-weight models over an
OpenAI-compatible API. An API key is required, and every request leaves the
machine, so the key must never be committed.

The generation timeout is deliberately larger than the place search
timeouts. A full itinerary is a long completion, and the two budgets have
nothing to do with each other.
"""

from django.conf import settings


AI_PROVIDER = settings.AI_PROVIDER

GROQ_API_KEY = settings.GROQ_API_KEY

GROQ_BASE_URL = settings.GROQ_BASE_URL

GROQ_MODEL = settings.GROQ_MODEL

# How long (seconds) we wait for the model to finish a single generation.
GROQ_TIMEOUT = settings.GROQ_TIMEOUT

# Lower values give more predictable, more conservative itineraries.
GROQ_TEMPERATURE = settings.GROQ_TEMPERATURE


__all__ = [
    "AI_PROVIDER",
    "GROQ_API_KEY",
    "GROQ_BASE_URL",
    "GROQ_MODEL",
    "GROQ_TIMEOUT",
    "GROQ_TEMPERATURE",
]
