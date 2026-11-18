"""
Tests for the read-only interests endpoint.

The preferences screen needs the interest catalogue (id + name) to build its
selection UI, so this endpoint is part of the frontend contract.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.trips.models import Interest


class InterestListTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="traveller@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Traveller",
        )

        self.heritage = Interest.objects.create(name="Heritage")
        self.adventure = Interest.objects.create(name="Adventure")
        self.food = Interest.objects.create(name="Food & Drink")

        self.url = reverse("interest-list")

    def test_authenticated_user_gets_interests_by_name(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("message", response.data)

        names = [interest["name"] for interest in response.data["data"]]

        self.assertEqual(names, ["Adventure", "Food & Drink", "Heritage"])

    def test_interests_expose_string_ids_and_names(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        first = response.data["data"][0]

        self.assertEqual(
            set(first.keys()),
            {"id", "name"},
        )
        self.assertEqual(first["id"], str(self.adventure.id))

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_endpoint_is_read_only(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, {"name": "Shopping"})

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertFalse(Interest.objects.filter(name="Shopping").exists())
