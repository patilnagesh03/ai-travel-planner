"""Tests for the environment-reading helpers.

These are plain unit tests: no database, no settings reload. They pin down
the rules that decide whether the project is allowed to start.
"""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from backend.environment import (
    DEVELOPMENT_SECRET_KEY,
    PLACEHOLDER_SECRET_KEYS,
    resolve_allowed_hosts,
    resolve_cors_origins,
    resolve_csrf_trusted_origins,
    resolve_secret_key,
    resolve_security_settings,
    split_csv,
)


class SplitCsvTests(SimpleTestCase):

    def test_none_becomes_an_empty_list(self):
        self.assertEqual(split_csv(None), [])

    def test_empty_string_becomes_an_empty_list(self):
        self.assertEqual(split_csv(""), [])

    def test_items_are_trimmed_and_blanks_dropped(self):
        self.assertEqual(
            split_csv("  a , b ,, c "),
            ["a", "b", "c"],
        )

    def test_single_item(self):
        self.assertEqual(split_csv("only"), ["only"])


class ResolveSecretKeyTests(SimpleTestCase):

    def test_development_without_a_key_gets_the_development_key(self):
        self.assertEqual(
            resolve_secret_key("", debug=True),
            DEVELOPMENT_SECRET_KEY,
        )

    def test_development_keeps_a_provided_key(self):
        self.assertEqual(
            resolve_secret_key("dev-key", debug=True),
            "dev-key",
        )

    def test_the_key_is_trimmed(self):
        self.assertEqual(
            resolve_secret_key("   spaced-key   ", debug=True),
            "spaced-key",
        )

    def test_production_without_a_key_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            resolve_secret_key("", debug=False)

        self.assertIn("SECRET_KEY is not set", str(caught.exception))

    def test_production_rejects_the_development_key(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key(DEVELOPMENT_SECRET_KEY, debug=False)

    def test_production_rejects_any_django_insecure_key(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("django-insecure-something-else", debug=False)

    def test_production_rejects_every_placeholder(self):
        for placeholder in PLACEHOLDER_SECRET_KEYS:
            with self.subTest(placeholder=placeholder):
                with self.assertRaises(ImproperlyConfigured):
                    resolve_secret_key(placeholder, debug=False)

    def test_production_rejects_placeholders_case_insensitively(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("CHANGEME", debug=False)

    def test_production_accepts_a_real_key(self):
        key = "a-real-production-key-that-is-not-a-placeholder"
        self.assertEqual(resolve_secret_key(key, debug=False), key)

    def test_error_message_says_how_to_generate_a_key(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            resolve_secret_key("", debug=False)

        self.assertIn("get_random_secret_key", str(caught.exception))


class ResolveAllowedHostsTests(SimpleTestCase):

    def test_explicit_hosts_are_used(self):
        self.assertEqual(
            resolve_allowed_hosts("example.com, www.example.com", debug=True),
            ["example.com", "www.example.com"],
        )

    def test_development_falls_back_to_local_hosts(self):
        hosts = resolve_allowed_hosts("", debug=True)

        self.assertIn("127.0.0.1", hosts)
        self.assertIn("localhost", hosts)

    def test_production_without_hosts_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            resolve_allowed_hosts("", debug=False)

        self.assertIn("ALLOWED_HOSTS is empty", str(caught.exception))


class ResolveCorsOriginsTests(SimpleTestCase):

    def test_explicit_origins_are_used(self):
        self.assertEqual(
            resolve_cors_origins(
                "https://app.example.com,https://admin.example.com",
                debug=True,
            ),
            ["https://app.example.com", "https://admin.example.com"],
        )

    def test_development_falls_back_to_the_vite_origin(self):
        origins = resolve_cors_origins("", debug=True)

        self.assertIn("http://localhost:5173", origins)

    def test_production_without_origins_allows_none(self):
        self.assertEqual(resolve_cors_origins("", debug=False), [])


class ResolveCsrfTrustedOriginsTests(SimpleTestCase):

    def test_an_explicit_list_wins(self):
        self.assertEqual(
            resolve_csrf_trusted_origins(
                "https://admin.example.com",
                ["https://app.example.com"],
            ),
            ["https://admin.example.com"],
        )

    def test_cors_origins_are_the_default(self):
        cors = ["https://app.example.com", "https://admin.example.com"]

        self.assertEqual(
            resolve_csrf_trusted_origins("", cors),
            cors,
        )

    def test_the_default_is_a_copy(self):
        cors = ["https://app.example.com"]

        result = resolve_csrf_trusted_origins("", cors)
        result.append("https://evil.example.com")

        self.assertEqual(cors, ["https://app.example.com"])

    def test_a_blank_list_falls_back(self):
        self.assertEqual(
            resolve_csrf_trusted_origins(" , ", ["https://app.example.com"]),
            ["https://app.example.com"],
        )


class ResolveSecuritySettingsTests(SimpleTestCase):

    def test_development_disables_transport_security(self):
        values = resolve_security_settings(debug=True)

        self.assertFalse(values["SECURE_SSL_REDIRECT"])
        self.assertFalse(values["SESSION_COOKIE_SECURE"])
        self.assertFalse(values["CSRF_COOKIE_SECURE"])
        self.assertEqual(values["SECURE_HSTS_SECONDS"], 0)
        self.assertFalse(values["SECURE_HSTS_INCLUDE_SUBDOMAINS"])
        self.assertFalse(values["SECURE_HSTS_PRELOAD"])

    def test_production_enables_transport_security(self):
        values = resolve_security_settings(debug=False)

        self.assertTrue(values["SECURE_SSL_REDIRECT"])
        self.assertTrue(values["SESSION_COOKIE_SECURE"])
        self.assertTrue(values["CSRF_COOKIE_SECURE"])
        self.assertEqual(values["SECURE_HSTS_SECONDS"], 31536000)
        self.assertTrue(values["SECURE_HSTS_INCLUDE_SUBDOMAINS"])
        self.assertTrue(values["SECURE_HSTS_PRELOAD"])
