"""
Regression tests for the itinerary app.

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

from backend.apps.itinerary.models import Itinerary, ItineraryItem
from backend.apps.trips.models import Trip


class ItineraryNotFoundTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="planner@example.com",
            password="TestPass123!",
            first_name="Itin",
            last_name="Planner",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Goa Trip",
            destination="Goa",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            budget=Decimal("30000.00"),
            currency="INR",
            travelers=2,
        )

        self.itinerary = Itinerary.objects.create(
            trip=self.trip,
            title="Goa Itinerary",
        )

        self.client.force_authenticate(user=self.user)

        self.missing_trip_id = uuid.uuid4()
        self.missing_itinerary_id = uuid.uuid4()

    def test_get_itinerary_for_a_missing_trip_returns_404(self):
        url = reverse(
            "itinerary",
            kwargs={"trip_id": self.missing_trip_id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_patch_itinerary_for_a_missing_trip_returns_404(self):
        url = reverse(
            "itinerary",
            kwargs={"trip_id": self.missing_trip_id},
        )

        response = self.client.patch(url, {"title": "New title"})

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_itinerary_for_a_missing_trip_returns_404(self):
        url = reverse(
            "itinerary",
            kwargs={"trip_id": self.missing_trip_id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_itinerary_for_another_users_trip_returns_404(self):
        user_model = get_user_model()

        other_user = user_model.objects.create_user(
            email="stranger@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Stranger",
        )

        self.client.force_authenticate(user=other_user)

        url = reverse(
            "itinerary",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_existing_itinerary_is_still_returned(self):
        url = reverse(
            "itinerary",
            kwargs={"trip_id": self.trip.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["title"],
            "Goa Itinerary",
        )


class ItineraryItemNotFoundTests(APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="planner@example.com",
            password="TestPass123!",
            first_name="Item",
            last_name="Planner",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Goa Trip",
            destination="Goa",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            budget=Decimal("30000.00"),
            currency="INR",
            travelers=2,
        )

        self.itinerary = Itinerary.objects.create(
            trip=self.trip,
            title="Goa Itinerary",
        )

        self.item = ItineraryItem.objects.create(
            itinerary=self.itinerary,
            date=self.trip.start_date,
            title="Visit Fort Aguada",
            order=1,
        )

        self.client.force_authenticate(user=self.user)

        self.missing_itinerary_id = uuid.uuid4()
        self.missing_item_id = uuid.uuid4()

    def test_list_items_for_a_missing_itinerary_returns_404(self):
        url = reverse(
            "itinerary-item-list-create",
            kwargs={"itinerary_id": self.missing_itinerary_id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_create_item_for_a_missing_itinerary_returns_404(self):
        url = reverse(
            "itinerary-item-list-create",
            kwargs={"itinerary_id": self.missing_itinerary_id},
        )

        response = self.client.post(
            url,
            {
                "date": str(self.trip.start_date),
                "title": "Visit Fort Aguada",
                "order": 1,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_patch_missing_item_returns_404(self):
        url = reverse(
            "itinerary-item-detail",
            kwargs={
                "itinerary_id": self.itinerary.id,
                "item_id": self.missing_item_id,
            },
        )

        response = self.client.patch(url, {"title": "New title"})

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_missing_item_returns_404(self):
        url = reverse(
            "itinerary-item-detail",
            kwargs={
                "itinerary_id": self.itinerary.id,
                "item_id": self.missing_item_id,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_existing_items_are_still_returned(self):
        url = reverse(
            "itinerary-item-list-create",
            kwargs={"itinerary_id": self.itinerary.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["title"],
            "Visit Fort Aguada",
        )

    def test_existing_item_can_still_be_updated(self):
        url = reverse(
            "itinerary-item-detail",
            kwargs={
                "itinerary_id": self.itinerary.id,
                "item_id": self.item.id,
            },
        )

        response = self.client.patch(url, {"title": "Visit Basilica"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.item.refresh_from_db()

        self.assertEqual(self.item.title, "Visit Basilica")
