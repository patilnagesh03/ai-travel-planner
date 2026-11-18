"""Regression tests for the refresh-token endpoint.

Unusable refresh tokens used to fall through the view's catch-all handler and
become 500 responses: a malformed, expired or blacklisted token raised
SimpleJWT's ``TokenError``, and a token whose account had been deleted raised
``User.DoesNotExist``. Both are client-side authentication failures and must
answer 401.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


def create_user(email="refresh@example.com", **overrides):
    values = {
        "email": email,
        "password": "TestPass123!",
        "first_name": "Refresh",
        "last_name": "Tester",
    }

    values.update(overrides)

    return get_user_model().objects.create_user(**values)


class RefreshTokenApiTests(APITestCase):

    def setUp(self):
        self.url = reverse("refresh-token")
        self.user = create_user()
        self.token = RefreshToken.for_user(self.user)

    def post(self, refresh=None):
        payload = {}

        if refresh is not None:
            payload["refresh"] = refresh

        return self.client.post(self.url, payload, format="json")

    # SUCCESS -------------------------------------------------------------

    def test_a_valid_token_is_refreshed(self):
        response = self.post(str(self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["access"])
        self.assertTrue(response.data["data"]["refresh"])

    def test_rotation_returns_a_new_refresh_token(self):
        response = self.post(str(self.token))

        self.assertNotEqual(
            response.data["data"]["refresh"],
            str(self.token),
        )

    def test_the_rotated_token_works_once_and_then_stops(self):
        rotated = self.post(str(self.token)).data["data"]["refresh"]

        # Rotation blacklists the previous token...
        self.assertEqual(
            self.post(str(self.token)).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        # ...while the new one still works.
        self.assertEqual(
            self.post(rotated).status_code,
            status.HTTP_200_OK,
        )

    # CLIENT ERRORS -------------------------------------------------------

    def test_a_malformed_token_is_rejected_with_401(self):
        response = self.post("not-a-real-token")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            response.data["detail"],
            "Invalid or expired refresh token.",
        )

    def test_an_expired_token_is_rejected_with_401(self):
        self.token.set_exp(lifetime=timedelta(seconds=-1))

        response = self.post(str(self.token))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_a_blacklisted_token_is_rejected_with_401(self):
        self.token.blacklist()

        response = self.post(str(self.token))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_a_token_for_a_deleted_user_is_rejected_with_401(self):
        token = str(self.token)
        self.user.delete()

        response = self.post(token)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            response.data["detail"],
            "Invalid or expired refresh token.",
        )

    def test_a_token_for_an_inactive_user_is_rejected_with_401(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.post(str(self.token))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_a_missing_token_is_still_a_400(self):
        response = self.post()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("refresh", response.data)

    def test_client_errors_are_not_logged_as_server_errors(self):
        # The view logs ERROR (and returns 500) only for genuinely
        # unexpected failures.
        with self.assertNoLogs(
            "backend.apps.authentication.views.refresh_token_view",
            level="ERROR",
        ):
            self.post("not-a-real-token")
            self.user.delete()
            self.post(str(self.token))
