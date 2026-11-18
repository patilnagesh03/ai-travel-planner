"""
HTTP client for the Open-Meteo forecast API.

Like the Overpass client, this module owns transport only: it builds the
request, sends it, and translates provider failures into integration
exceptions. Deciding *which* days a trip needs belongs to the service
layer.

Open-Meteo needs no key, so there is no credential to leak or rotate here.
Their usage policy asks clients not to hammer the endpoint, which is why
results are cached by the service and the requested window is capped at
the provider's 16-day limit.
"""

import logging

import requests

from backend.apps.integrations.config import (
    INTEGRATIONS_USER_AGENT,
    WEATHER_API_URL,
    WEATHER_CONNECT_TIMEOUT,
    WEATHER_READ_TIMEOUT,
)
from backend.apps.integrations.exceptions import (
    IntegrationError,
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


logger = logging.getLogger(__name__)


TEMPORARY_STATUS_CODES = frozenset({500, 502, 503, 504})

# The daily fields the app actually renders. Asking for only these keeps
# the response small and makes the contract explicit.
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "sunrise",
    "sunset",
)


class OpenMeteoClient:
    """Thin, synchronous client for the Open-Meteo daily forecast."""

    def __init__(
        self,
        api_url=None,
        connect_timeout=None,
        read_timeout=None,
        user_agent=None,
    ):
        self.api_url = api_url or WEATHER_API_URL

        # `None` means "use the configured default"; 0 would mean
        # "no timeout", so a truthiness check would be wrong here.
        self.connect_timeout = (
            WEATHER_CONNECT_TIMEOUT
            if connect_timeout is None
            else connect_timeout
        )

        self.read_timeout = (
            WEATHER_READ_TIMEOUT
            if read_timeout is None
            else read_timeout
        )

        self.user_agent = user_agent or INTEGRATIONS_USER_AGENT

    def fetch_daily_forecast(
        self,
        latitude,
        longitude,
        forecast_days,
    ):
        """Return the provider's raw daily forecast payload.

        The payload is validated just enough to guarantee that callers can
        index ``payload["daily"]``; interpreting the values is the service
        layer's job.
        """

        response = self._get(
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": ",".join(DAILY_FIELDS),
                "forecast_days": forecast_days,
                "timezone": "auto",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
            },
        )

        payload = self._parse_json(response)

        daily = payload.get("daily")

        if not isinstance(daily, dict):
            logger.warning(
                "Open-Meteo returned a payload without a 'daily' block."
            )

            raise IntegrationResponseError(
                "The weather provider returned an unexpected response."
            )

        if not isinstance(daily.get("time"), list):
            logger.warning(
                "Open-Meteo returned a 'daily' block without a 'time' list."
            )

            raise IntegrationResponseError(
                "The weather provider returned an unexpected response."
            )

        return payload

    def _get(self, params):
        try:
            response = requests.get(
                self.api_url,
                params=params,
                headers=self._build_headers(),
                timeout=(
                    self.connect_timeout,
                    self.read_timeout,
                ),
            )

        except requests.exceptions.Timeout as exc:
            logger.warning(
                "Open-Meteo request timed out "
                "(connect=%ss, read=%ss).",
                self.connect_timeout,
                self.read_timeout,
            )

            raise IntegrationTimeoutError(
                "The weather provider did not respond in time."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "Could not connect to the weather provider at %s.",
                self.api_url,
            )

            raise IntegrationUnavailableError(
                "The weather provider could not be reached."
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.exception(
                "Unexpected failure while calling the weather provider."
            )

            raise IntegrationError(
                "The weather provider request could not be completed."
            ) from exc

        self._raise_for_status(response)

        return response

    def _build_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def _raise_for_status(self, response):
        """Translate a non-success status code into an exception."""

        if response.ok:
            return

        status_code = response.status_code

        retry_after = self._parse_retry_after(response)

        if status_code == 429:
            logger.warning(
                "Open-Meteo rate limited the request (HTTP %s).",
                status_code,
            )

            raise IntegrationRateLimitError(
                "The weather provider is rate limiting requests.",
                retry_after=retry_after,
            )

        if status_code in TEMPORARY_STATUS_CODES:
            logger.warning(
                "Open-Meteo is temporarily unavailable (HTTP %s).",
                status_code,
            )

            raise IntegrationUnavailableError(
                "The weather provider is temporarily unavailable.",
                retry_after=retry_after,
            )

        if 400 <= status_code < 500:
            logger.warning(
                "Open-Meteo rejected the request (HTTP %s).",
                status_code,
            )

            raise IntegrationRequestError(
                "The weather provider rejected the request."
            )

        logger.error(
            "Open-Meteo returned an unexpected status code (HTTP %s).",
            status_code,
        )

        raise IntegrationError(
            "The weather provider returned an unexpected response."
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
                "Open-Meteo returned a response that is not valid JSON."
            )

            raise IntegrationResponseError(
                "The weather provider returned an unreadable response."
            ) from exc

        if not isinstance(payload, dict):
            logger.warning(
                "Open-Meteo returned an unexpected JSON structure (%s).",
                type(payload).__name__,
            )

            raise IntegrationResponseError(
                "The weather provider returned an unexpected response."
            )

        return payload


__all__ = ["OpenMeteoClient", "DAILY_FIELDS"]
