"""
Configuration for the AI provider.

The AI layer talks to Ollama by default. Ollama runs locally, which means
no API key, no cost and no data leaving the machine.

The generation timeout is deliberately much larger than the place search
timeouts. Asking a local model to plan a multi-day trip takes far longer
than asking Overpass for a list of nearby places, and the two budgets have
nothing to do with each other.
"""

from django.conf import settings


AI_PROVIDER = settings.AI_PROVIDER

OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL

OLLAMA_MODEL = settings.OLLAMA_MODEL

# How long (seconds) we wait for the model to finish a single generation.
# Local models on modest hardware can take a while.
OLLAMA_TIMEOUT = settings.OLLAMA_TIMEOUT

# Lower values give more predictable, more conservative itineraries.
OLLAMA_TEMPERATURE = settings.OLLAMA_TEMPERATURE


__all__ = [
    "AI_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT",
    "OLLAMA_TEMPERATURE",
]
