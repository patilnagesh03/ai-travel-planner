"""
HTTP client for the Frankfurter exchange-rate API.

Frankfurter republishes European Central Bank reference rates. It needs no
key, so currency conversion works in a local development setup without an
account or a paid plan.

The client deliberately does not convert amounts: rates are what the
provider owns, and arithmetic is better done once, in the service layer,
where it can be tested without mocking HTTP.
"""

import logging

import requests

from backend.apps.integrations.config import (
    CURRENCY_API_URL,
    CURRENCY_CONNECT_TIMEOUT,
    CURRENCY_READ_TIMEOUT,
    INTEGRATIONS_USER_AGENT,
)
from backend.apps.integrations.exceptions import (
    IntegrationError,
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    UnsupportedCurrencyError,
)


logger = logging.getLogger(__name__)


TEMPORARY_STATUS_CODES = frozenset({500, 502, 503, 504})

# The provider answers 404 or 422 for a currency code it does not publish.
UNSUPPORTED_CURRENCY_STATUS_CODES = frozenset({404, 422})


class FrankfurterClient:
    """Thin, synchronous client for Frankfurter's latest rates."""

    def __init__(
        self,
        api_url=None,
        connect_timeout=None,
        read_timeout=None,
        user_agent=None,
    ):
        self.api_url = (api_url or CURRENCY_API_URL).rstrip("/")

        self.connect_timeout = (
            CURRENCY_CONNECT_TIMEOUT
            if connect_timeout is None
            else connect_timeout
        )

        self.read_timeout = (
            CURRENCY_READ_TIMEOUT
            if read_timeout is None
            else read_timeout
        )

        self.user_agent = user_agent or INTEGRATIONS_USER_AGENT

    def fetch_latest(self, base, symbols=None):
        """Return the provider's latest rates payload for ``base``.

        ``symbols`` is a list of three-letter codes. When it is empty the
        provider returns every currency it publishes, which the app never
        needs: the caller must have narrowed the request first.
        """

        params = {"base": base}

        if symbols:
            params["symbols"] = ",".join(symbols)

        response = self._get(params)

        payload = self._parse_json(response)

        rates = payload.get("rates")

        if not isinstance(rates, dict) or not rates:
            logger.warning(
                "Frankfurter returned a payload without usable rates."
            )

            raise IntegrationResponseError(
                "The currency provider returned an unexpected response."
            )

        return payload

    def _get(self, params):
        try:
            response = requests.get(
                "{base}/latest".format(base=self.api_url),
                params=params,
                headers=self._build_headers(),
                timeout=(
                    self.connect_timeout,
                    self.read_timeout,
                ),
            )

        except requests.exceptions.Timeout as exc:
            logger.warning(
                "Frankfurter request timed out "
                "(connect=%ss, read=%ss).",
                self.connect_timeout,
                self.read_timeout,
            )

            raise IntegrationTimeoutError(
                "The currency provider did not respond in time."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "Could not connect to the currency provider at %s.",
                self.api_url,
            )

            raise IntegrationUnavailableError(
                "The currency provider could not be reached."
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.exception(
                "Unexpected failure while calling the currency provider."
            )

            raise IntegrationError(
                "The currency provider request could not be completed."
            ) from exc

        self._raise_for_status(response)

        return response

    def _build_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def _raise_for_status(self, response):
        if response.ok:
            return

        status_code = response.status_code

        retry_after = self._parse_retry_after(response)

        if status_code in UNSUPPORTED_CURRENCY_STATUS_CODES:
            logger.info(
                "Frankfurter does not publish one of the requested "
                "currencies (HTTP %s).",
                status_code,
            )

            raise UnsupportedCurrencyError(
                "One or more requested currencies are not supported by "
                "the rates provider."
            )

        if status_code == 429:
            logger.warning(
                "Frankfurter rate limited the request (HTTP %s).",
                status_code,
            )

            raise IntegrationRateLimitError(
                "The currency provider is rate limiting requests.",
                retry_after=retry_after,
            )

        if status_code in TEMPORARY_STATUS_CODES:
            logger.warning(
                "Frankfurter is temporarily unavailable (HTTP %s).",
                status_code,
            )

            raise IntegrationUnavailableError(
                "The currency provider is temporarily unavailable.",
                retry_after=retry_after,
            )

        if 400 <= status_code < 500:
            logger.warning(
                "Frankfurter rejected the request (HTTP %s).",
                status_code,
            )

            raise IntegrationRequestError(
                "The currency provider rejected the request."
            )

        logger.error(
            "Frankfurter returned an unexpected status code (HTTP %s).",
            status_code,
        )

        raise IntegrationError(
            "The currency provider returned an unexpected response."
        )

    @staticmethod
    def _parse_retry_after(response):
        raw_value = response.headers.get("Retry-After")

        if not raw_value:
            return None

        try:
            seconds = int(raw_value)
        except (TypeError, ValueError):
            return None

        return max(seconds, 0)

    @staticmethod
    def _parse_json(response):
        try:
            payload = response.json()

        except ValueError as exc:
            logger.warning(
                "Frankfurter returned a response that is not valid JSON."
            )

            raise IntegrationResponseError(
                "The currency provider returned an unreadable response."
            ) from exc

        if not isinstance(payload, dict):
            logger.warning(
                "Frankfurter returned an unexpected JSON structure (%s).",
                type(payload).__name__,
            )

            raise IntegrationResponseError(
                "The currency provider returned an unexpected response."
            )

        return payload


__all__ = ["FrankfurterClient"]
