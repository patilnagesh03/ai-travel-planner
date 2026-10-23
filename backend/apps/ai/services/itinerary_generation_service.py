"""
Generates an itinerary for a trip using a local model.

The flow has four clearly separated stages:

1. **Collect** the trip, its preferences and the places it could visit.
   The places come from the integrations app. The AI layer never makes its
   own external requests.
2. **Generate** a plan with the model.
3. **Validate** the plan. Nothing is persisted until it passes.
4. **Persist** the plan as an `Itinerary` and its `ItineraryItem`s.

The validation in stage 3 is the important part. A language model will
happily invent a restaurant, a date outside the trip or a time that makes
no sense. We therefore:

* assign the dates ourselves, so the model cannot choose them;
* only accept a place the model references by a stable id we supplied, so
  the model cannot invent a venue;
* take the coordinates from our own place data, so the model never states
  a coordinate;
* drop any activity that survives none of that, rather than storing
  something we cannot vouch for.
"""

import logging
from datetime import datetime, time, timedelta

from django.db import transaction

from backend.apps.ai.clients import OllamaClient, parse_json_completion
from backend.apps.ai.exceptions import (
    AIResponseError,
    AIValidationError,
)
from backend.apps.ai.schemas import (
    GeneratedDay,
    GeneratedItem,
    GeneratedPlan,
)
from backend.apps.ai.services.prompt_service import PromptService
from backend.apps.integrations.schemas import BoundingBox
from backend.apps.integrations.services import (
    DestinationService,
    PlacesService,
)
from backend.apps.itinerary.enums import ActivityType
from backend.apps.itinerary.models import Itinerary, ItineraryItem
from backend.apps.trips.models import TripPreference


logger = logging.getLogger(__name__)


# Time formats a model might use for a start or end time.
TIME_FORMATS = ("%H:%M", "%H:%M:%S")


class ItineraryGenerationService:

    @staticmethod
    def generate(
        trip,
        preferences=None,
        places=None,
        dry_run=False,
        replace=False,
        client=None,
    ):
        """Generate an itinerary for a trip.

        ``dry_run`` returns the plan without saving anything. ``replace``
        allows an existing itinerary for this trip to be overwritten; without
        it, an existing itinerary is left alone.
        """

        if places is None:
            places = ItineraryGenerationService.collect_places(trip)

        prompt = PromptService.build_prompt(
            trip=trip,
            preferences=preferences,
            places=places,
        )

        ollama_client = client or OllamaClient()

        completion = ollama_client.generate(
            prompt=prompt,
            system=PromptService.build_system_prompt(),
        )

        raw_plan = parse_json_completion(completion)

        plan = ItineraryGenerationService.validate_plan(
            raw_plan=raw_plan,
            trip=trip,
            places=places,
        )

        if dry_run:
            return {
                "itinerary_id": None,
                "persisted": False,
                "plan": plan,
            }

        itinerary = ItineraryGenerationService.persist_plan(
            trip=trip,
            plan=plan,
            replace=replace,
        )

        return {
            "itinerary_id": itinerary.id,
            "persisted": True,
            "plan": plan,
        }

    @staticmethod
    def get_preferences(trip):
        """Return the trip's preferences, or None when there are none."""

        try:
            return trip.preferences
        except TripPreference.DoesNotExist:
            return None

    @staticmethod
    def collect_places(trip):
        """Find the places the trip could visit.

        The trip's destination is resolved to a search area and the
        integrations app does the actual provider call. The AI layer never
        talks to the places provider itself.
        """

        bbox = DestinationService.resolve(destination=trip.destination)

        return PlacesService.search_places(bbox=bbox)

    @staticmethod
    def validate_plan(raw_plan, trip, places):
        """Turn the model's raw output into a validated plan.

        Raises `AIValidationError` when the plan is unusable, and drops
        individual activities that cannot be trusted.
        """

        if not isinstance(raw_plan, dict):
            raise AIValidationError(
                "The generated plan was not a JSON object."
            )

        title = raw_plan.get("title")

        if not isinstance(title, str) or not title.strip():
            raise AIValidationError(
                "The generated plan has no title."
            )

        description = raw_plan.get("description")

        if not isinstance(description, str) or not description.strip():
            description = None
        else:
            description = description.strip()

        raw_days = raw_plan.get("days")

        if not isinstance(raw_days, list) or not raw_days:
            raise AIValidationError(
                "The generated plan has no days."
            )

        trip_length = PromptService.trip_length(trip)

        if len(raw_days) > trip_length:
            logger.warning(
                "The model returned %s day(s) for a %s day trip; "
                "the extra day(s) were dropped.",
                len(raw_days),
                trip_length,
            )

            raw_days = raw_days[:trip_length]

        if len(raw_days) < trip_length:
            logger.warning(
                "The model returned %s day(s) for a %s day trip.",
                len(raw_days),
                trip_length,
            )

        places_by_id = {
            place.source_id: place
            for place in places
        }

        days = []

        for index, raw_day in enumerate(raw_days):
            # The model never chooses the date. We do.
            trip_date = trip.start_date + timedelta(days=index)

            raw_items = None

            if isinstance(raw_day, dict):
                raw_items = raw_day.get("items")

            if not isinstance(raw_items, list):
                raw_items = []

            items = []

            for raw_item in raw_items:
                item = ItineraryGenerationService.validate_item(
                    raw_item,
                    places_by_id,
                )

                if item is not None:
                    items.append(item)

            if not items:
                logger.warning(
                    "The model produced no usable activities for %s.",
                    trip_date,
                )

            days.append(
                GeneratedDay(
                    date=trip_date,
                    items=items,
                )
            )

        return GeneratedPlan(
            title=title.strip(),
            description=description,
            days=days,
        )

    @staticmethod
    def validate_item(raw_item, places_by_id):
        """Validate one activity, or return None if it cannot be trusted."""

        if not isinstance(raw_item, dict):
            return None

        title = raw_item.get("title")

        if not isinstance(title, str) or not title.strip():
            return None

        place_source_id = raw_item.get("place")

        if not isinstance(place_source_id, str):
            place_source_id = None

        place = places_by_id.get(place_source_id)

        if place is None:
            # The model referenced a place we never offered it. Storing
            # this would mean storing a venue that may not exist.
            logger.warning(
                "Dropping activity %r: it references an unknown place "
                "(%r).",
                title.strip(),
                place_source_id,
            )

            return None

        description = raw_item.get("description")

        if not isinstance(description, str) or not description.strip():
            description = None
        else:
            description = description.strip()

        activity_type = raw_item.get("activity_type")

        if (
            not isinstance(activity_type, str)
            or activity_type not in ActivityType.values
        ):
            activity_type = ActivityType.OTHER

        start_time = ItineraryGenerationService.parse_time(
            raw_item.get("start_time"),
        )

        end_time = ItineraryGenerationService.parse_time(
            raw_item.get("end_time"),
        )

        if start_time and end_time and end_time < start_time:
            logger.warning(
                "Activity %r had an end time before its start time; "
                "the two were swapped.",
                title.strip(),
            )

            start_time, end_time = end_time, start_time

        return GeneratedItem(
            title=title.strip(),
            description=description,
            start_time=start_time,
            end_time=end_time,
            activity_type=activity_type,
            place_source_id=place.source_id,
            place_name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
            address=place.address,
        )

    @staticmethod
    def parse_time(value):
        """Parse an `HH:MM` string, returning None when it is unusable."""

        if not isinstance(value, str):
            return None

        text = value.strip()

        if not text:
            return None

        for time_format in TIME_FORMATS:
            try:
                return datetime.strptime(text, time_format).time()
            except ValueError:
                continue

        logger.warning(
            "Ignoring unparseable time %r.",
            value,
        )

        return None

    @staticmethod
    def persist_plan(trip, plan, replace=False):
        """Save a validated plan as an itinerary and its items."""

        existing = Itinerary.objects.filter(trip=trip).first()

        if existing is not None and not replace:
            raise ItineraryExistsError(
                "This trip already has an itinerary. "
                "Send replace=true to regenerate it."
            )

        with transaction.atomic():
            if existing is None:
                itinerary = Itinerary.objects.create(
                    trip=trip,
                    title=plan.title,
                    description=plan.description,
                )
            else:
                itinerary = existing
                itinerary.title = plan.title
                itinerary.description = plan.description
                itinerary.save()

                # The order of a day has to start at 1 again, so the old
                # items have to go before the new ones are written.
                itinerary.items.all().delete()

            for day in plan.days:
                for order, item in enumerate(day.items, start=1):
                    ItineraryItem.objects.create(
                        itinerary=itinerary,
                        date=day.date,
                        start_time=item.start_time,
                        end_time=item.end_time,
                        title=item.title,
                        description=item.description,
                        location_name=item.place_name,
                        location_address=item.address,
                        latitude=item.latitude,
                        longitude=item.longitude,
                        activity_type=item.activity_type,
                        order=order,
                    )

        return itinerary


class ItineraryExistsError(Exception):
    """The trip already has an itinerary and replacement was not requested."""


__all__ = [
    "ItineraryGenerationService",
    "ItineraryExistsError",
]
