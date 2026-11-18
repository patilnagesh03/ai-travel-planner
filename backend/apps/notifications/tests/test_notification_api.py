import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.notifications.enums import NotificationKind
from backend.apps.notifications.models import Notification
from backend.apps.trips.models import Trip


TODAY = timezone.localdate()


def create_user(email="traveller@example.com"):
    return get_user_model().objects.create_user(
        email=email,
        password="TestPass123!",
        first_name="Test",
        last_name="Traveller",
    )


def create_trip(user, start_in_days=20):
    start_date = TODAY + timedelta(days=start_in_days)

    return Trip.objects.create(
        user=user,
        title="Jaipur Trip",
        destination="Jaipur",
        start_date=start_date,
        end_date=start_date + timedelta(days=3),
        budget=Decimal("10000.00"),
        currency="INR",
        travelers=2,
    )


def create_notification(user, title="Trip starting soon", dedupe_key="manual"):
    return Notification.objects.create(
        user=user,
        kind=NotificationKind.TRIP_SOON,
        title=title,
        message="Packing time.",
        dedupe_key=dedupe_key,
    )


class NotificationApiTests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("notification-list")
        self.count_url = reverse("notification-unread-count")
        self.read_all_url = reverse("notification-read-all")

    def read_url(self, notification_id):
        return reverse(
            "notification-read",
            kwargs={"notification_id": notification_id},
        )

    def detail_url(self, notification_id):
        return reverse(
            "notification-detail",
            kwargs={"notification_id": notification_id},
        )

    def test_the_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_the_list_returns_an_envelope(self):
        create_notification(self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Trip starting soon")
        self.assertFalse(response.data["data"][0]["is_read"])

    def test_the_list_syncs_pending_reminders(self):
        create_trip(self.user, start_in_days=2)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(
            response.data["data"][0]["kind"],
            NotificationKind.TRIP_SOON,
        )

    def test_the_list_can_exclude_read_notifications(self):
        read = create_notification(self.user, dedupe_key="read")
        read.read_at = timezone.now()
        read.save(update_fields=["read_at"])

        create_notification(
            self.user,
            title="Unread notice",
            dedupe_key="unread",
        )

        response = self.client.get(self.list_url, {"unread": "true"})

        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Unread notice")

    def test_the_unread_count_counts_only_unread_items(self):
        create_notification(self.user, dedupe_key="one")
        create_notification(self.user, dedupe_key="two")

        response = self.client.get(self.count_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread"], 2)

    def test_marking_as_read_updates_the_badge(self):
        notification = create_notification(self.user)

        response = self.client.post(self.read_url(notification.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["is_read"])

        self.assertEqual(
            self.client.get(self.count_url).data["data"]["unread"],
            0,
        )

    def test_marking_as_read_twice_is_harmless(self):
        notification = create_notification(self.user)

        first = self.client.post(self.read_url(notification.id))
        second = self.client.post(self.read_url(notification.id))

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            first.data["data"]["read_at"],
            second.data["data"]["read_at"],
        )

    def test_read_all_reports_how_many_changed(self):
        create_notification(self.user, dedupe_key="one")
        create_notification(self.user, dedupe_key="two")

        response = self.client.post(self.read_all_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["updated"], 2)
        self.assertEqual(
            self.client.get(self.count_url).data["data"]["unread"],
            0,
        )

    def test_a_notification_can_be_deleted(self):
        notification = create_notification(self.user)

        response = self.client.delete(self.detail_url(notification.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(Notification.objects.exists())

    def test_another_users_notification_is_a_404(self):
        stranger = create_user("stranger@example.com")
        notification = create_notification(stranger)

        self.assertEqual(
            self.client.post(self.read_url(notification.id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(self.detail_url(notification.id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_a_missing_notification_is_a_404(self):
        missing_id = uuid.uuid4()

        self.assertEqual(
            self.client.post(self.read_url(missing_id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(self.detail_url(missing_id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_the_list_only_contains_the_callers_notifications(self):
        stranger = create_user("stranger@example.com")
        create_notification(stranger, title="Their notice")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])
