"""
Tests for the optional departure city stored on a trip.

`origin` is required only when a flight link is requested, so the API must
accept trips without one and expose whatever the user supplied.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.trips.models import Trip


class TripOriginApiTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="traveller@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Traveller",
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("trip")

        self.payload = {
            "title": "Goa Break",
            "destination": "Goa",
            "start_date": str(date.today() + timedelta(days=7)),
            "end_date": str(date.today() + timedelta(days=10)),
            "budget": "50000.00",
            "currency": "INR",
            "travelers": 2,
        }

    def test_a_trip_can_be_created_with_an_origin(self):
        response = self.client.post(
            self.url,
            {**self.payload, "origin": "Delhi"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["data"]["origin"], "Delhi")

    def test_the_origin_is_optional(self):
        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["data"]["origin"], "")

    def test_a_blank_origin_is_accepted(self):
        response = self.client.post(
            self.url,
            {**self.payload, "origin": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["data"]["origin"], "")

    def test_the_origin_is_trimmed(self):
        response = self.client.post(
            self.url,
            {**self.payload, "origin": "  New Delhi  "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["data"]["origin"],
            "New Delhi",
        )

    def test_an_overlong_origin_is_rejected(self):
        response = self.client.post(
            self.url,
            {**self.payload, "origin": "x" * 256},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_the_origin_can_be_updated(self):
        create_response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        trip_id = create_response.data["data"]["id"]

        response = self.client.patch(
            reverse("trip-detail", kwargs={"trip_id": trip_id}),
            {"origin": "Mumbai"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["origin"], "Mumbai")

        trip = Trip.objects.get(id=trip_id)

        self.assertEqual(trip.origin, "Mumbai")

    def test_existing_rows_default_to_an_empty_origin(self):
        trip = Trip.objects.create(
            user=self.user,
            title="Legacy Trip",
            destination="Jaipur",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            budget="30000.00",
            currency="INR",
            travelers=1,
        )

        trip.refresh_from_db()

        self.assertEqual(trip.origin, "")
