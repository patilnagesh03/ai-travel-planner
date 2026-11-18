"""
Unit tests for the Overpass HTTP client.

Every test mocks `requests.post`, so the suite never touches the public
Overpass instance and never depends on network availability.
"""

import socket
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase
from urllib3.util import connection as urllib3_connection

from backend.apps.integrations.clients import OverpassClient
from backend.apps.integrations.clients.overpass_client import ipv4_only
from backend.apps.integrations.config import OVERPASS_IPV4_ONLY
from backend.apps.integrations.exceptions import (
    IntegrationError,
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


POST_TARGET = "backend.apps.integrations.clients.overpass_client.requests.post"


def build_response(status_code=200, payload=None, headers=None):
    """Build a stand-in for `requests.Response`."""

    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


class Ipv4OnlyTests(SimpleTestCase):
    """The IPv4 fallback must be scoped and always restored."""

    def test_disabled_leaves_the_address_family_untouched(self):
        original = urllib3_connection.allowed_gai_family

        with ipv4_only(False):
            self.assertIs(
                urllib3_connection.allowed_gai_family,
                original,
            )

    def test_enabled_forces_ipv4_and_restores_the_original(self):
        original = urllib3_connection.allowed_gai_family

        with ipv4_only(True):
            self.assertEqual(
                urllib3_connection.allowed_gai_family(),
                socket.AF_INET,
            )

        self.assertIs(
            urllib3_connection.allowed_gai_family,
            original,
        )

    def test_the_original_is_restored_after_an_exception(self):
        original = urllib3_connection.allowed_gai_family

        with self.assertRaises(ValueError):
            with ipv4_only(True):
                raise ValueError("boom")

        self.assertIs(
            urllib3_connection.allowed_gai_family,
            original,
        )

    def test_client_defaults_to_the_configured_value(self):
        client = OverpassClient()

        self.assertEqual(
            client.ipv4_only,
            OVERPASS_IPV4_ONLY,
        )

    def test_client_accepts_an_explicit_override(self):
        client = OverpassClient(ipv4_only=True)

        self.assertTrue(client.ipv4_only)

    def test_the_client_applies_the_setting_around_the_request(self):
        response = build_response(payload={"elements": []})

        original = urllib3_connection.allowed_gai_family

        with patch(POST_TARGET, return_value=response):
            client = OverpassClient(ipv4_only=True)
            client.fetch_elements("[out:json];out 1;")

        self.assertIs(
            urllib3_connection.allowed_gai_family,
            original,
        )


class OverpassClientTests(SimpleTestCase):

    def setUp(self):
        self.client = OverpassClient()
        self.query = "[out:json];node(1,2,3,4);out 1;"

    # ------------------------------------------------------------------
    # Successful responses
    # ------------------------------------------------------------------

    def test_successful_response_returns_elements(self):
        payload = {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 12.97,
                    "lon": 77.59,
                    "tags": {"name": "Test Park"},
                },
            ],
        }

        with patch(POST_TARGET, return_value=build_response(payload=payload)):
            elements = self.client.fetch_elements(self.query)

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["id"], 1)

    def test_successful_response_with_no_results_returns_empty_list(self):
        # A valid query that matches nothing is NOT an error.
        payload = {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [],
        }

        with patch(POST_TARGET, return_value=build_response(payload=payload)):
            elements = self.client.fetch_elements(self.query)

        self.assertEqual(elements, [])

    def test_request_uses_expected_method_headers_body_and_timeouts(self):
        response = build_response(payload={"elements": []})

        with patch(POST_TARGET, return_value=response) as mocked_post:
            self.client.fetch_elements(self.query)

        mocked_post.assert_called_once()

        kwargs = mocked_post.call_args.kwargs

        self.assertEqual(
            kwargs["data"],
            {"data": self.query},
        )

        self.assertEqual(
            kwargs["headers"]["User-Agent"],
            self.client.user_agent,
        )

        self.assertEqual(
            kwargs["headers"]["Accept"],
            "application/json",
        )

        self.assertEqual(
            kwargs["timeout"],
            (
                self.client.connect_timeout,
                self.client.read_timeout,
            ),
        )

    def test_user_agent_identifies_the_application(self):
        self.assertIn("AITravelPlanner", self.client.user_agent)

    # ------------------------------------------------------------------
    # Provider failures
    # ------------------------------------------------------------------

    def test_http_400_raises_integration_request_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=400),
        ):
            with self.assertRaises(IntegrationRequestError):
                self.client.fetch_elements(self.query)

    def test_http_429_raises_integration_rate_limit_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=429),
        ):
            with self.assertRaises(IntegrationRateLimitError):
                self.client.fetch_elements(self.query)

    def test_http_429_captures_retry_after_header(self):
        response = build_response(
            status_code=429,
            headers={"Retry-After": "120"},
        )

        with patch(POST_TARGET, return_value=response):
            with self.assertRaises(IntegrationRateLimitError) as ctx:
                self.client.fetch_elements(self.query)

        self.assertEqual(ctx.exception.retry_after, 120)

    def test_http_429_with_invalid_retry_after_header(self):
        response = build_response(
            status_code=429,
            headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        )

        with patch(POST_TARGET, return_value=response):
            with self.assertRaises(IntegrationRateLimitError) as ctx:
                self.client.fetch_elements(self.query)

        self.assertIsNone(ctx.exception.retry_after)

    def test_http_503_raises_integration_unavailable_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=503),
        ):
            with self.assertRaises(IntegrationUnavailableError):
                self.client.fetch_elements(self.query)

    def test_http_504_raises_integration_unavailable_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=504),
        ):
            with self.assertRaises(IntegrationUnavailableError):
                self.client.fetch_elements(self.query)

    def test_http_502_raises_integration_unavailable_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=502),
        ):
            with self.assertRaises(IntegrationUnavailableError):
                self.client.fetch_elements(self.query)

    def test_unexpected_status_code_raises_integration_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=302),
        ):
            with self.assertRaises(IntegrationError):
                self.client.fetch_elements(self.query)

    # ------------------------------------------------------------------
    # Transport failures
    # ------------------------------------------------------------------

    def test_read_timeout_raises_integration_timeout_error(self):
        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.ReadTimeout("timed out"),
        ):
            with self.assertRaises(IntegrationTimeoutError):
                self.client.fetch_elements(self.query)

    def test_connect_timeout_raises_integration_timeout_error(self):
        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.ConnectTimeout("timed out"),
        ):
            with self.assertRaises(IntegrationTimeoutError):
                self.client.fetch_elements(self.query)

    def test_connection_error_raises_integration_unavailable_error(self):
        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with self.assertRaises(IntegrationUnavailableError):
                self.client.fetch_elements(self.query)

    def test_unexpected_request_exception_raises_integration_error(self):
        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.TooManyRedirects("loop"),
        ):
            with self.assertRaises(IntegrationError):
                self.client.fetch_elements(self.query)

    # ------------------------------------------------------------------
    # Malformed responses
    # ------------------------------------------------------------------

    def test_invalid_json_raises_integration_response_error(self):
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.headers = {}
        response.json.side_effect = ValueError("not json")

        with patch(POST_TARGET, return_value=response):
            with self.assertRaises(IntegrationResponseError):
                self.client.fetch_elements(self.query)

    def test_response_that_is_not_an_object_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=["not", "a", "dict"]),
        ):
            with self.assertRaises(IntegrationResponseError):
                self.client.fetch_elements(self.query)

    def test_missing_elements_key_raises_integration_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload={"version": 0.6}),
        ):
            with self.assertRaises(IntegrationResponseError):
                self.client.fetch_elements(self.query)

    def test_elements_that_is_not_a_list_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload={"elements": "nope"}),
        ):
            with self.assertRaises(IntegrationResponseError):
                self.client.fetch_elements(self.query)

    # ------------------------------------------------------------------
    # Information leakage
    # ------------------------------------------------------------------

    def test_exception_messages_do_not_leak_provider_bodies(self):
        response = build_response(
            status_code=400,
            payload={"remark": "runtime error: query syntax error"},
        )

        with patch(POST_TARGET, return_value=response):
            with self.assertRaises(IntegrationRequestError) as ctx:
                self.client.fetch_elements(self.query)

        message = str(ctx.exception)

        self.assertNotIn("runtime error", message)
        self.assertNotIn("syntax error", message)
