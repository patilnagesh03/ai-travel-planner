"""
API tests for the destination resolve endpoint.

This endpoint exists so the map does not have to duplicate the backend's
alias and state rules. It never calls an external provider.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class DestinationResolveApiTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="resolve@example.com",
            password="TestPass123!",
            first_name="Resolve",
            last_name="Tester",
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("place-resolve")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url, {"destination": "Jaipur"})

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_a_known_city_is_resolved_to_its_centre_and_box(self):
        response = self.client.get(
            self.url,
            {"destination": "Jaipur"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        data = response.data["data"]

        self.assertEqual(data["name"], "Jaipur")
        self.assertEqual(data["state"], "Rajasthan")
        self.assertAlmostEqual(data["latitude"], 26.915, places=3)
        self.assertAlmostEqual(data["longitude"], 75.795, places=3)
        self.assertEqual(data["bbox"]["south"], 26.8)
        self.assertEqual(data["bbox"]["east"], 75.87)

    def test_aliases_and_state_forms_are_accepted(self):
        for value in ("jpr", "Jaipur, Rajasthan", "Jaipur RJ"):
            with self.subTest(value=value):
                response = self.client.get(
                    self.url,
                    {"destination": value},
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(response.data["data"]["name"], "Jaipur")

    def test_an_unknown_destination_returns_a_clear_400(self):
        response = self.client.get(
            self.url,
            {"destination": "Kumbakonam"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("Kumbakonam", response.data["message"])

    def test_a_city_in_the_wrong_state_returns_a_clear_400(self):
        response = self.client.get(
            self.url,
            {"destination": "Jaipur, Kerala"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("Rajasthan", response.data["message"])

    def test_the_destination_is_required(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
