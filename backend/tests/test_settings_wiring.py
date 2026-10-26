"""Tests that the settings and middleware are actually wired together.

The helper tests prove the rules; these prove the rules are used.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from backend.environment import PLACEHOLDER_SECRET_KEYS


class SettingsWiringTests(SimpleTestCase):

    def test_cors_headers_app_is_installed(self):
        self.assertIn("corsheaders", settings.INSTALLED_APPS)

    def test_cors_middleware_runs_before_common_middleware(self):
        middleware = list(settings.MIDDLEWARE)

        cors = middleware.index("corsheaders.middleware.CorsMiddleware")
        common = middleware.index("django.middleware.common.CommonMiddleware")

        self.assertLess(cors, common)

    def test_secret_key_is_configured_and_is_not_a_placeholder(self):
        self.assertTrue(settings.SECRET_KEY)

        self.assertNotIn(
            settings.SECRET_KEY.lower(),
            PLACEHOLDER_SECRET_KEYS,
        )

    def test_base_dir_is_the_django_project_directory(self):
        # .env, media/ and staticfiles/ live next to settings.py.
        self.assertEqual(settings.BASE_DIR.name, "backend")

    def test_static_configuration(self):
        # Django normalises URL settings to a leading slash.
        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertEqual(settings.STATIC_ROOT, settings.BASE_DIR / "staticfiles")

    def test_media_configuration(self):
        self.assertEqual(settings.MEDIA_URL, "/media/")
        self.assertEqual(settings.MEDIA_ROOT, settings.BASE_DIR / "media")

    def test_static_root_and_media_root_are_paths(self):
        self.assertIsInstance(settings.STATIC_ROOT, Path)
        self.assertIsInstance(settings.MEDIA_ROOT, Path)

    def test_allowed_hosts_is_resolved_to_a_non_empty_list(self):
        # The test runner forces DEBUG=False, so this checks the value that
        # was resolved from the environment when settings were imported.
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)
        self.assertTrue(settings.ALLOWED_HOSTS)

    def test_cors_origins_are_explicit_not_a_wildcard(self):
        # A wildcard origin cannot be combined with credentials and would
        # let any site call the API, so it must never be configured.
        self.assertNotIn("*", settings.CORS_ALLOWED_ORIGINS)


@override_settings(CORS_ALLOWED_ORIGINS=["https://app.example.com"])
class CorsHeaderTests(TestCase):
    """The middleware must actually answer a browser preflight."""

    url = "/api/v1/ai/status/"

    def test_allowed_origin_is_echoed(self):
        response = self.client.get(
            self.url,
            HTTP_ORIGIN="https://app.example.com",
        )

        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "https://app.example.com",
        )

    def test_unknown_origin_is_not_allowed(self):
        response = self.client.get(
            self.url,
            HTTP_ORIGIN="https://evil.example.com",
        )

        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_preflight_request_is_answered(self):
        response = self.client.options(
            self.url,
            HTTP_ORIGIN="https://app.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )

        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "https://app.example.com",
        )

    def test_authorization_header_is_allowed(self):
        # The frontend authenticates with a JWT in the Authorization header,
        # so the preflight has to permit it.
        response = self.client.options(
            self.url,
            HTTP_ORIGIN="https://app.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
        )

        allowed = response.headers.get("Access-Control-Allow-Headers", "")

        self.assertIn("authorization", allowed.lower())
