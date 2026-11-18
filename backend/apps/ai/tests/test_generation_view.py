"""
API tests for the AI itinerary generation endpoint.

Both the model and the places provider are mocked, so the tests never need
a running Ollama server and never touch the public Overpass instance.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.ai.exceptions import (
    AIModelError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseError,
    AIValidationError,
)
from backend.apps.integrations.exceptions import UnsupportedDestinationError
from backend.apps.integrations.schemas import Place, PlaceCategory
from backend.apps.itinerary.models import Itinerary, ItineraryItem
from backend.apps.trips.models import Trip


CLIENT_TARGET = (
    "backend.apps.ai.services.itinerary_generation_service.OllamaClient"
)

PLACES_TARGET = (
    "backend.apps.ai.services.itinerary_generation_service."
    "ItineraryGenerationService.collect_places"
)


def make_place(source_id="node/1", name="Cubbon Park"):
    return Place(
        source="openstreetmap",
        source_id=source_id,
        name=name,
        category=PlaceCategory.PARK,
        latitude=12.9763,
        longitude=77.6033,
        address="MG Road, Bengaluru",
        opening_hours=None,
    )


def raw_plan(days=2):
    return {
        "title": "Bengaluru Getaway",
        "description": "A couple of days in the city.",
        "days": [
            {
                "items": [
                    {
                        "title": "Visit Cubbon Park",
                        "description": "A green park.",
                        "start_time": "09:00",
                        "end_time": "11:00",
                        "activity_type": "attraction",
                        "place": "node/1",
                    },
                ],
            }
            for _ in range(days)
        ],
    }


class ItineraryGenerationApiTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="generator@example.com",
            password="TestPass123!",
            first_name="Gene",
            last_name="Rator",
        )

        self.other_user = user_model.objects.create_user(
            email="stranger@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Stranger",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Bengaluru Getaway",
            destination="Bengaluru",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            budget=Decimal("40000.00"),
            currency="INR",
            travelers=2,
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse(
            "itinerary-generate",
            kwargs={"trip_id": self.trip.id},
        )

        self.places = [make_place()]

    def generate(self, completion=None, body=None):
        """Run the endpoint with the model and provider mocked."""

        with patch(PLACES_TARGET, return_value=self.places):
            with patch(CLIENT_TARGET) as mocked_client:
                mocked_client.return_value.generate.return_value = (
                    completion
                    if completion is not None
                    else json.dumps(raw_plan())
                )

                return self.client.post(
                    self.url,
                    body if body is not None else {},
                )

    # ------------------------------------------------------------------
    # Authentication and ownership
    # ------------------------------------------------------------------

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_another_users_trip_returns_404(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ------------------------------------------------------------------
    # Successful generation
    # ------------------------------------------------------------------

    def test_generation_persists_and_returns_the_plan(self):
        response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["persisted"])

        plan = response.data["data"]["plan"]

        self.assertEqual(plan["title"], "Bengaluru Getaway")
        self.assertEqual(len(plan["days"]), 2)

        self.assertEqual(
            Itinerary.objects.filter(trip=self.trip).count(),
            1,
        )

    def test_generated_items_carry_the_place_details(self):
        response = self.generate()

        item = response.data["data"]["plan"]["days"][0]["items"][0]

        self.assertEqual(item["place"]["name"], "Cubbon Park")
        self.assertEqual(item["place"]["source_id"], "node/1")
        self.assertAlmostEqual(item["place"]["latitude"], 12.9763)

    def test_dry_run_returns_a_plan_without_saving_it(self):
        response = self.generate(body={"dry_run": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(response.data["data"]["persisted"])
        self.assertIsNone(response.data["data"]["itinerary_id"])

        self.assertEqual(
            Itinerary.objects.filter(trip=self.trip).count(),
            0,
        )

    def test_an_existing_itinerary_is_not_replaced_by_default(self):
        Itinerary.objects.create(
            trip=self.trip,
            title="Existing Itinerary",
        )

        response = self.generate()

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertEqual(
            Itinerary.objects.get(trip=self.trip).title,
            "Existing Itinerary",
        )

    def test_an_existing_itinerary_is_replaced_when_asked(self):
        Itinerary.objects.create(
            trip=self.trip,
            title="Existing Itinerary",
        )

        response = self.generate(body={"replace": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            Itinerary.objects.get(trip=self.trip).title,
            "Bengaluru Getaway",
        )

    # ------------------------------------------------------------------
    # Failure modes
    # ------------------------------------------------------------------

    def test_unsupported_destination_returns_400(self):
        with patch(
            PLACES_TARGET,
            side_effect=UnsupportedDestinationError(
                "'Coorg' is not a destination we can search."
            ),
        ):
            with patch(CLIENT_TARGET):
                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("Coorg", response.data["message"])

    def test_provider_unavailable_returns_503(self):
        with patch(
            PLACES_TARGET,
            side_effect=AIProviderUnavailableError("unavailable"),
        ):
            with patch(CLIENT_TARGET):
                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def test_model_timeout_returns_504(self):
        with patch(PLACES_TARGET, return_value=self.places):
            with patch(CLIENT_TARGET) as mocked_client:
                mocked_client.return_value.generate.side_effect = (
                    AIProviderTimeoutError("too slow")
                )

                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_504_GATEWAY_TIMEOUT,
        )

    def test_missing_model_returns_503(self):
        with patch(PLACES_TARGET, return_value=self.places):
            with patch(CLIENT_TARGET) as mocked_client:
                mocked_client.return_value.generate.side_effect = (
                    AIModelError(
                        "The configured AI model is not available. "
                        "Pull it first with `ollama pull`."
                    )
                )

                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        self.assertIn("ollama pull", response.data["message"])

    def test_unusable_model_output_returns_502(self):
        with patch(PLACES_TARGET, return_value=self.places):
            with patch(CLIENT_TARGET) as mocked_client:
                mocked_client.return_value.generate.return_value = (
                    "this is not json at all"
                )

                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

    def test_a_plan_that_fails_validation_returns_502(self):
        with patch(PLACES_TARGET, return_value=self.places):
            with patch(CLIENT_TARGET) as mocked_client:
                mocked_client.return_value.generate.return_value = (
                    json.dumps({"title": "Trip"})
                )

                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

    def test_provider_errors_do_not_leak_model_output(self):
        with patch(PLACES_TARGET, return_value=self.places):
            with patch(CLIENT_TARGET) as mocked_client:
                mocked_client.return_value.generate.return_value = (
                    "SENSITIVE MODEL OUTPUT THAT MUST NOT LEAK"
                )

                response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

        self.assertNotIn(
            "SENSITIVE MODEL OUTPUT",
            json.dumps(response.data),
        )


class AIStatusApiTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="status@example.com",
            password="TestPass123!",
            first_name="Status",
            last_name="Checker",
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("ai-status")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_status_reports_the_configured_provider(self):
        with patch(
            "backend.apps.ai.views.generation_view.OllamaClient"
        ) as mocked_client:
            mocked_client.return_value.is_available.return_value = True

            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["data"]["provider"], "ollama")
        self.assertTrue(response.data["data"]["available"])
