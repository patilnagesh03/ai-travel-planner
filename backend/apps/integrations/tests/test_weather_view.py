"""
API tests for the trip weather endpoint.

The provider is mocked, so these tests never call Open-Meteo.
"""

from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.integrations.tests.helpers import CacheClearingMixin
from backend.apps.trips.models import Trip


GET_TARGET = "backend.apps.integrations.clients.open_meteo_client.requests.get"


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


def build_payload(start, days=16):
    dates = [
        (start + timedelta(days=index)).isoformat()
        for index in range(days)
    ]

    return {
        "latitude": 26.915,
        "longitude": 75.795,
        "timezone": "Asia/Kolkata",
        "daily": {
            "time": dates,
            "weather_code": [2 for _ in range(days)],
            "temperature_2m_max": [30.0 for _ in range(days)],
            "temperature_2m_min": [18.0 for _ in range(days)],
            "precipitation_probability_max": [20 for _ in range(days)],
            "wind_speed_10m_max": [11.0 for _ in range(days)],
            "sunrise": [
                "{date}T06:24".format(date=value) for value in dates
            ],
            "sunset": [
                "{date}T17:52".format(date=value) for value in dates
            ],
        },
    }


class TripWeatherApiTests(CacheClearingMixin, APITestCase):

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="weather@example.com",
            password="TestPass123!",
            first_name="Weather",
            last_name="Tester",
        )

        self.other_user = user_model.objects.create_user(
            email="other@example.com",
            password="TestPass123!",
            first_name="Other",
            last_name="Tester",
        )

        today = timezone.localdate()

        self.trip = Trip.objects.create(
            user=self.user,
            title="Jaipur trip",
            destination="Jaipur",
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=3),
            budget=50000,
        )

        self.client.force_authenticate(user=self.user)

        self.url = reverse("trip-weather", args=[self.trip.id])

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_another_users_trip_is_not_found(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_forecast_is_returned_for_the_trip_dates(self):
        today = timezone.localdate()

        with patch(
            GET_TARGET,
            return_value=build_response(payload=build_payload(today)),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        data = response.data["data"]

        self.assertEqual(data["destination"]["name"], "Jaipur")
        self.assertEqual(data["trip_days"], 3)
        self.assertEqual(data["covered_days"], 3)
        self.assertEqual(len(data["days"]), 3)
        self.assertEqual(
            data["days"][0]["date"],
            (today + timedelta(days=1)).isoformat(),
        )

    def test_an_unsupported_destination_returns_a_clear_400(self):
        self.trip.destination = "Kumbakonam"
        self.trip.save(update_fields=["destination"])

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("Kumbakonam", response.data["message"])

    def test_a_provider_timeout_returns_503(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.Timeout,
        ):
            response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertIn("weather provider", response.data["message"])

    def test_a_rate_limited_provider_returns_429_and_retry_after(self):
        with patch(
            GET_TARGET,
            return_value=build_response(
                status_code=429,
                headers={"Retry-After": "45"},
            ),
        ):
            response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.assertEqual(response["Retry-After"], "45")
