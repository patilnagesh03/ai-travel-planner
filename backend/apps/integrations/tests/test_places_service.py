"""
Unit tests for the places service: query building, normalization,
de-duplication and result limiting.
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase

from backend.apps.integrations.exceptions import IntegrationError
from backend.apps.integrations.tests.helpers import CacheClearingMixin
from backend.apps.integrations.schemas import (
    BoundingBox,
    Place,
    PlaceCategory,
    PlaceSource,
)
from backend.apps.integrations.services import PlacesService


BENGALURU = BoundingBox(
    south=12.90,
    west=77.50,
    north=12.99,
    east=77.65,
)


def node_element(element_id=1, name="Cubbon Park", **tags):
    element = {
        "type": "node",
        "id": element_id,
        "lat": 12.9763,
        "lon": 77.6033,
    }

    element["tags"] = {"name": name, **tags}

    return element


def way_element(element_id=2, name="Palace", **tags):
    return {
        "type": "way",
        "id": element_id,
        "center": {"lat": 12.9719, "lon": 77.5946},
        "tags": {"name": name, **tags},
    }


def relation_element(element_id=3, name="Heritage Zone", **tags):
    return {
        "type": "relation",
        "id": element_id,
        "center": {"lat": 12.9650, "lon": 77.6010},
        "tags": {"name": name, **tags},
    }


class PlacesQueryTests(SimpleTestCase):

    def test_query_contains_bbox_timeout_and_limit(self):
        query = PlacesService.build_query(
            bbox=BENGALURU,
            limit=15,
        )

        self.assertIn("[out:json][timeout:20];", query)
        self.assertIn("(12.9,77.5,12.99,77.65)", query)
        self.assertIn("out center 15;", query)

    def test_query_only_contains_requested_categories(self):
        query = PlacesService.build_query(
            bbox=BENGALURU,
            categories=[PlaceCategory.MUSEUM, PlaceCategory.CAFE],
            limit=5,
        )

        self.assertIn('nwr["tourism"="museum"]', query)
        self.assertIn('nwr["amenity"="cafe"]', query)

        self.assertNotIn('nwr["tourism"="attraction"]', query)
        self.assertNotIn('nwr["amenity"="restaurant"]', query)

    def test_query_contains_every_category_by_default(self):
        query = PlacesService.build_query(
            bbox=BENGALURU,
            limit=20,
        )

        self.assertIn('nwr["tourism"="attraction"]', query)
        self.assertIn('nwr["tourism"="museum"]', query)
        self.assertIn('nwr["tourism"="viewpoint"]', query)
        self.assertIn('nwr["historic"="monument"]', query)
        self.assertIn('nwr["amenity"="place_of_worship"]', query)
        self.assertIn('nwr["leisure"="park"]', query)
        self.assertIn('nwr["amenity"="restaurant"]', query)
        self.assertIn('nwr["amenity"="cafe"]', query)

    def test_unsupported_category_is_rejected(self):
        with self.assertRaises(ValueError):
            PlacesService.build_query(
                bbox=BENGALURU,
                categories=["not-a-real-category"],
                limit=5,
            )

    def test_bbox_must_be_a_bounding_box(self):
        with self.assertRaises(ValueError):
            PlacesService.build_query(
                bbox="12.9,77.5,12.99,77.65",
                limit=5,
            )

    def test_limit_cannot_exceed_configured_maximum(self):
        query = PlacesService.build_query(
            bbox=BENGALURU,
            limit=500,
        )

        self.assertIn("out center 20;", query)

    def test_limit_must_be_positive(self):
        with self.assertRaises(ValueError):
            PlacesService.build_query(
                bbox=BENGALURU,
                limit=0,
            )


class BoundingBoxTests(SimpleTestCase):

    def test_bbox_serialises_in_overpass_order(self):
        self.assertEqual(
            BENGALURU.as_overpass_tuple(),
            "12.9,77.5,12.99,77.65",
        )

    def test_invalid_latitude_is_rejected(self):
        with self.assertRaises(ValueError):
            BoundingBox(south=-91, west=0, north=10, east=10)

    def test_invalid_longitude_is_rejected(self):
        with self.assertRaises(ValueError):
            BoundingBox(south=0, west=0, north=10, east=181)

    def test_inverted_latitudes_are_rejected(self):
        with self.assertRaises(ValueError):
            BoundingBox(south=10, west=0, north=0, east=10)

    def test_inverted_longitudes_are_rejected(self):
        with self.assertRaises(ValueError):
            BoundingBox(south=0, west=10, north=10, east=0)


class PlacesNormalizationTests(SimpleTestCase):

    def test_node_is_normalized(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=101,
                    name="Cubbon Park",
                    leisure="park",
                ),
            ],
        )

        self.assertEqual(len(places), 1)

        place = places[0]

        self.assertEqual(place.source, PlaceSource.OPENSTREETMAP)
        self.assertEqual(place.source_id, "node/101")
        self.assertEqual(place.name, "Cubbon Park")
        self.assertEqual(place.category, PlaceCategory.PARK)
        self.assertAlmostEqual(place.latitude, 12.9763)
        self.assertAlmostEqual(place.longitude, 77.6033)

    def test_way_is_normalized_using_its_center(self):
        places = PlacesService.normalize_elements(
            [
                way_element(
                    element_id=202,
                    name="Palace",
                    tourism="attraction",
                ),
            ],
        )

        self.assertEqual(len(places), 1)

        place = places[0]

        self.assertEqual(place.source_id, "way/202")
        self.assertEqual(place.category, PlaceCategory.ATTRACTION)
        self.assertAlmostEqual(place.latitude, 12.9719)
        self.assertAlmostEqual(place.longitude, 77.5946)

    def test_relation_is_normalized_using_its_center(self):
        places = PlacesService.normalize_elements(
            [
                relation_element(
                    element_id=303,
                    name="Heritage Zone",
                    historic="monument",
                ),
            ],
        )

        self.assertEqual(len(places), 1)

        place = places[0]

        self.assertEqual(place.source_id, "relation/303")
        self.assertEqual(place.category, PlaceCategory.MONUMENT)
        self.assertAlmostEqual(place.latitude, 12.9650)
        self.assertAlmostEqual(place.longitude, 77.6010)

    def test_element_without_name_is_skipped(self):
        places = PlacesService.normalize_elements(
            [
                {
                    "type": "node",
                    "id": 404,
                    "lat": 12.97,
                    "lon": 77.59,
                    "tags": {"tourism": "attraction"},
                },
            ],
        )

        self.assertEqual(places, [])

    def test_element_without_coordinates_is_skipped(self):
        places = PlacesService.normalize_elements(
            [
                {
                    "type": "way",
                    "id": 505,
                    "tags": {"name": "No Coordinates"},
                },
            ],
        )

        self.assertEqual(places, [])

    def test_element_with_out_of_range_coordinates_is_skipped(self):
        places = PlacesService.normalize_elements(
            [
                {
                    "type": "node",
                    "id": 606,
                    "lat": 999,
                    "lon": 77.59,
                    "tags": {"name": "Broken"},
                },
            ],
        )

        self.assertEqual(places, [])

    def test_duplicate_source_ids_are_removed(self):
        places = PlacesService.normalize_elements(
            [
                node_element(element_id=707, name="Museum"),
                node_element(element_id=707, name="Museum"),
                node_element(element_id=708, name="Museum Annexe"),
            ],
        )

        self.assertEqual(len(places), 2)

        self.assertEqual(
            [place.source_id for place in places],
            ["node/707", "node/708"],
        )

    def test_same_numeric_id_on_different_element_types_is_kept(self):
        # A node and a way can share a numeric OSM id. They are different
        # objects, so both must survive de-duplication.
        places = PlacesService.normalize_elements(
            [
                node_element(element_id=909, name="Node Place"),
                way_element(element_id=909, name="Way Place"),
            ],
        )

        self.assertEqual(len(places), 2)

        self.assertEqual(
            [place.source_id for place in places],
            ["node/909", "way/909"],
        )

    def test_results_are_capped_at_the_configured_limit(self):
        elements = [
            node_element(element_id=index, name="Place {0}".format(index))
            for index in range(1000, 1050)
        ]

        places = PlacesService.normalize_elements(elements)

        self.assertEqual(len(places), 20)

    def test_results_are_capped_at_an_explicit_smaller_limit(self):
        elements = [
            node_element(element_id=index, name="Place {0}".format(index))
            for index in range(1000, 1050)
        ]

        places = PlacesService.normalize_elements(elements, limit=5)

        self.assertEqual(len(places), 5)

    def test_sparse_provider_data_yields_none_for_missing_optionals(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=1111,
                    name="Bare Place",
                    tourism="attraction",
                ),
            ],
        )

        place = places[0]

        self.assertIsNone(place.address)
        self.assertIsNone(place.opening_hours)

    def test_address_is_built_from_addr_tags(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=1212,
                    name="Addressed Place",
                    tourism="attraction",
                    **{
                        "addr:housenumber": "12",
                        "addr:street": "MG Road",
                        "addr:city": "Bengaluru",
                        "addr:state": "Karnataka",
                        "addr:country": "IN",
                    },
                ),
            ],
        )

        self.assertEqual(
            places[0].address,
            "12 MG Road, Bengaluru, Karnataka, IN",
        )

    def test_full_address_tag_is_preferred(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=1313,
                    name="Addressed Place",
                    tourism="attraction",
                    **{
                        "addr:full": "1 MG Road, Bengaluru",
                        "addr:street": "MG Road",
                    },
                ),
            ],
        )

        self.assertEqual(
            places[0].address,
            "1 MG Road, Bengaluru",
        )

    def test_opening_hours_are_passed_through_unchanged(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=1414,
                    name="Timed Place",
                    tourism="attraction",
                    opening_hours="Mo-Fr 09:00-17:00",
                ),
            ],
        )

        self.assertEqual(
            places[0].opening_hours,
            "Mo-Fr 09:00-17:00",
        )

    def test_category_is_derived_from_the_element_tags(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=1515,
                    name="Museum",
                    tourism="museum",
                ),
                node_element(
                    element_id=1516,
                    name="Cafe",
                    amenity="cafe",
                ),
                node_element(
                    element_id=1517,
                    name="Temple",
                    amenity="place_of_worship",
                ),
                node_element(
                    element_id=1518,
                    name="Viewpoint",
                    tourism="viewpoint",
                ),
            ],
        )

        self.assertEqual(
            [place.category for place in places],
            [
                PlaceCategory.MUSEUM,
                PlaceCategory.CAFE,
                PlaceCategory.RELIGIOUS_SITE,
                PlaceCategory.VIEWPOINT,
            ],
        )

    def test_unknown_tag_combination_is_reported_as_other(self):
        places = PlacesService.normalize_elements(
            [
                node_element(
                    element_id=1616,
                    name="Unclassifiable",
                    tourism="artwork",
                ),
            ],
        )

        self.assertEqual(places[0].category, PlaceCategory.OTHER)

    def test_alternative_name_tag_is_used_when_name_is_missing(self):
        places = PlacesService.normalize_elements(
            [
                {
                    "type": "node",
                    "id": 1717,
                    "lat": 12.97,
                    "lon": 77.59,
                    "tags": {
                        "alt_name": "Alternate Name",
                        "tourism": "attraction",
                    },
                },
            ],
        )

        self.assertEqual(places[0].name, "Alternate Name")

    def test_element_without_tags_is_skipped(self):
        places = PlacesService.normalize_elements(
            [
                {
                    "type": "node",
                    "id": 1818,
                    "lat": 12.97,
                    "lon": 77.59,
                },
            ],
        )

        self.assertEqual(places, [])

    def test_non_dict_element_is_skipped(self):
        places = PlacesService.normalize_elements(["garbage"])

        self.assertEqual(places, [])

    def test_normalize_requires_a_list(self):
        with self.assertRaises(ValueError):
            PlacesService.normalize_elements("not-a-list")


class PlacesCacheTests(CacheClearingMixin, SimpleTestCase):
    """Caching behaviour for place search results."""

    def setUp(self):
        self.client = Mock()
        self.client.fetch_elements.return_value = [
            node_element(
                element_id=3001,
                name="Cubbon Park",
                leisure="park",
            ),
        ]

    def test_second_search_is_served_from_the_cache(self):
        first = PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        second = PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        # The provider was only asked once.
        self.client.fetch_elements.assert_called_once()

        self.assertEqual(first, second)

    def test_cached_places_are_equal_to_the_original(self):
        original = PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        cached = PlacesService.read_cache(
            PlacesService.cache_key(
                PlacesService.build_query(
                    bbox=BENGALURU,
                    limit=20,
                )
            )
        )

        self.assertEqual(cached, original)

    def test_an_empty_result_is_cached_too(self):
        self.client.fetch_elements.return_value = []

        first = PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        second = PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        # An empty list is a valid result, not a cache miss. If this were
        # treated as a miss the provider would be called on every request.
        self.client.fetch_elements.assert_called_once()

        self.assertEqual(first, [])
        self.assertEqual(second, [])

    def test_different_queries_use_different_cache_entries(self):
        PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        PlacesService.search_places(
            bbox=BENGALURU,
            limit=5,
            client=self.client,
        )

        self.assertEqual(self.client.fetch_elements.call_count, 2)

    def test_different_bounding_boxes_use_different_cache_entries(self):
        PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        PlacesService.search_places(
            bbox=BoundingBox(
                south=28.40,
                west=76.84,
                north=28.74,
                east=77.35,
            ),
            client=self.client,
        )

        self.assertEqual(self.client.fetch_elements.call_count, 2)

    def test_failures_are_not_cached(self):
        self.client.fetch_elements.side_effect = IntegrationError(
            "The places provider is temporarily unavailable."
        )

        with self.assertRaises(IntegrationError):
            PlacesService.search_places(
                bbox=BENGALURU,
                client=self.client,
            )

        # The next attempt must go to the provider again rather than
        # replaying a cached failure.
        self.client.fetch_elements.side_effect = None

        PlacesService.search_places(
            bbox=BENGALURU,
            client=self.client,
        )

        self.assertEqual(self.client.fetch_elements.call_count, 2)

    def test_caching_can_be_disabled(self):
        with patch(
            "backend.apps.integrations.services.places_service."
            "PLACES_CACHE_TIMEOUT",
            0,
        ):
            PlacesService.search_places(
                bbox=BENGALURU,
                client=self.client,
            )

            PlacesService.search_places(
                bbox=BENGALURU,
                client=self.client,
            )

        self.assertEqual(self.client.fetch_elements.call_count, 2)

    def test_cache_keys_are_stable_and_distinct(self):
        first = PlacesService.cache_key("query-one")
        second = PlacesService.cache_key("query-one")
        third = PlacesService.cache_key("query-two")

        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertTrue(first.startswith("places:v1:"))


class PlacesSearchTests(CacheClearingMixin, SimpleTestCase):

    def test_search_uses_the_client_and_returns_places(self):
        client = Mock()
        client.fetch_elements.return_value = [
            node_element(
                element_id=2001,
                name="Cubbon Park",
                leisure="park",
            ),
        ]

        places = PlacesService.search_places(
            bbox=BENGALURU,
            client=client,
        )

        self.assertEqual(len(places), 1)
        self.assertIsInstance(places[0], Place)

        query = client.fetch_elements.call_args.args[0]

        self.assertIn("(12.9,77.5,12.99,77.65)", query)
        self.assertIn("out center 20;", query)

    def test_search_with_no_results_returns_empty_list(self):
        client = Mock()
        client.fetch_elements.return_value = []

        places = PlacesService.search_places(
            bbox=BENGALURU,
            client=client,
        )

        self.assertEqual(places, [])

    def test_search_passes_the_requested_limit_to_the_query(self):
        client = Mock()
        client.fetch_elements.return_value = []

        PlacesService.search_places(
            bbox=BENGALURU,
            limit=7,
            client=client,
        )

        query = client.fetch_elements.call_args.args[0]

        self.assertIn("out center 7;", query)

    def test_search_restricts_the_query_to_requested_categories(self):
        client = Mock()
        client.fetch_elements.return_value = []

        PlacesService.search_places(
            bbox=BENGALURU,
            categories=[PlaceCategory.MUSEUM],
            client=client,
        )

        query = client.fetch_elements.call_args.args[0]

        self.assertIn('nwr["tourism"="museum"]', query)
        self.assertNotIn('nwr["leisure"="park"]', query)
