"""
Regression tests for the trips app.

These lock in the behaviour that a missing resource returns a 404, not a
generic 500.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.trips.models import Trip


class TripNotFoundTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="traveller@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Traveller",
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

        self.missing_id = uuid.uuid4()

    def test_get_missing_trip_returns_404(self):
        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.missing_id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_patch_missing_trip_returns_404(self):
        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.missing_id},
        )

        response = self.client.patch(url, {"title": "New title"})

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_missing_trip_returns_404(self):
        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.missing_id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_another_users_trip_returns_404(self):
        user_model = get_user_model()

        other_user = user_model.objects.create_user(
            email="stranger@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Stranger",
        )

        self.client.force_authenticate(user=other_user)

        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_existing_trip_is_still_returned(self):
        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Karnataka Getaway")

    def test_existing_trip_can_still_be_updated(self):
        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.patch(url, {"title": "Renamed Trip"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.trip.refresh_from_db()

        self.assertEqual(self.trip.title, "Renamed Trip")

    def test_existing_trip_can_still_be_deleted(self):
        url = reverse(
            "trip-detail",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Trip.objects.filter(id=self.trip.id).exists()
        )


class TripPreferenceNotFoundTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="planner@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Planner",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Kerala Trip",
            destination="Kochi",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            budget=Decimal("40000.00"),
            currency="INR",
            travelers=1,
        )

        self.client.force_authenticate(user=self.user)

        self.missing_id = uuid.uuid4()

    def test_preferences_for_a_missing_trip_return_404(self):
        url = reverse(
            "trip-preferences",
            kwargs={"trip_id": self.missing_id},
        )

        for method in (self.client.get, self.client.post, self.client.patch):
            response = method(url)

            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_delete_preferences_for_a_missing_trip_returns_404(self):
        url = reverse(
            "trip-preferences",
            kwargs={"trip_id": self.missing_id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_preferences_that_do_not_exist_yet_return_404(self):
        url = reverse(
            "trip-preferences",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertIn(
            "not found",
            response.data["message"].lower(),
        )
