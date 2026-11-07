"""
Unit tests for accommodation discovery.

The Overpass call is always mocked. The real provider is not reachable from
every network, and these tests are about our own filtering, sorting and
distance maths, not about the provider.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.apps.integrations.config import MAX_PLACES_PER_SEARCH
from backend.apps.integrations.exceptions import (
    IntegrationUnavailableError,
    UnsupportedDestinationError,
)
from backend.apps.integrations.schemas import (
    HOTEL_CATEGORIES,
    Place,
    PlaceCategory,
    PlaceSource,
)
from backend.apps.integrations.services import HotelService
from backend.apps.integrations.services.hotel_service import Hotel


SEARCH_TARGET = (
    "backend.apps.integrations.services.hotel_service."
    "PlacesService.search_places"
)


def make_place(name, latitude, longitude):
    return Place(
        source=PlaceSource.OPENSTREETMAP,
        source_id="node/{name}".format(name=name),
        name=name,
        category=PlaceCategory.HOTEL,
        latitude=latitude,
        longitude=longitude,
    )


def make_trip(destination="Bengaluru", travelers=2):
    return SimpleNamespace(
        destination=destination,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 15),
        travelers=travelers,
    )


class HotelSearchTests(SimpleTestCase):

    def test_hotels_are_sorted_by_distance_from_the_centre(self):
        places = [
            make_place("Far Hotel", 13.10, 77.70),
            make_place("Near Hotel", 12.991, 77.601),
            make_place("Middle Hotel", 13.00, 77.61),
        ]

        with patch(SEARCH_TARGET, return_value=places):
            result = HotelService.search_hotels(make_trip())

        self.assertEqual(
            [hotel.name for hotel in result["hotels"]],
            ["Near Hotel", "Middle Hotel", "Far Hotel"],
        )

    def test_equally_distant_hotels_are_ordered_by_name(self):
        places = [
            make_place("Beta Lodge", 12.991, 77.601),
            make_place("Alpha Lodge", 12.991, 77.601),
        ]

        with patch(SEARCH_TARGET, return_value=places):
            result = HotelService.search_hotels(make_trip())

        self.assertEqual(
            [hotel.name for hotel in result["hotels"]],
            ["Alpha Lodge", "Beta Lodge"],
        )

    def test_only_accommodation_categories_are_requested(self):
        with patch(SEARCH_TARGET, return_value=[]) as search:
            HotelService.search_hotels(make_trip())

        kwargs = search.call_args.kwargs

        self.assertEqual(kwargs["categories"], list(HOTEL_CATEGORIES))
        self.assertEqual(kwargs["limit"], MAX_PLACES_PER_SEARCH)

    def test_distance_is_computed_from_the_destination_centre(self):
        places = [make_place("At The Centre", 12.99, 77.6)]

        with patch(SEARCH_TARGET, return_value=places):
            result = HotelService.search_hotels(make_trip())

        self.assertEqual(result["hotels"][0].distance_km, 0.0)

    def test_distance_uses_the_haversine_formula(self):
        # One degree of latitude is about 111.2 km.
        distance = HotelService.distance_km(12.99, 77.6, 13.99, 77.6)

        self.assertAlmostEqual(distance, 111.19, places=1)

    def test_the_limit_is_applied_after_sorting(self):
        places = [
            make_place("Far Hotel", 13.10, 77.70),
            make_place("Near Hotel", 12.991, 77.601),
        ]

        with patch(SEARCH_TARGET, return_value=places):
            result = HotelService.search_hotels(make_trip(), limit=1)

        self.assertEqual(len(result["hotels"]), 1)
        self.assertEqual(result["hotels"][0].name, "Near Hotel")

    def test_hotels_keep_the_place_fields(self):
        places = [
            Place(
                source=PlaceSource.OPENSTREETMAP,
                source_id="way/42",
                name="Riverside Inn",
                category=PlaceCategory.GUEST_HOUSE,
                latitude=12.991,
                longitude=77.601,
                address="1 River Road",
                opening_hours="24/7",
            ),
        ]

        with patch(SEARCH_TARGET, return_value=places):
            result = HotelService.search_hotels(make_trip())

        hotel = result["hotels"][0]

        self.assertIsInstance(hotel, Hotel)
        self.assertEqual(hotel.source_id, "way/42")
        self.assertEqual(hotel.category, PlaceCategory.GUEST_HOUSE)
        self.assertEqual(hotel.address, "1 River Road")
        self.assertEqual(hotel.opening_hours, "24/7")

    def test_the_destination_is_reported(self):
        with patch(SEARCH_TARGET, return_value=[]):
            result = HotelService.search_hotels(make_trip())

        self.assertEqual(
            result["destination"],
            {
                "name": "Bengaluru",
                "state": "Karnataka",
                "latitude": 12.99,
                "longitude": 77.6,
            },
        )

    def test_a_booking_search_link_is_built(self):
        with patch(SEARCH_TARGET, return_value=[]):
            result = HotelService.search_hotels(make_trip())

        url = result["booking_url"]

        self.assertTrue(url.startswith(
            "https://www.booking.com/searchresults.html?",
        ))
        self.assertIn("ss=Bengaluru", url)
        self.assertIn("checkin=2026-11-10", url)
        self.assertIn("checkout=2026-11-15", url)
        self.assertIn("group_adults=2", url)

    def test_an_unsupported_destination_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            HotelService.search_hotels(make_trip(destination="Kumbakonam"))

    def test_provider_failures_are_not_swallowed(self):
        with patch(
            SEARCH_TARGET,
            side_effect=IntegrationUnavailableError("down"),
        ):
            with self.assertRaises(IntegrationUnavailableError):
                HotelService.search_hotels(make_trip())

    def test_the_attribution_is_present(self):
        with patch(SEARCH_TARGET, return_value=[]):
            result = HotelService.search_hotels(make_trip())

        self.assertIn("OpenStreetMap", result["attribution"])
