"""Tests for the deployment health endpoint."""

from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):

    url = "/health"

    def test_reports_ok_when_the_database_is_reachable(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "database": "up"},
        )

    def test_accepts_a_trailing_slash(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)

    def test_accepts_head_requests(self):
        response = self.client.head(self.url)

        self.assertEqual(response.status_code, 200)

    def test_rejects_unsafe_methods(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_does_not_require_authentication(self):
        # The default test client is anonymous; a probe cannot log in.
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_reports_unavailable_when_the_database_is_down(self):
        with patch(
            "backend.views.connection.cursor",
            side_effect=OperationalError("database is down"),
        ):
            with patch("backend.views.logger.exception") as logged:
                response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable", "database": "down"},
        )
        logged.assert_called_once()

    def test_failure_does_not_leak_the_exception(self):
        with patch(
            "backend.views.connection.cursor",
            side_effect=OperationalError("secret connection string"),
        ):
            with patch("backend.views.logger.exception"):
                response = self.client.get(self.url)

        self.assertNotIn("secret", response.content.decode().lower())

    def test_reverse_resolves_the_probe_url(self):
        self.assertEqual(reverse("health"), "/health")
