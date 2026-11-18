"""
Unit tests for destination resolution.

The curated city list, the coordinate override and the explicit handling of
unsupported destinations are all covered here.
"""

from django.test import SimpleTestCase

from backend.apps.integrations.exceptions import UnsupportedDestinationError
from backend.apps.integrations.schemas import BoundingBox
from backend.apps.integrations.services import DestinationService
from backend.apps.integrations.services.destination_service import (
    DEFAULT_SEARCH_RADIUS_KM,
    MAX_SEARCH_RADIUS_KM,
)


class DestinationNameTests(SimpleTestCase):

    def test_exact_city_name_resolves(self):
        bbox = DestinationService.resolve(destination="Mumbai")

        self.assertIsInstance(bbox, BoundingBox)
        self.assertAlmostEqual(bbox.south, 18.8930)
        self.assertAlmostEqual(bbox.north, 19.2760)

    def test_city_name_is_case_insensitive(self):
        self.assertEqual(
            DestinationService.resolve(destination="mumbai"),
            DestinationService.resolve(destination="MUMBAI"),
        )

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(
            DestinationService.resolve(destination="   Mumbai   "),
            DestinationService.resolve(destination="Mumbai"),
        )

    def test_known_alias_resolves(self):
        self.assertEqual(
            DestinationService.resolve(destination="Bombay"),
            DestinationService.resolve(destination="Mumbai"),
        )

        self.assertEqual(
            DestinationService.resolve(destination="Bangalore"),
            DestinationService.resolve(destination="Bengaluru"),
        )

        self.assertEqual(
            DestinationService.resolve(destination="Trivandrum"),
            DestinationService.resolve(destination="Thiruvananthapuram"),
        )

    def test_city_with_state_after_comma_resolves(self):
        self.assertEqual(
            DestinationService.resolve(destination="Bengaluru, Karnataka"),
            DestinationService.resolve(destination="Bengaluru"),
        )

    def test_city_with_state_after_space_resolves(self):
        self.assertEqual(
            DestinationService.resolve(destination="Bengaluru Karnataka"),
            DestinationService.resolve(destination="Bengaluru"),
        )

    def test_city_with_state_code_resolves(self):
        self.assertEqual(
            DestinationService.resolve(destination="Mumbai MH"),
            DestinationService.resolve(destination="Mumbai"),
        )

    def test_city_with_country_suffix_resolves(self):
        self.assertEqual(
            DestinationService.resolve(destination="Mumbai, India"),
            DestinationService.resolve(destination="Mumbai"),
        )

    def test_multi_word_alias_is_not_split(self):
        # "New Delhi" must not be read as the city "New" in the state "Delhi".
        self.assertEqual(
            DestinationService.resolve(destination="New Delhi"),
            DestinationService.resolve(destination="Delhi"),
        )

    def test_unknown_destination_is_rejected_explicitly(self):
        with self.assertRaises(UnsupportedDestinationError) as ctx:
            DestinationService.resolve(destination="Kumbakonam")

        self.assertIn("Kumbakonam", str(ctx.exception))

    def test_whole_country_destination_is_rejected(self):
        # A country-wide search is exactly the kind of broad query we must
        # never send to shared public infrastructure.
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(destination="India")

    def test_state_mismatch_is_reported_explicitly(self):
        with self.assertRaises(UnsupportedDestinationError) as ctx:
            DestinationService.resolve(destination="Mumbai, Karnataka")

        message = str(ctx.exception)

        self.assertIn("Mumbai", message)
        self.assertIn("Maharashtra", message)

    def test_state_mismatch_in_the_space_form_is_reported(self):
        with self.assertRaises(UnsupportedDestinationError) as ctx:
            DestinationService.resolve(destination="Kedarnath Himachal")

        message = str(ctx.exception)

        self.assertIn("Kedarnath", message)
        self.assertIn("Uttarakhand", message)

    def test_a_country_suffix_does_not_trigger_a_mismatch(self):
        # "Kedarnath Himachal, India" names the city correctly and only
        # gets the state wrong. The city itself is unambiguous, so it
        # resolves rather than being rejected over a typo.
        self.assertEqual(
            DestinationService.resolve(
                destination="Kedarnath Himachal, India"
            ),
            DestinationService.resolve(destination="Kedarnath"),
        )

    def test_empty_destination_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(destination="   ")

    def test_find_city_returns_none_for_unknown_destination(self):
        self.assertIsNone(
            DestinationService.find_city("Nowhere In Particular")
        )


class CoordinateOverrideTests(SimpleTestCase):

    def test_coordinates_are_used_when_no_destination_is_given(self):
        bbox = DestinationService.resolve(
            latitude=19.0760,
            longitude=72.8777,
        )

        self.assertIsInstance(bbox, BoundingBox)

        # The box is centred on the requested point.
        self.assertAlmostEqual((bbox.south + bbox.north) / 2, 19.0760, places=3)
        self.assertAlmostEqual((bbox.west + bbox.east) / 2, 72.8777, places=3)

    def test_coordinates_override_a_destination_name(self):
        with_destination = DestinationService.resolve(destination="Mumbai")

        with_override = DestinationService.resolve(
            destination="Mumbai",
            latitude=15.4909,
            longitude=73.8278,
        )

        self.assertNotEqual(with_destination, with_override)
        self.assertAlmostEqual(
            (with_override.south + with_override.north) / 2,
            15.4909,
            places=3,
        )

    def test_default_radius_is_used_when_none_is_given(self):
        bbox = DestinationService.resolve(
            latitude=19.0760,
            longitude=72.8777,
        )

        expected = DEFAULT_SEARCH_RADIUS_KM / 111.32

        self.assertAlmostEqual(
            (bbox.north - bbox.south) / 2,
            expected,
            places=4,
        )

    def test_radius_is_honoured(self):
        bbox = DestinationService.resolve(
            latitude=19.0760,
            longitude=72.8777,
            radius_km=10,
        )

        expected = 10 / 111.32

        self.assertAlmostEqual(
            (bbox.north - bbox.south) / 2,
            expected,
            places=4,
        )

    def test_longitude_delta_widens_away_from_the_equator(self):
        # A degree of longitude covers less ground near the poles, so the
        # longitude span must grow for the same radius.
        near_equator = DestinationService.resolve(
            latitude=1.0,
            longitude=0.0,
            radius_km=10,
        )

        near_pole = DestinationService.resolve(
            latitude=60.0,
            longitude=0.0,
            radius_km=10,
        )

        self.assertGreater(
            near_pole.east - near_pole.west,
            near_equator.east - near_equator.west,
        )

    def test_missing_longitude_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(latitude=19.0760)

    def test_missing_latitude_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(longitude=72.8777)

    def test_out_of_range_latitude_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(latitude=95.0, longitude=72.8777)

    def test_out_of_range_longitude_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(latitude=19.0, longitude=200.0)

    def test_non_numeric_coordinates_are_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(
                latitude="north-ish",
                longitude=72.8777,
            )

    def test_excessive_radius_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(
                latitude=19.0,
                longitude=72.8,
                radius_km=MAX_SEARCH_RADIUS_KM + 1,
            )

    def test_zero_radius_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(
                latitude=19.0,
                longitude=72.8,
                radius_km=0,
            )

    def test_negative_radius_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve(
                latitude=19.0,
                longitude=72.8,
                radius_km=-5,
            )


class ResolveInputTests(SimpleTestCase):

    def test_neither_destination_nor_coordinates_is_rejected(self):
        with self.assertRaises(UnsupportedDestinationError):
            DestinationService.resolve()

    def test_supported_destinations_are_listed(self):
        destinations = DestinationService.supported_destinations()

        self.assertGreater(len(destinations), 20)

        first = destinations[0]

        self.assertIn("name", first)
        self.assertIn("state", first)
        self.assertIn("latitude", first)
        self.assertIn("longitude", first)

    def test_mumbai_is_a_supported_destination(self):
        names = [
            destination["name"]
            for destination
            in DestinationService.supported_destinations()
        ]

        self.assertIn("Mumbai", names)
        self.assertIn("Bengaluru", names)


class CuratedCityCoordinatesTests(SimpleTestCase):
    """Guard against bad entries in the curated city list.

    A live check found that Goa had been given Thiruvananthapuram's latitude
    band (8.35..8.55 instead of 14.90..15.75), which put its bounding box in
    the sea and made every Goa search return nothing. The box was still
    "inside India" and structurally valid, so only an explicit expectation
    would have caught it.
    """

    def test_goa_is_on_the_goan_coast(self):
        bbox = DestinationService.resolve(destination="Goa")

        # Goa sits between ~14.9 and ~15.8 degrees north.
        self.assertGreater(bbox.south, 14.0)
        self.assertLess(bbox.north, 16.5)

        # ...and between ~73.7 and ~74.4 degrees east.
        self.assertGreater(bbox.west, 73.0)
        self.assertLess(bbox.east, 75.0)

    def test_goa_is_not_mistaken_for_a_southern_kerala_city(self):
        goa = DestinationService.resolve(destination="Goa")
        trivandrum = DestinationService.resolve(destination="Trivandrum")

        # The two must not share a latitude band; that was the copy/paste
        # defect that emptied every Goa search.
        self.assertGreater(goa.south - trivandrum.north, 5.0)
