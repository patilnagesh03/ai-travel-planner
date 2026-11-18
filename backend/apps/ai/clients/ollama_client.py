"""
HTTP client for a local Ollama server.

Ollama exposes a small HTTP API. The two endpoints we care about are:

* ``POST /api/generate`` - run a prompt and get a completion back.
* ``GET  /api/tags``     - list the models that have been pulled.

This client is only responsible for transport. It knows nothing about
itineraries, places or prompts. The raw model output is returned as a
string; interpreting it is the job of the service layer.
"""

import json
import logging

import requests

from backend.apps.ai.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
)
from backend.apps.ai.exceptions import (
    AIModelError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseError,
)


logger = logging.getLogger(__name__)


class OllamaClient:
    """Thin, synchronous HTTP client for a local Ollama server."""

    def __init__(
        self,
        base_url=None,
        model=None,
        timeout=None,
        temperature=None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL

        # `None` means "use the configured default".
        self.timeout = (
            OLLAMA_TIMEOUT if timeout is None else timeout
        )

        self.temperature = (
            OLLAMA_TEMPERATURE
            if temperature is None
            else temperature
        )

    def generate(self, prompt, system=None):
        """Run a prompt and return the raw completion text.

        The model is asked for JSON, but the text is returned as-is. Whether
        it really is valid JSON is decided by the caller, which is the only
        layer that knows what a valid answer looks like.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        if system:
            payload["system"] = system

        response = self._post("/api/generate", payload)

        data = self._parse_json_object(response)

        if "response" not in data:
            logger.warning(
                "Ollama response did not contain a `response` field."
            )

            raise AIResponseError(
                "The AI provider returned an unexpected response."
            )

        completion = data["response"]

        if not isinstance(completion, str):
            raise AIResponseError(
                "The AI provider returned an unexpected response."
            )

        return completion

    def list_models(self):
        """Return the names of the models available on the server."""

        response = self._get("/api/tags")

        data = self._parse_json_object(response)

        models = data.get("models")

        if not isinstance(models, list):
            raise AIResponseError(
                "The AI provider returned an unexpected response."
            )

        return [
            model.get("name")
            for model in models
            if isinstance(model, dict) and model.get("name")
        ]

    def is_available(self):
        """Return True when the server is up and the model is present.

        This is used by the diagnostics endpoint so that a developer can see
        at a glance whether Ollama is running and whether the configured
        model has been pulled.
        """

        try:
            available = self.list_models()
        except (AIProviderUnavailableError, AIProviderTimeoutError):
            return False
        except AIResponseError:
            return False

        return self.model in available

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _post(self, path, payload):
        url = "{base}{path}".format(base=self.base_url, path=path)

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout,
            )

        except requests.exceptions.Timeout as exc:
            logger.warning(
                "Ollama did not finish within %ss.",
                self.timeout,
            )

            raise AIProviderTimeoutError(
                "The AI provider did not finish in time."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "Could not connect to the AI provider at %s.",
                self.base_url,
            )

            raise AIProviderUnavailableError(
                "The AI provider could not be reached. Is Ollama running?"
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.exception(
                "Unexpected failure while calling the AI provider."
            )

            raise AIProviderUnavailableError(
                "The AI provider request could not be completed."
            ) from exc

        self._raise_for_status(response)

        return response

    def _get(self, path):
        url = "{base}{path}".format(base=self.base_url, path=path)

        try:
            response = requests.get(
                url,
                headers=self._build_headers(),
                timeout=self.timeout,
            )

        except requests.exceptions.Timeout as exc:
            raise AIProviderTimeoutError(
                "The AI provider did not finish in time."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            raise AIProviderUnavailableError(
                "The AI provider could not be reached. Is Ollama running?"
            ) from exc

        except requests.exceptions.RequestException as exc:
            raise AIProviderUnavailableError(
                "The AI provider request could not be completed."
            ) from exc

        self._raise_for_status(response)

        return response

    def _build_headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _raise_for_status(self, response):
        if response.ok:
            return

        status_code = response.status_code

        if status_code == 404:
            # Ollama answers 404 when the model has not been pulled.
            logger.warning(
                "The AI provider does not know the model '%s'.",
                self.model,
            )

            raise AIModelError(
                "The configured AI model is not available. "
                "Pull it first with `ollama pull`."
            )

        if status_code >= 500:
            logger.warning(
                "The AI provider returned HTTP %s.",
                status_code,
            )

            raise AIProviderUnavailableError(
                "The AI provider is temporarily unavailable."
            )

        logger.warning(
            "The AI provider rejected the request (HTTP %s).",
            status_code,
        )

        raise AIResponseError(
            "The AI provider rejected the request."
        )

    @staticmethod
    def _parse_json_object(response):
        try:
            payload = response.json()

        except ValueError as exc:
            # `requests.exceptions.JSONDecodeError` derives from
            # `json.JSONDecodeError`, which derives from `ValueError`.
            logger.warning(
                "The AI provider returned a response that is not JSON."
            )

            raise AIResponseError(
                "The AI provider returned an unreadable response."
            ) from exc

        if not isinstance(payload, dict):
            raise AIResponseError(
                "The AI provider returned an unexpected response."
            )

        return payload


def parse_json_completion(completion):
    """Parse a completion that the model was asked to make JSON.

    Local models often wrap JSON in a markdown code fence, so that is
    stripped before parsing.
    """

    if not isinstance(completion, str):
        raise AIResponseError(
            "The AI provider returned an unexpected response."
        )

    text = completion.strip()

    if text.startswith("```"):
        # ```json ... ``` -> json ...
        text = text.split("\n", 1)[-1]

        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]

        text = text.strip()

    try:
        payload = json.loads(text)
    except ValueError as exc:
        logger.warning(
            "The AI provider did not return valid JSON."
        )

        raise AIResponseError(
            "The AI provider did not return a usable plan."
        ) from exc

    if not isinstance(payload, dict):
        raise AIResponseError(
            "The AI provider returned an unexpected response."
        )

    return payload


__all__ = ["OllamaClient", "parse_json_completion"]
