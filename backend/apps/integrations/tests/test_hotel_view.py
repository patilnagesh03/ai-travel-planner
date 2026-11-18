"""
API tests for accommodation discovery.

The provider is mocked, so the suite does not depend on Overpass being
reachable. The tests still exercise the real query builder, normalization,
distance sorting and error mapping.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from requests.exceptions import ConnectionError as RequestsConnectionError
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.integrations.tests.helpers import CacheClearingMixin
from backend.apps.trips.models import Trip


POST_TARGET = "backend.apps.integrations.clients.overpass_client.requests.post"


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


HOTEL_PAYLOAD = {
    "version": 0.6,
    "generator": "Overpass API",
    "elements": [
        {
            "type": "node",
            "id": 11,
            "lat": 13.10,
            "lon": 77.70,
            "tags": {"name": "Far Hotel", "tourism": "hotel"},
        },
        {
            "type": "way",
            "id": 12,
            "center": {"lat": 12.991, "lon": 77.601},
            "tags": {
                "name": "Near Guest House",
                "tourism": "guest_house",
                "addr:street": "1 River Road",
            },
        },
    ],
}


class TripHotelSearchApiTests(CacheClearingMixin, APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="owner@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Owner",
        )

        self.other_user = user_model.objects.create_user(
            email="stranger@example.com",
            password="TestPass123!",
            first_name="Trip",
            last_name="Stranger",
        )

        self.trip = Trip.objects.create(
            user=self.user,
            title="Karnataka Getaway",
            destination="Bengaluru",
            origin="Delhi",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 15),
            budget=Decimal("50000.00"),
            currency="INR",
            travelers=2,
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse(
            "trip-hotels",
            kwargs={"trip_id": self.trip.id},
        )

    def test_returns_hotels_sorted_by_distance(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=HOTEL_PAYLOAD),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        hotels = response.data["data"]["hotels"]

        self.assertEqual(
            [hotel["name"] for hotel in hotels],
            ["Near Guest House", "Far Hotel"],
        )
        self.assertLess(hotels[0]["distance_km"], hotels[1]["distance_km"])

    def test_hotel_payload_includes_place_fields_and_distance(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=HOTEL_PAYLOAD),
        ):
            response = self.client.get(self.url)

        hotel = response.data["data"]["hotels"][0]

        self.assertEqual(hotel["source"], "openstreetmap")
        self.assertEqual(hotel["category"], "guest_house")
        self.assertEqual(hotel["address"], "1 River Road")
        self.assertIn("distance_km", hotel)

    def test_only_accommodation_categories_are_queried(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=HOTEL_PAYLOAD),
        ) as mocked_post:
            self.client.get(self.url)

        query = mocked_post.call_args.kwargs["data"]["data"]

        self.assertIn('nwr["tourism"="hotel"]', query)
        self.assertIn('nwr["tourism"="guest_house"]', query)
        self.assertIn('nwr["tourism"="hostel"]', query)
        self.assertIn('nwr["tourism"="apartment"]', query)

        self.assertNotIn('nwr["tourism"="attraction"]', query)
        self.assertNotIn('nwr["amenity"="restaurant"]', query)

    def test_the_booking_link_and_destination_are_returned(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=HOTEL_PAYLOAD),
        ):
            response = self.client.get(self.url)

        data = response.data["data"]

        self.assertEqual(data["destination"]["name"], "Bengaluru")
        self.assertIn("booking.com", data["booking_url"])
        self.assertIn("OpenStreetMap", data["attribution"])

    def test_the_limit_parameter_is_honoured(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=HOTEL_PAYLOAD),
        ):
            response = self.client.get(self.url, {"limit": 1})

        self.assertEqual(
            len(response.data["data"]["hotels"]),
            1,
        )

    def test_an_invalid_limit_is_rejected(self):
        response = self.client.get(self.url, {"limit": 0})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_a_destination_above_the_maximum_limit_is_rejected(self):
        response = self.client.get(self.url, {"limit": 21})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_an_unsupported_destination_is_rejected(self):
        self.trip.destination = "Kumbakonam"
        self.trip.save()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("Kumbakonam", response.data["message"])

    def test_a_provider_outage_is_reported_as_503(self):
        with patch(
            POST_TARGET,
            side_effect=RequestsConnectionError("connection refused"),
        ):
            response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertIn(
            "accommodation provider",
            response.data["message"],
        )

    def test_provider_errors_do_not_leak_details(self):
        with patch(
            POST_TARGET,
            return_value=build_response(
                status_code=400,
                payload={"remark": "runtime error: parse error"},
            ),
        ):
            response = self.client.get(self.url)

        self.assertNotIn("parse error", response.data["message"])

    def test_another_users_trip_is_not_found(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_a_missing_trip_is_not_found(self):
        url = reverse(
            "trip-hotels",
            kwargs={"trip_id": uuid.uuid4()},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_the_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
