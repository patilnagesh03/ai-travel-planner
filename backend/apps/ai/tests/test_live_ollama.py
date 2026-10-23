"""
A live test against a real, running Ollama server.

This test is SKIPPED by default. It needs a real model, so it only runs
when you explicitly ask for it::

    # Windows PowerShell
    $env:OLLAMA_LIVE_TEST = "1"
    python manage.py test backend.apps.ai.tests.test_live_ollama

    # Linux / macOS
    OLLAMA_LIVE_TEST=1 python manage.py test \
        backend.apps.ai.tests.test_live_ollama

The places provider is mocked in this test. The Overpass integration has
its own live test, and this one is about the AI path. The model itself is
real.

The test runs against Django's throwaway test database, so it never
touches your development data.
"""

import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from backend.apps.ai.clients import OllamaClient
from backend.apps.ai.config import OLLAMA_MODEL
from backend.apps.ai.services import ItineraryGenerationService
from backend.apps.integrations.schemas import Place, PlaceCategory
from backend.apps.itinerary.models import Itinerary, ItineraryItem
from backend.apps.trips.models import Trip


LIVE_TEST_ENABLED = os.environ.get("OLLAMA_LIVE_TEST") == "1"


def make_place(source_id="node/1", name="Cubbon Park"):
    return Place(
        source="openstreetmap",
        source_id=source_id,
        name=name,
        category=PlaceCategory.ATTRACTION,
        latitude=12.9763,
        longitude=77.6033,
        address="MG Road, Bengaluru",
        opening_hours=None,
    )


class LiveOllamaTests(TestCase):

    def setUp(self):
        if not LIVE_TEST_ENABLED:
            self.skipTest(
                "Live Ollama test is disabled. "
                "Set OLLAMA_LIVE_TEST=1 to run it."
            )

        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="live@example.com",
            password="TestPass123!",
            first_name="Live",
            last_name="Tester",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Bengaluru Getaway",
            destination="Bengaluru",
            start_date=timezone.now().date() + timedelta(days=7),
            end_date=timezone.now().date() + timedelta(days=8),
            budget=Decimal("40000.00"),
            currency="INR",
            travelers=2,
        )

        self.places = [
            make_place("node/1", "Cubbon Park"),
            make_place("node/2", "Vidhana Soudha"),
            make_place("node/3", "Karnataka Government Museum"),
            make_place("node/4", "Lalbagh Palace"),
        ]

    def test_the_configured_model_is_installed(self):
        models = OllamaClient().list_models()

        self.assertIn(
            OLLAMA_MODEL,
            models,
            "The configured model '{0}' is not installed. "
            "Pull it with: ollama pull {0}".format(OLLAMA_MODEL),
        )

    def test_a_real_generation_produces_a_validated_plan(self):
        result = ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            dry_run=True,
        )

        plan = result["plan"]

        self.assertTrue(plan.title)
        self.assertTrue(plan.days)
        self.assertTrue(plan.item_count)

        trip_dates = {
            self.trip.start_date,
            self.trip.start_date + timedelta(days=1),
        }

        for day in plan.days:
            self.assertIn(day.date, trip_dates)

            for item in day.items:
                # Every activity must point at a place we offered, and the
                # coordinates must be ours.
                self.assertIn(
                    item.place_source_id,
                    [place.source_id for place in self.places],
                )

                self.assertIsNotNone(item.latitude)
                self.assertIsNotNone(item.longitude)

    def test_a_real_generation_persists_a_valid_itinerary(self):
        result = ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            dry_run=False,
        )

        itinerary = Itinerary.objects.get(id=result["itinerary_id"])

        items = list(
            ItineraryItem.objects
            .filter(itinerary=itinerary)
            .order_by("date", "order")
        )

        self.assertTrue(items)

        for item in items:
            self.assertGreaterEqual(item.date, self.trip.start_date)
            self.assertLessEqual(item.date, self.trip.end_date)
            self.assertIsNotNone(item.latitude)
            self.assertIsNotNone(item.longitude)

        # The database enforces a unique order per day.
        for day in set(item.date for item in items):
            orders = [
                item.order
                for item in items
                if item.date == day
            ]

            self.assertEqual(
                orders,
                list(range(1, len(orders) + 1)),
            )

    def test_an_invented_place_is_never_persisted(self):
        # A model that invents a venue must not end up in the database.
        from unittest.mock import patch

        hostile = (
            '{"title": "Hostile Plan", "description": "x", "days": ['
            '{"items": [{"title": "Invented venue", "description": "x", '
            '"start_time": "19:00", "end_time": "20:00", '
            '"activity_type": "restaurant", "place": "node/999999999"}]}]}'
        )

        with patch(
            "backend.apps.ai.services.itinerary_generation_service."
            "OllamaClient.generate",
            return_value=hostile,
        ):
            result = ItineraryGenerationService.generate(
                trip=self.trip,
                places=self.places,
                dry_run=False,
            )

        itinerary = Itinerary.objects.get(id=result["itinerary_id"])

        self.assertEqual(
            ItineraryItem.objects.filter(itinerary=itinerary).count(),
            0,
        )
