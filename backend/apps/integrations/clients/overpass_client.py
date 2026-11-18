"""
HTTP client for the Overpass API (OpenStreetMap data).

This module owns *transport* concerns only: building the request, sending it,
and translating provider failures into the integration exceptions defined in
``backend.apps.integrations.exceptions``.

It deliberately knows nothing about places, categories or bounding boxes.
Those are business decisions and belong to the service layer.

Notes on provider behaviour
---------------------------
* The public Overpass instances are shared, finite infrastructure. They rate
  limit, they go down, and they do not guarantee availability.
* There are deliberately **no automatic retries** in this first version. A
  retry policy can amplify load on an overloaded public service. When the
  provider sends ``Retry-After`` we capture it on the raised exception so a
  caller can honour it.
"""

import logging
import socket
from contextlib import contextmanager

import requests
from urllib3.util import connection as urllib3_connection

from backend.apps.integrations.config import (
    INTEGRATIONS_USER_AGENT,
    OVERPASS_API_URL,
    OVERPASS_CONNECT_TIMEOUT,
    OVERPASS_IPV4_ONLY,
    OVERPASS_READ_TIMEOUT,
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


# Status codes that mean "come back later".
TEMPORARY_STATUS_CODES = frozenset({500, 502, 503, 504})


@contextmanager
def ipv4_only(enabled):
    """Force the IPv4 address family for the duration of the block.

    Some networks publish IPv6 addresses for a host but cannot actually
    route IPv6 traffic. A request to such a host then hangs until it times
    out, even though IPv4 would have worked perfectly.

    `urllib3` resolves the address family per connection through
    `allowed_gai_family`, so swapping that function for the duration of the
    call is enough. The swap is restored afterwards, and it is scoped to
    this one integration.

    Note that the swap is process-wide while it is in effect, so it would
    also affect another thread making an HTTP request at the same moment.
    That is harmless here, because the only thing it changes is which
    address family is tried first, and this project serves requests
    synchronously.

    This is off by default: forcing IPv4 would break a network that is
    genuinely IPv6-only.
    """

    if not enabled:
        yield
        return

    original = urllib3_connection.allowed_gai_family

    urllib3_connection.allowed_gai_family = lambda: socket.AF_INET

    try:
        yield
    finally:
        urllib3_connection.allowed_gai_family = original


class OverpassClient:
    """Thin, synchronous HTTP client for the Overpass API."""

    def __init__(
        self,
        api_url=None,
        connect_timeout=None,
        read_timeout=None,
        user_agent=None,
        ipv4_only=None,
    ):
        self.api_url = api_url or OVERPASS_API_URL

        # `None` means "use the configured default", `0` would mean
        # "no timeout", so we must not use a truthiness check here.
        self.connect_timeout = (
            OVERPASS_CONNECT_TIMEOUT
            if connect_timeout is None
            else connect_timeout
        )

        self.read_timeout = (
            OVERPASS_READ_TIMEOUT
            if read_timeout is None
            else read_timeout
        )

        self.user_agent = user_agent or INTEGRATIONS_USER_AGENT

        self.ipv4_only = (
            OVERPASS_IPV4_ONLY if ipv4_only is None else ipv4_only
        )

    def fetch_elements(self, query):
        """Run an Overpass QL query and return the raw element list.

        A valid query that simply matches nothing returns an empty list.
        Every provider failure is raised as an integration exception.
        """

        response = self._send(query)

        payload = self._parse_json(response)

        return self._extract_elements(payload)

    def _send(self, query):
        """POST the query and return the response, or raise."""

        try:
            with ipv4_only(self.ipv4_only):
                response = requests.post(
                    self.api_url,
                    data={"data": query},
                    headers=self._build_headers(),
                    timeout=(
                        self.connect_timeout,
                        self.read_timeout,
                    ),
                )

        except requests.exceptions.Timeout as exc:
            # Covers both ConnectTimeout and ReadTimeout.
            logger.warning(
                "Overpass request timed out "
                "(connect=%ss, read=%ss).",
                self.connect_timeout,
                self.read_timeout,
            )

            raise IntegrationTimeoutError(
                "The places provider did not respond in time."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "Could not connect to the places provider at %s.",
                self.api_url,
            )

            raise IntegrationUnavailableError(
                "The places provider could not be reached."
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.exception(
                "Unexpected failure while calling the places provider."
            )

            raise IntegrationError(
                "The places provider request could not be completed."
            ) from exc

        self._raise_for_status(response)

        return response

    def _build_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _raise_for_status(self, response):
        """Translate a non-success status code into an exception."""

        if response.ok:
            return

        status_code = response.status_code

        retry_after = self._parse_retry_after(response)

        if status_code == 429:
            logger.warning(
                "Overpass rate limited the request (HTTP %s).",
                status_code,
            )

            raise IntegrationRateLimitError(
                "The places provider is rate limiting requests.",
                retry_after=retry_after,
            )

        if status_code in TEMPORARY_STATUS_CODES:
            logger.warning(
                "Overpass is temporarily unavailable (HTTP %s).",
                status_code,
            )

            raise IntegrationUnavailableError(
                "The places provider is temporarily unavailable.",
                retry_after=retry_after,
            )

        if 400 <= status_code < 500:
            logger.warning(
                "Overpass rejected the request (HTTP %s).",
                status_code,
            )

            raise IntegrationRequestError(
                "The places provider rejected the request."
            )

        logger.error(
            "Overpass returned an unexpected status code (HTTP %s).",
            status_code,
        )

        raise IntegrationError(
            "The places provider returned an unexpected response."
        )

    @staticmethod
    def _parse_retry_after(response):
        """Return the provider's ``Retry-After`` delay in seconds, if any.

        The header may also carry an HTTP-date. We do not need an exact
        deadline, so in that case we simply report no delay.
        """

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
            # `requests.exceptions.JSONDecodeError` derives from
            # `json.JSONDecodeError`, which derives from `ValueError`, so a
            # single `ValueError` clause covers every JSON decoding failure.
            logger.warning(
                "Overpass returned a response that is not valid JSON."
            )

            raise IntegrationResponseError(
                "The places provider returned an unreadable response."
            ) from exc

        if not isinstance(payload, dict):
            logger.warning(
                "Overpass returned an unexpected JSON structure "
                "(%s).",
                type(payload).__name__,
            )

            raise IntegrationResponseError(
                "The places provider returned an unexpected response."
            )

        return payload

    @staticmethod
    def _extract_elements(payload):
        elements = payload.get("elements")

        if elements is None:
            # Every successful Overpass response carries an `elements` key,
            # even when it is an empty list.
            logger.warning(
                "Overpass response did not contain an `elements` key."
            )

            raise IntegrationResponseError(
                "The places provider returned an unexpected response."
            )

        if not isinstance(elements, list):
            logger.warning(
                "Overpass returned an `elements` value that is not a list."
            )

            raise IntegrationResponseError(
                "The places provider returned an unexpected response."
            )

        return elements


__all__ = ["OverpassClient", "TEMPORARY_STATUS_CODES"]
