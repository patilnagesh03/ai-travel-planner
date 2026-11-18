from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from backend.apps.expenses.models import Expense
from backend.apps.expenses.services import ExpenseService
from backend.apps.trips.models import Trip


def create_user(email="traveller@example.com"):
    return get_user_model().objects.create_user(
        email=email,
        password="TestPass123!",
        first_name="Test",
        last_name="Traveller",
    )


def create_trip(user, title="Jaipur Trip"):
    return Trip.objects.create(
        user=user,
        title=title,
        destination="Jaipur",
        start_date=timezone.localdate() + timedelta(days=20),
        end_date=timezone.localdate() + timedelta(days=24),
        budget=Decimal("10000.00"),
        currency="INR",
        travelers=2,
    )


class ExpenseServiceTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.trip = create_trip(self.user)
        self.other_trip = create_trip(self.user, title="Udaipur Trip")

    def test_spending_is_totalled_per_trip(self):
        Expense.objects.create(
            trip=self.trip,
            title="Taxi",
            amount=Decimal("500.00"),
        )
        Expense.objects.create(
            trip=self.trip,
            title="Dinner",
            amount=Decimal("1200.50"),
        )
        Expense.objects.create(
            trip=self.other_trip,
            title="Boat",
            amount=Decimal("300.00"),
        )

        totals = ExpenseService.spent_by_trip(self.user)

        self.assertEqual(totals[self.trip.id], Decimal("1700.50"))
        self.assertEqual(totals[self.other_trip.id], Decimal("300.00"))

    def test_another_users_spending_is_not_counted(self):
        stranger = create_user("stranger@example.com")
        stranger_trip = create_trip(stranger)

        Expense.objects.create(
            trip=stranger_trip,
            title="Their taxi",
            amount=Decimal("900.00"),
        )

        totals = ExpenseService.spent_by_trip(self.user)

        self.assertNotIn(stranger_trip.id, totals)

    def test_a_trip_without_expenses_reports_zero(self):
        summary = ExpenseService.build_summary(self.trip)

        self.assertEqual(summary["total_spent"], Decimal("0.00"))
        self.assertEqual(summary["remaining"], Decimal("10000.00"))
        self.assertFalse(summary["over_budget"])
        self.assertEqual(summary["by_category"], [])

    def test_category_totals_are_ordered_by_amount(self):
        for amount, category in (
            ("200.00", "food"),
            ("800.00", "stay"),
            ("300.00", "food"),
        ):
            Expense.objects.create(
                trip=self.trip,
                title=f"{category} expense",
                category=category,
                amount=Decimal(amount),
            )

        summary = ExpenseService.build_summary(self.trip)

        self.assertEqual(
            [row["category"] for row in summary["by_category"]],
            ["stay", "food"],
        )
        self.assertEqual(
            summary["by_category"][1]["total"],
            Decimal("500.00"),
        )
