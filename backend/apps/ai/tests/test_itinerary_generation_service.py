"""
Tests for the itinerary generation service.

The important behaviour here is the validation: a model must not be able to
invent a date, a place or a coordinate.
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import TestCase

from backend.apps.ai.exceptions import AIValidationError
from backend.apps.ai.services import (
    ItineraryExistsError,
    ItineraryGenerationService,
)
from backend.apps.ai.services.prompt_service import PromptService
from backend.apps.integrations.schemas import Place, PlaceCategory
from backend.apps.itinerary.enums import ActivityType
from backend.apps.itinerary.models import Itinerary, ItineraryItem
from backend.apps.trips.models import Trip


class FakeOllamaClient:
    """Stands in for the Ollama client."""

    def __init__(self, completion):
        self.completion = completion
        self.prompts = []

    def generate(self, prompt, system=None):
        self.prompts.append((prompt, system))

        return self.completion


def make_place(source_id="node/1", name="Cubbon Park", category=None):
    return Place(
        source="openstreetmap",
        source_id=source_id,
        name=name,
        category=category or PlaceCategory.PARK,
        latitude=12.9763,
        longitude=77.6033,
        address="MG Road, Bengaluru",
        opening_hours=None,
    )


def raw_plan(days=1, place_id="node/1", **item_overrides):
    item = {
        "title": "Visit Cubbon Park",
        "description": "A green park in the heart of the city.",
        "start_time": "09:00",
        "end_time": "11:00",
        "activity_type": "attraction",
        "place": place_id,
    }

    item.update(item_overrides)

    return {
        "title": "Bengaluru Getaway",
        "description": "A couple of days in the city.",
        "days": [
            {"items": [dict(item) for _ in range(1)]}
            for _ in range(days)
        ],
    }


class PromptServiceTests(TestCase):

    def setUp(self):
        self.trip = Trip.objects.create(
            user=self._make_user(),
            title="Bengaluru Getaway",
            destination="Bengaluru",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 3),
            budget=Decimal("40000.00"),
            currency="INR",
            travelers=2,
        )

    def _make_user(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            email="prompt@example.com",
            password="TestPass123!",
            first_name="Prompt",
            last_name="Tester",
        )

    def test_trip_length_counts_both_end_days(self):
        self.assertEqual(
            PromptService.trip_length(self.trip),
            3,
        )

    def test_prompt_includes_the_trip_details(self):
        prompt = PromptService.build_prompt(
            trip=self.trip,
            places=[make_place()],
        )

        self.assertIn("Bengaluru Getaway", prompt)
        self.assertIn("Bengaluru", prompt)
        self.assertIn("2026-11-01", prompt)
        self.assertIn("2026-11-03", prompt)
        self.assertIn("3 day(s)", prompt)

    def test_prompt_lists_the_places_with_their_stable_ids(self):
        prompt = PromptService.build_prompt(
            trip=self.trip,
            places=[make_place()],
        )

        self.assertIn("node/1", prompt)
        self.assertIn("Cubbon Park", prompt)

    def test_prompt_tells_the_model_not_to_invent_places(self):
        prompt = PromptService.build_prompt(
            trip=self.trip,
            places=[make_place()],
        )

        self.assertIn("Only use places from the list above", prompt)
        self.assertIn("Do not include coordinates", prompt)
        self.assertIn("Do not include dates", prompt)

    def test_prompt_handles_a_trip_with_no_places(self):
        prompt = PromptService.build_prompt(
            trip=self.trip,
            places=[],
        )

        self.assertIn("no places were found", prompt)

    def test_items_per_day_follow_the_pace(self):
        self.assertEqual(
            PromptService.items_per_day("slow"),
            3,
        )
        self.assertEqual(
            PromptService.items_per_day("moderate"),
            4,
        )
        self.assertEqual(
            PromptService.items_per_day("fast"),
            6,
        )


class PlanValidationTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.trip = Trip.objects.create(
            user=get_user_model().objects.create_user(
                email="validator@example.com",
                password="TestPass123!",
                first_name="Valid",
                last_name="Ator",
            ),
            title="Bengaluru Getaway",
            destination="Bengaluru",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 3),
            budget=Decimal("40000.00"),
            currency="INR",
            travelers=2,
        )

        self.places = [
            make_place("node/1", "Cubbon Park"),
            make_place("node/2", "Vidhana Soudha", PlaceCategory.ATTRACTION),
        ]

    def validate(self, raw):
        return ItineraryGenerationService.validate_plan(
            raw_plan=raw,
            trip=self.trip,
            places=self.places,
        )

    def test_dates_are_assigned_by_us_not_the_model(self):
        raw = raw_plan(days=3)
        raw["days"][0]["date"] = "1999-01-01"
        raw["days"][1]["date"] = "2030-12-31"

        plan = self.validate(raw)

        self.assertEqual(
            [day.date for day in plan.days],
            [
                date(2026, 11, 1),
                date(2026, 11, 2),
                date(2026, 11, 3),
            ],
        )

    def test_coordinates_come_from_our_own_place_data(self):
        raw = raw_plan(days=1)
        raw["days"][0]["items"][0]["latitude"] = 1.234
        raw["days"][0]["items"][0]["longitude"] = 5.678

        plan = self.validate(raw)

        item = plan.days[0].items[0]

        self.assertAlmostEqual(item.latitude, 12.9763)
        self.assertAlmostEqual(item.longitude, 77.6033)

    def test_an_activity_referencing_an_unknown_place_is_dropped(self):
        raw = raw_plan(days=1, place_id="node/does-not-exist")

        plan = self.validate(raw)

        self.assertEqual(plan.item_count, 0)

    def test_an_activity_without_a_place_reference_is_dropped(self):
        raw = raw_plan(days=1)
        del raw["days"][0]["items"][0]["place"]

        plan = self.validate(raw)

        self.assertEqual(plan.item_count, 0)

    def test_an_activity_without_a_title_is_dropped(self):
        raw = raw_plan(days=1)
        raw["days"][0]["items"][0]["title"] = "   "

        plan = self.validate(raw)

        self.assertEqual(plan.item_count, 0)

    def test_an_unknown_activity_type_falls_back_to_other(self):
        raw = raw_plan(days=1, activity_type="teleportation")

        plan = self.validate(raw)

        self.assertEqual(
            plan.days[0].items[0].activity_type,
            ActivityType.OTHER,
        )

    def test_a_valid_activity_type_is_kept(self):
        raw = raw_plan(days=1, activity_type="attraction")

        plan = self.validate(raw)

        self.assertEqual(
            plan.days[0].items[0].activity_type,
            ActivityType.ATTRACTION,
        )

    def test_reversed_times_are_swapped(self):
        raw = raw_plan(days=1, start_time="11:00", end_time="09:00")

        plan = self.validate(raw)

        item = plan.days[0].items[0]

        self.assertEqual(item.start_time, datetime(2026, 1, 1, 9, 0).time())
        self.assertEqual(item.end_time, datetime(2026, 1, 1, 11, 0).time())

    def test_unparseable_times_become_none(self):
        raw = raw_plan(days=1, start_time="half past nine")

        plan = self.validate(raw)

        self.assertIsNone(plan.days[0].items[0].start_time)

    def test_missing_times_are_allowed(self):
        raw = raw_plan(days=1)
        del raw["days"][0]["items"][0]["start_time"]
        del raw["days"][0]["items"][0]["end_time"]

        plan = self.validate(raw)

        self.assertIsNone(plan.days[0].items[0].start_time)
        self.assertIsNone(plan.days[0].items[0].end_time)

    def test_too_many_days_are_truncated_to_the_trip_length(self):
        raw = raw_plan(days=10)

        plan = self.validate(raw)

        self.assertEqual(len(plan.days), 3)

    def test_too_few_days_are_kept_as_they_are(self):
        raw = raw_plan(days=1)

        plan = self.validate(raw)

        self.assertEqual(len(plan.days), 1)

    def test_a_plan_without_days_is_rejected(self):
        with self.assertRaises(AIValidationError):
            self.validate({"title": "Trip", "days": []})

    def test_a_plan_without_a_title_is_rejected(self):
        with self.assertRaises(AIValidationError):
            self.validate({"days": [{"items": []}]})

    def test_a_plan_that_is_not_an_object_is_rejected(self):
        with self.assertRaises(AIValidationError):
            self.validate(["not", "an", "object"])


class GenerationServiceTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            email="generator@example.com",
            password="TestPass123!",
            first_name="Gene",
            last_name="Rator",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Bengaluru Getaway",
            destination="Bengaluru",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 2),
            budget=Decimal("40000.00"),
            currency="INR",
            travelers=2,
        )

        self.places = [make_place("node/1", "Cubbon Park")]

    def test_generate_persists_the_plan(self):
        client = FakeOllamaClient(
            json.dumps(raw_plan(days=2)),
        )

        result = ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            client=client,
        )

        self.assertTrue(result["persisted"])
        self.assertIsNotNone(result["itinerary_id"])

        itinerary = Itinerary.objects.get(id=result["itinerary_id"])

        self.assertEqual(itinerary.trip, self.trip)
        self.assertEqual(itinerary.title, "Bengaluru Getaway")

        items = ItineraryItem.objects.filter(
            itinerary=itinerary,
        ).order_by("date", "order")

        self.assertEqual(items.count(), 2)

        self.assertEqual(items[0].date, date(2026, 11, 1))
        self.assertEqual(items[0].order, 1)
        self.assertEqual(items[1].date, date(2026, 11, 2))
        self.assertEqual(items[1].order, 1)

    def test_generated_items_carry_the_place_location(self):
        client = FakeOllamaClient(
            json.dumps(raw_plan(days=1)),
        )

        result = ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            client=client,
        )

        item = ItineraryItem.objects.get(
            itinerary_id=result["itinerary_id"],
        )

        self.assertEqual(item.location_name, "Cubbon Park")
        self.assertEqual(item.location_address, "MG Road, Bengaluru")
        self.assertAlmostEqual(float(item.latitude), 12.9763)
        self.assertAlmostEqual(float(item.longitude), 77.6033)
        self.assertEqual(item.start_time, datetime(2026, 1, 1, 9, 0).time())

    def test_dry_run_does_not_persist_anything(self):
        client = FakeOllamaClient(
            json.dumps(raw_plan(days=2)),
        )

        result = ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            dry_run=True,
            client=client,
        )

        self.assertFalse(result["persisted"])
        self.assertIsNone(result["itinerary_id"])
        self.assertEqual(
            Itinerary.objects.filter(trip=self.trip).count(),
            0,
        )

    def test_an_existing_itinerary_is_not_replaced_without_permission(self):
        Itinerary.objects.create(
            trip=self.trip,
            title="Existing Itinerary",
        )

        client = FakeOllamaClient(
            json.dumps(raw_plan(days=2)),
        )

        with self.assertRaises(ItineraryExistsError):
            ItineraryGenerationService.generate(
                trip=self.trip,
                places=self.places,
                client=client,
            )

        self.assertEqual(
            Itinerary.objects.get(trip=self.trip).title,
            "Existing Itinerary",
        )

    def test_an_existing_itinerary_is_replaced_when_allowed(self):
        Itinerary.objects.create(
            trip=self.trip,
            title="Existing Itinerary",
        )

        client = FakeOllamaClient(
            json.dumps(raw_plan(days=2)),
        )

        result = ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            replace=True,
            client=client,
        )

        itinerary = Itinerary.objects.get(trip=self.trip)

        self.assertEqual(itinerary.title, "Bengaluru Getaway")
        self.assertEqual(
            ItineraryItem.objects.filter(itinerary=itinerary).count(),
            2,
        )

    def test_replacing_removes_the_previous_items(self):
        itinerary = Itinerary.objects.create(
            trip=self.trip,
            title="Existing Itinerary",
        )

        ItineraryItem.objects.create(
            itinerary=itinerary,
            date=self.trip.start_date,
            title="Old Activity",
            order=1,
        )

        client = FakeOllamaClient(
            json.dumps(raw_plan(days=2)),
        )

        ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            replace=True,
            client=client,
        )

        titles = list(
            ItineraryItem.objects
            .filter(itinerary=itinerary)
            .values_list("title", flat=True)
        )

        self.assertNotIn("Old Activity", titles)

    def test_the_prompt_includes_the_places(self):
        client = FakeOllamaClient(
            json.dumps(raw_plan(days=1)),
        )

        ItineraryGenerationService.generate(
            trip=self.trip,
            places=self.places,
            client=client,
        )

        prompt, system = client.prompts[0]

        self.assertIn("node/1", prompt)
        self.assertIn("Cubbon Park", prompt)
        self.assertTrue(system)

    def test_get_preferences_returns_none_when_there_are_none(self):
        self.assertIsNone(
            ItineraryGenerationService.get_preferences(self.trip)
        )
