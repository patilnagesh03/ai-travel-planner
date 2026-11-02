from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from backend.apps.expenses.models import Expense
from backend.apps.notifications.enums import NotificationKind
from backend.apps.notifications.models import Notification
from backend.apps.notifications.services import NotificationService
from backend.apps.notifications.services.notification_service import LIST_LIMIT
from backend.apps.trips.models import Trip


TODAY = timezone.localdate()


def create_user(email="traveller@example.com"):
    return get_user_model().objects.create_user(
        email=email,
        password="TestPass123!",
        first_name="Test",
        last_name="Traveller",
    )


def create_trip(user, start_in_days=20, length=4, budget="10000.00", **overrides):
    start_date = TODAY + timedelta(days=start_in_days)

    values = {
        "user": user,
        "title": "Jaipur Trip",
        "destination": "Jaipur",
        "start_date": start_date,
        "end_date": start_date + timedelta(days=length - 1),
        "budget": Decimal(budget),
        "currency": "INR",
        "travelers": 2,
    }

    values.update(overrides)

    return Trip.objects.create(**values)


def add_expense(trip, amount):
    return Expense.objects.create(
        trip=trip,
        title="Something",
        amount=Decimal(amount),
    )


class BudgetNotificationTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.trip = create_trip(self.user, start_in_days=20)

    def test_crossing_the_budget_creates_one_notification(self):
        add_expense(self.trip, "11000.00")

        created = NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(len(created), 1)
        self.assertEqual(
            created[0].kind,
            NotificationKind.BUDGET_EXCEEDED,
        )
        self.assertIn("11,000.00", created[0].message)
        self.assertIn("10,000.00", created[0].message)

    def test_spending_exactly_the_budget_is_not_over_budget(self):
        add_expense(self.trip, "10000.00")

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertFalse(
            Notification.objects.filter(
                kind=NotificationKind.BUDGET_EXCEEDED
            ).exists()
        )

    def test_syncing_twice_does_not_duplicate(self):
        add_expense(self.trip, "11000.00")

        NotificationService.sync_for_user(self.user, today=TODAY)
        created = NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(created, [])
        self.assertEqual(Notification.objects.count(), 1)

    def test_a_new_budget_re_arms_the_notification(self):
        add_expense(self.trip, "11000.00")

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.trip.budget = Decimal("9000.00")
        self.trip.save(update_fields=["budget"])

        created = NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(len(created), 1)
        self.assertEqual(Notification.objects.count(), 2)

    def test_another_users_budget_is_not_evaluated(self):
        stranger = create_user("stranger@example.com")
        stranger_trip = create_trip(stranger, start_in_days=20)

        add_expense(stranger_trip, "12000.00")

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertFalse(Notification.objects.exists())


class ReminderNotificationTests(TestCase):

    def setUp(self):
        self.user = create_user()

    def kind_count(self, kind):
        return Notification.objects.filter(kind=kind).count()

    def test_a_trip_starting_today_is_announced(self):
        create_trip(self.user, start_in_days=0)

        NotificationService.sync_for_user(self.user, today=TODAY)

        notification = Notification.objects.get(
            kind=NotificationKind.TRIP_SOON
        )

        self.assertIn("starts today", notification.message)

    def test_a_trip_starting_tomorrow_is_announced(self):
        create_trip(self.user, start_in_days=1)

        NotificationService.sync_for_user(self.user, today=TODAY)

        notification = Notification.objects.get(
            kind=NotificationKind.TRIP_SOON
        )

        self.assertIn("starts tomorrow", notification.message)

    def test_a_trip_within_the_reminder_window_is_announced(self):
        create_trip(self.user, start_in_days=5)

        NotificationService.sync_for_user(self.user, today=TODAY)

        notification = Notification.objects.get(
            kind=NotificationKind.TRIP_SOON
        )

        self.assertIn("in 5 days", notification.message)

    def test_a_trip_further_out_is_not_announced_yet(self):
        create_trip(self.user, start_in_days=8)

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(self.kind_count(NotificationKind.TRIP_SOON), 0)

    def test_a_recently_ended_trip_gets_a_reminder(self):
        create_trip(self.user, start_in_days=-6, length=4)

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(self.kind_count(NotificationKind.TRIP_ENDED), 1)

    def test_a_long_finished_trip_is_not_announced(self):
        create_trip(self.user, start_in_days=-120, length=4)

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(self.kind_count(NotificationKind.TRIP_ENDED), 0)

    def test_moving_a_trip_re_arms_its_reminder(self):
        trip = create_trip(self.user, start_in_days=30)

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(self.kind_count(NotificationKind.TRIP_SOON), 0)

        trip.start_date = TODAY + timedelta(days=2)
        trip.end_date = trip.start_date + timedelta(days=3)
        trip.save(update_fields=["start_date", "end_date"])

        NotificationService.sync_for_user(self.user, today=TODAY)

        self.assertEqual(self.kind_count(NotificationKind.TRIP_SOON), 1)


class NotificationStateTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.notification = Notification.objects.create(
            user=self.user,
            kind=NotificationKind.TRIP_SOON,
            title="Trip starting soon",
            message="Packing time.",
            dedupe_key="trip-soon:manual",
        )

    def test_marking_as_read_records_when(self):
        notification = NotificationService.mark_read(
            self.user,
            self.notification.id,
        )

        self.assertIsNotNone(notification.read_at)
        self.assertTrue(notification.is_read)

    def test_marking_as_read_is_idempotent(self):
        first = NotificationService.mark_read(
            self.user,
            self.notification.id,
        )
        second = NotificationService.mark_read(
            self.user,
            self.notification.id,
        )

        self.assertEqual(first.read_at, second.read_at)

    def test_mark_all_read_only_touches_the_callers_unread_items(self):
        stranger = create_user("stranger@example.com")

        strangers = Notification.objects.create(
            user=stranger,
            kind=NotificationKind.TRIP_SOON,
            title="Trip starting soon",
            message="Packing time.",
            dedupe_key="trip-soon:manual",
        )

        updated = NotificationService.mark_all_read(self.user)

        self.assertEqual(updated, 1)
        self.assertEqual(NotificationService.unread_count(self.user), 0)
        self.assertEqual(NotificationService.unread_count(stranger), 1)

        strangers.refresh_from_db()

        self.assertIsNone(strangers.read_at)

    def test_the_list_can_be_limited_to_unread(self):
        NotificationService.mark_read(self.user, self.notification.id)

        Notification.objects.create(
            user=self.user,
            kind=NotificationKind.BUDGET_EXCEEDED,
            title="Budget exceeded",
            message="Over budget.",
            dedupe_key="budget-exceeded:manual",
        )

        unread = NotificationService.list_for_user(
            self.user,
            unread_only=True,
        )

        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0].title, "Budget exceeded")

    def test_the_list_is_capped(self):
        for index in range(55):
            Notification.objects.create(
                user=self.user,
                kind=NotificationKind.TRIP_SOON,
                title=f"Notice {index}",
                message="Packing time.",
                dedupe_key=f"trip-soon:manual:{index}",
            )

        self.assertEqual(
            len(NotificationService.list_for_user(self.user)),
            LIST_LIMIT,
        )

    def test_deleting_removes_only_the_callers_item(self):
        stranger = create_user("stranger@example.com")

        strangers = Notification.objects.create(
            user=stranger,
            kind=NotificationKind.TRIP_SOON,
            title="Their notice",
            message="Packing time.",
            dedupe_key="trip-soon:theirs",
        )

        NotificationService.delete(self.user, self.notification.id)

        self.assertFalse(
            Notification.objects.filter(id=self.notification.id).exists()
        )
        self.assertTrue(
            Notification.objects.filter(id=strangers.id).exists()
        )
