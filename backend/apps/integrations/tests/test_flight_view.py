"""
API tests for the flight link endpoint.

The endpoint is pure: it reads the trip and builds URLs, so these tests do
not need to mock any provider.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.trips.models import Trip


class TripFlightLinksApiTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="flyer@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Flyer",
        )

        self.other_user = user_model.objects.create_user(
            email="stranger@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Stranger",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Goa Break",
            destination="Goa",
            origin="Delhi",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 15),
            budget=Decimal("50000.00"),
            currency="INR",
            travelers=2,
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse(
            "trip-flights",
            kwargs={"trip_id": self.trip.id},
        )

    def test_returns_two_search_links(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]

        self.assertEqual(len(data["links"]), 2)
        self.assertEqual(
            [link["provider"] for link in data["links"]],
            ["google_flights", "kayak"],
        )

    def test_includes_the_trip_details(self):
        response = self.client.get(self.url)

        data = response.data["data"]

        self.assertEqual(data["origin"], "Delhi")
        self.assertEqual(data["destination"], "Goa")
        self.assertEqual(data["start_date"], "2026-11-10")
        self.assertEqual(data["end_date"], "2026-11-15")
        self.assertEqual(data["travelers"], 2)

    def test_a_trip_without_an_origin_returns_400(self):
        self.trip.origin = ""
        self.trip.save()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("origin", response.data["message"])

    def test_another_users_trip_is_not_found(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_a_missing_trip_is_not_found(self):
        url = reverse(
            "trip-flights",
            kwargs={"trip_id": uuid.uuid4()},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_the_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
