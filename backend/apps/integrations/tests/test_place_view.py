"""
API tests for the place discovery endpoints.

The provider is always mocked, so these tests never touch the public
Overpass instance.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.integrations.exceptions import (
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)
from backend.apps.integrations.tests.helpers import CacheClearingMixin
from backend.apps.trips.models import Trip


POST_TARGET = "backend.apps.integrations.clients.overpass_client.requests.post"


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


SAMPLE_PAYLOAD = {
    "version": 0.6,
    "generator": "Overpass API",
    "elements": [
        {
            "type": "node",
            "id": 1,
            "lat": 12.9763,
            "lon": 77.6033,
            "tags": {"name": "Cubbon Park", "leisure": "park"},
        },
        {
            "type": "way",
            "id": 2,
            "center": {"lat": 12.9719, "lon": 77.5946},
            "tags": {"name": "Vidhana Soudha", "tourism": "attraction"},
        },
    ],
}


class PlaceSearchApiTests(CacheClearingMixin, APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="traveller@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Traveller",
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("place-search")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_search_by_destination_returns_normalized_places(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ):
            response = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(response.data["success"])

        places = response.data["data"]

        self.assertEqual(len(places), 2)

        self.assertEqual(places[0]["name"], "Cubbon Park")
        self.assertEqual(places[0]["category"], "park")
        self.assertEqual(places[0]["source"], "openstreetmap")
        self.assertEqual(places[0]["source_id"], "node/1")
        self.assertIsNone(places[0]["address"])

        self.assertEqual(places[1]["source_id"], "way/2")
        self.assertEqual(places[1]["category"], "attraction")

    def test_search_by_coordinates_uses_a_radius(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_post:
            response = self.client.get(
                self.url,
                {"latitude": 12.9716, "longitude": 77.5946},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        query = mocked_post.call_args.kwargs["data"]["data"]

        self.assertIn("(12.", query)

    def test_categories_are_passed_to_the_provider(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_post:
            self.client.get(
                self.url,
                {
                    "destination": "Bengaluru",
                    "categories": "museum,cafe",
                },
            )

        query = mocked_post.call_args.kwargs["data"]["data"]

        self.assertIn('nwr["tourism"="museum"]', query)
        self.assertIn('nwr["amenity"="cafe"]', query)
        self.assertNotIn('nwr["leisure"="park"]', query)

    def test_limit_above_the_application_maximum_is_rejected(self):
        # The API rejects an oversized limit outright rather than silently
        # clamping it, so the caller is told what the maximum is.
        response = self.client.get(
            self.url,
            {"destination": "Bengaluru", "limit": 999},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_limit_within_the_maximum_is_forwarded(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_post:
            self.client.get(
                self.url,
                {"destination": "Bengaluru", "limit": 7},
            )

        query = mocked_post.call_args.kwargs["data"]["data"]

        self.assertIn("out center 7;", query)

    def test_missing_parameters_are_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unsupported_destination_is_rejected(self):
        response = self.client.get(
            self.url,
            {"destination": "Kumbakonam"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("Kumbakonam", response.data["message"])

    def test_unknown_category_is_rejected(self):
        response = self.client.get(
            self.url,
            {
                "destination": "Bengaluru",
                "categories": "not-a-category",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_partial_coordinates_are_rejected(self):
        response = self.client.get(
            self.url,
            {"latitude": 12.9716},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_rate_limiting_returns_429_with_retry_after(self):
        response = Mock()
        response.status_code = 429
        response.ok = False
        response.headers = {"Retry-After": "90"}

        with patch(POST_TARGET, return_value=response):
            result = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(
            result.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        self.assertEqual(result["Retry-After"], "90")

    def test_provider_unavailable_returns_503(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=503),
        ):
            response = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def test_provider_timeout_returns_503(self):
        import requests

        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.ReadTimeout("timed out"),
        ):
            response = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def test_provider_rejecting_the_request_returns_400(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=400),
        ):
            response = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_provider_response_returns_502(self):
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.headers = {}
        response.json.side_effect = ValueError("not json")

        with patch(POST_TARGET, return_value=response):
            result = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(
            result.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

    def test_provider_errors_do_not_leak_details(self):
        response = Mock()
        response.status_code = 400
        response.ok = False
        response.headers = {}
        response.json.return_value = {
            "remark": "runtime error: Error: line 3: parse error",
        }

        with patch(POST_TARGET, return_value=response):
            result = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(
            result.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertNotIn("parse error", result.data["message"])


class TripPlaceSearchApiTests(CacheClearingMixin, APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="owner@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Owner",
        )

        self.other_user = user_model.objects.create_user(
            email="stranger@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Stranger",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Karnataka Getaway",
            destination="Bengaluru",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            budget=Decimal("50000.00"),
            currency="INR",
            travelers=2,
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse(
            "trip-places",
            kwargs={"trip_id": self.trip.id},
        )

    def test_trip_places_use_the_trip_destination(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_post:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        query = mocked_post.call_args.kwargs["data"]["data"]

        self.assertIn("(12.83,77.45,13.15,77.75)", query)

    def test_query_parameter_cannot_override_the_trip_destination(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ) as mocked_post:
            self.client.get(self.url, {"destination": "Mumbai"})

        query = mocked_post.call_args.kwargs["data"]["data"]

        self.assertNotIn("(18.893,72.785,19.276,72.99)", query)

    def test_another_users_trip_is_not_found(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_missing_trip_is_not_found(self):
        url = reverse(
            "trip-places",
            kwargs={"trip_id": uuid.uuid4()},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_trip_with_unsupported_destination_is_rejected(self):
        self.trip.destination = "Kumbakonam"
        self.trip.save()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("Kumbakonam", response.data["message"])

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class JwtAuthenticationTests(CacheClearingMixin, APITestCase):
    """The place endpoints must work with a real Bearer token."""

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="jwt@example.com",
            password="TestPass123!",
            first_name="Jwt",
            last_name="User",
        )

        self.url = reverse("place-search")

    def test_a_real_access_token_is_accepted(self):
        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer {token}".format(
                token=refresh.access_token,
            )
        )

        with patch(
            POST_TARGET,
            return_value=build_response(payload=SAMPLE_PAYLOAD),
        ):
            response = self.client.get(
                self.url,
                {"destination": "Bengaluru"},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_a_missing_token_is_rejected(self):
        response = self.client.get(
            self.url,
            {"destination": "Bengaluru"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class SupportedDestinationsApiTests(CacheClearingMixin, APITestCase):
    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="browser@example.com",
            password="TestPass123!",
            first_name="Place",
            last_name="Browser",
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("place-destinations")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_supported_destinations_are_listed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(response.data["success"])

        names = [
            destination["name"]
            for destination in response.data["data"]
        ]

        self.assertIn("Mumbai", names)
        self.assertIn("Bengaluru", names)
