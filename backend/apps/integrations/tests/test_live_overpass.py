"""
A small, controlled live test against the public Overpass API.

This test is SKIPPED by default. It talks to a third-party public service, so
it must only run when you explicitly ask for it::

    # Windows PowerShell
    $env:OVERPASS_LIVE_TEST = "1"
    python manage.py test backend.apps.integrations.tests.test_live_overpass

    # Linux / macOS
    OVERPASS_LIVE_TEST=1 python manage.py test \
        backend.apps.integrations.tests.test_live_overpass

The query used here is intentionally tiny. We are a guest on shared public
infrastructure and should never ask it for more than we need.
"""

import os

from django.test import SimpleTestCase

from backend.apps.integrations.config import MAX_PLACES_PER_SEARCH
from backend.apps.integrations.schemas import BoundingBox, PlaceCategory
from backend.apps.integrations.services import PlacesService


LIVE_TEST_ENABLED = os.environ.get("OVERPASS_LIVE_TEST") == "1"

# A small box in central Bengaluru: densely mapped, so a successful query
# should return real results.
BENGALURU = BoundingBox(
    south=12.9600,
    west=77.5900,
    north=12.9800,
    east=77.6100,
)


class LiveOverpassTests(SimpleTestCase):

    def setUp(self):
        if not LIVE_TEST_ENABLED:
            self.skipTest(
                "Live Overpass test is disabled. "
                "Set OVERPASS_LIVE_TEST=1 to run it."
            )

    def test_live_query_is_accepted_and_bounded(self):
        """The provider accepts our query and we stay within our limit."""

        places = PlacesService.search_places(
            bbox=BENGALURU,
            categories=[PlaceCategory.ATTRACTION],
            limit=5,
        )

        self.assertIsInstance(places, list)
        self.assertLessEqual(len(places), 5)

    def test_live_places_are_well_formed(self):
        """Every place the provider returns is usable by the application."""

        places = PlacesService.search_places(
            bbox=BENGALURU,
            limit=10,
        )

        self.assertLessEqual(len(places), MAX_PLACES_PER_SEARCH)

        for place in places:
            self.assertTrue(place.name)
            self.assertTrue(place.source_id)
            self.assertTrue(place.category)
            self.assertGreaterEqual(place.latitude, -90)
            self.assertLessEqual(place.latitude, 90)
            self.assertGreaterEqual(place.longitude, -180)
            self.assertLessEqual(place.longitude, 180)
