"""
Unit tests for the deterministic flight link builder.

No network is involved: the whole point of the service is that the links are
derived from the trip alone.
"""

from datetime import date
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from django.test import SimpleTestCase

from backend.apps.integrations.exceptions import MissingTripOriginError
from backend.apps.integrations.services import FlightService


def make_trip(
    origin="Delhi",
    destination="Goa",
    travelers=2,
    start_date=date(2026, 11, 10),
    end_date=date(2026, 11, 15),
):
    return SimpleNamespace(
        origin=origin,
        destination=destination,
        travelers=travelers,
        start_date=start_date,
        end_date=end_date,
    )


class FlightLinkTests(SimpleTestCase):

    def test_a_trip_without_an_origin_is_rejected(self):
        with self.assertRaises(MissingTripOriginError):
            FlightService.build_links(make_trip(origin=""))

    def test_a_whitespace_origin_is_rejected(self):
        with self.assertRaises(MissingTripOriginError):
            FlightService.build_links(make_trip(origin="   "))

    def test_google_flights_query_contains_route_and_dates(self):
        result = FlightService.build_links(make_trip())

        google = result["links"][0]

        self.assertEqual(google["provider"], "google_flights")
        self.assertEqual(google["label"], "Google Flights")

        query = parse_qs(urlparse(google["url"]).query)["q"][0]

        self.assertEqual(
            query,
            "Flights from Delhi to Goa on 2026-11-10 through 2026-11-15 "
            "for 2 adults",
        )

    def test_google_flights_query_is_encoded(self):
        result = FlightService.build_links(
            make_trip(origin="New Delhi", destination="Goa & Mumbai"),
        )

        url = result["links"][0]["url"]

        self.assertIn("New+Delhi", url)
        self.assertNotIn(" ", url)

    def test_kayak_url_uses_route_and_dates(self):
        result = FlightService.build_links(make_trip())

        kayak = result["links"][1]

        self.assertEqual(kayak["provider"], "kayak")
        self.assertEqual(
            kayak["url"],
            "https://www.kayak.co.in/flights/Delhi-Goa/"
            "2026-11-10/2026-11-15",
        )

    def test_multi_word_places_become_single_path_segments(self):
        result = FlightService.build_links(
            make_trip(origin="New Delhi", destination="Goa"),
        )

        kayak_url = result["links"][1]["url"]

        self.assertIn("/flights/New-Delhi-Goa/", kayak_url)

    def test_a_non_latin_origin_is_percent_encoded(self):
        result = FlightService.build_links(make_trip(origin="दिल्ली"))

        kayak_url = result["links"][1]["url"]

        self.assertIn("%E0%A4%A6", kayak_url)

    def test_a_single_traveller_is_not_mentioned(self):
        result = FlightService.build_links(make_trip(travelers=1))

        query = parse_qs(
            urlparse(result["links"][0]["url"]).query,
        )["q"][0]

        self.assertNotIn("adults", query)

    def test_the_result_reports_the_trip_details(self):
        result = FlightService.build_links(make_trip())

        self.assertEqual(result["origin"], "Delhi")
        self.assertEqual(result["destination"], "Goa")
        self.assertEqual(result["start_date"], date(2026, 11, 10))
        self.assertEqual(result["end_date"], date(2026, 11, 15))
        self.assertEqual(result["travelers"], 2)
        self.assertTrue(result["disclaimer"])

    def test_links_are_deterministic(self):
        first = FlightService.build_links(make_trip())
        second = FlightService.build_links(make_trip())

        self.assertEqual(first, second)
