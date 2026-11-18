from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from backend.apps.expenses.models import Expense
from backend.apps.notifications.models import Notification
from backend.apps.trips.models import Trip


def create_user(email="traveller@example.com"):
    return get_user_model().objects.create_user(
        email=email,
        password="TestPass123!",
        first_name="Test",
        last_name="Traveller",
    )


def create_trip(user, budget="10000.00", **overrides):
    values = {
        "user": user,
        "title": "Jaipur Trip",
        "destination": "Jaipur",
        "start_date": timezone.localdate() + timedelta(days=20),
        "end_date": timezone.localdate() + timedelta(days=24),
        "budget": Decimal(budget),
        "currency": "INR",
        "travelers": 2,
    }

    values.update(overrides)

    return Trip.objects.create(**values)


class ExpenseApiTests(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.trip = create_trip(self.user)
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse(
            "trip-expense-list-create",
            kwargs={"trip_id": self.trip.id},
        )

        self.summary_url = reverse(
            "trip-expense-summary",
            kwargs={"trip_id": self.trip.id},
        )

    def detail_url(self, expense_id):
        return reverse(
            "trip-expense-detail",
            kwargs={
                "trip_id": self.trip.id,
                "expense_id": expense_id,
            },
        )

    def create_expense(self, **overrides):
        payload = {
            "title": "Auto to Amber Fort",
            "category": "transport",
            "amount": "450.00",
            "spent_on": self.trip.start_date.isoformat(),
        }

        payload.update(overrides)

        # `None` means "leave the field out" so the model default applies.
        payload = {
            key: value
            for key, value in payload.items()
            if value is not None
        }

        return self.client.post(self.list_url, payload)

    # CREATING -----------------------------------------------------------

    def test_an_expense_can_be_recorded(self):
        response = self.create_expense()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["title"], "Auto to Amber Fort")
        self.assertEqual(response.data["data"]["amount"], "450.00")
        self.assertTrue(
            Expense.objects.filter(trip=self.trip).exists()
        )

    def test_the_trip_is_derived_from_the_url_not_the_body(self):
        other_trip = create_trip(self.user, title="Other trip")

        response = self.create_expense(trip=other_trip.id)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            str(Expense.objects.get().trip_id),
            str(self.trip.id),
        )

    def test_category_defaults_to_other(self):
        response = self.create_expense(category=None)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["data"]["category"], "other")

    def test_spent_on_defaults_to_today(self):
        response = self.create_expense(spent_on=None)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["data"]["spent_on"],
            timezone.localdate().isoformat(),
        )

    def test_a_zero_amount_is_rejected(self):
        response = self.create_expense(amount="0")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("amount", response.data)

    def test_a_negative_amount_is_rejected(self):
        response = self.create_expense(amount="-10.00")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(Expense.objects.exists())

    def test_a_blank_title_is_rejected(self):
        response = self.create_expense(title="   ")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("title", response.data)

    def test_an_unknown_category_is_rejected(self):
        response = self.create_expense(category="yacht")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("category", response.data)

    # LISTING ------------------------------------------------------------

    def test_the_list_includes_the_summary(self):
        self.create_expense(amount="1000.00", category="food")
        self.create_expense(amount="500.00", category="transport")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]

        self.assertEqual(len(data["expenses"]), 2)
        self.assertEqual(data["summary"]["total_spent"], "1500.00")
        self.assertEqual(data["summary"]["remaining"], "8500.00")
        self.assertFalse(data["summary"]["over_budget"])
        self.assertEqual(data["summary"]["expense_count"], 2)

    def test_the_summary_breaks_spending_down_by_category(self):
        self.create_expense(amount="1000.00", category="food")
        self.create_expense(amount="250.00", category="food")
        self.create_expense(amount="500.00", category="transport")

        response = self.client.get(self.summary_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        by_category = response.data["data"]["by_category"]

        self.assertEqual(by_category[0]["category"], "food")
        self.assertEqual(by_category[0]["total"], "1250.00")
        self.assertEqual(by_category[0]["count"], 2)
        self.assertEqual(by_category[0]["label"], "Food")
        self.assertEqual(by_category[1]["category"], "transport")

    def test_an_empty_trip_reports_zeroes(self):
        response = self.client.get(self.summary_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]

        self.assertEqual(data["total_spent"], "0.00")
        self.assertEqual(data["remaining"], "10000.00")
        self.assertEqual(data["by_category"], [])
        self.assertEqual(data["currency"], "INR")

    def test_going_over_budget_is_reported_and_not_clamped(self):
        self.create_expense(amount="12000.00")

        response = self.client.get(self.summary_url)

        data = response.data["data"]

        self.assertTrue(data["over_budget"])
        self.assertEqual(data["remaining"], "-2000.00")

    def test_the_summary_can_be_filtered_by_category(self):
        self.create_expense(amount="1000.00", category="food")
        self.create_expense(amount="500.00", category="transport")

        response = self.client.get(self.list_url, {"category": "food"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["expenses"]), 1)

        # The summary stays trip-wide on purpose: a filtered list must not
        # look like the trip spent less than it did.
        self.assertEqual(
            response.data["data"]["summary"]["total_spent"],
            "1500.00",
        )

    def test_an_unknown_category_filter_is_rejected(self):
        response = self.client.get(self.list_url, {"category": "yacht"})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # UPDATING AND DELETING ----------------------------------------------

    def test_an_expense_can_be_updated(self):
        expense_id = self.create_expense().data["data"]["id"]

        response = self.client.patch(
            self.detail_url(expense_id),
            {"amount": "900.00", "notes": "Included a tip"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["amount"], "900.00")
        self.assertEqual(
            response.data["data"]["notes"],
            "Included a tip",
        )

        summary = self.client.get(self.summary_url).data["data"]

        self.assertEqual(summary["total_spent"], "900.00")

    def test_an_update_cannot_zero_the_amount(self):
        expense_id = self.create_expense().data["data"]["id"]

        response = self.client.patch(
            self.detail_url(expense_id),
            {"amount": "0.00"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_an_expense_can_be_deleted(self):
        expense_id = self.create_expense().data["data"]["id"]

        response = self.client.delete(self.detail_url(expense_id))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(Expense.objects.exists())

    # OWNERSHIP ----------------------------------------------------------

    def test_another_users_trip_is_a_404(self):
        stranger = create_user("stranger@example.com")
        self.client.force_authenticate(user=stranger)

        for method, url in (
            (self.client.get, self.list_url),
            (self.client.get, self.summary_url),
        ):
            self.assertEqual(
                method(url).status_code,
                status.HTTP_404_NOT_FOUND,
            )

        self.assertEqual(
            self.client.post(
                self.list_url,
                {
                    "title": "Sneaky",
                    "amount": "10.00",
                },
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_another_users_expense_is_a_404(self):
        expense_id = self.create_expense().data["data"]["id"]

        stranger = create_user("stranger@example.com")
        self.client.force_authenticate(user=stranger)

        response = self.client.delete(self.detail_url(expense_id))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(Expense.objects.exists())

    def test_an_expense_id_from_another_trip_is_a_404(self):
        other_trip = create_trip(self.user, title="Udaipur Trip")

        expense = Expense.objects.create(
            trip=other_trip,
            title="Boat ride",
            amount=Decimal("300.00"),
        )

        response = self.client.delete(self.detail_url(expense.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_deleting_a_trip_deletes_its_expenses(self):
        self.create_expense()

        self.trip.delete()

        self.assertFalse(Expense.objects.exists())

    # NOTIFICATIONS ------------------------------------------------------

    def test_crossing_the_budget_creates_a_notification(self):
        self.create_expense(amount="12000.00")

        notification = Notification.objects.get(kind="budget_exceeded")

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.trip, self.trip)
        self.assertFalse(notification.is_read)

    def test_staying_under_budget_creates_no_notification(self):
        self.create_expense(amount="100.00")

        self.assertFalse(
            Notification.objects.filter(
                kind="budget_exceeded"
            ).exists()
        )
