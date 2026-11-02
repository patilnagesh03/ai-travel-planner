from decimal import Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from backend.apps.expenses.enums import ExpenseCategory
from backend.apps.expenses.models import Expense
from backend.apps.trips.services.trip_service import TripService


# Sums can exceed a single expense, so the aggregate uses a wider field.
MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)

ZERO = Decimal("0.00")

CATEGORY_LABELS = dict(ExpenseCategory.choices)


class ExpenseService:

    @staticmethod
    def get_user_trip(user, trip_id):
        return TripService.get_user_trip(
            user=user,
            trip_id=trip_id,
        )

    @staticmethod
    def list_for_trip(trip, category=None):
        expenses = Expense.objects.filter(trip=trip)

        if category:
            expenses = expenses.filter(category=category)

        return expenses.order_by("-spent_on", "-created_at")

    @staticmethod
    def get_expense(user, trip_id, expense_id):
        trip = TripService.get_user_trip(
            user=user,
            trip_id=trip_id,
        )

        return get_object_or_404(
            Expense,
            id=expense_id,
            trip=trip,
        )

    @staticmethod
    @transaction.atomic
    def create_expense(user, trip_id, validated_data):
        trip = TripService.get_user_trip(
            user=user,
            trip_id=trip_id,
        )

        return Expense.objects.create(
            trip=trip,
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def update_expense(user, trip_id, expense_id, validated_data):
        expense = ExpenseService.get_expense(
            user=user,
            trip_id=trip_id,
            expense_id=expense_id,
        )

        for field, value in validated_data.items():
            setattr(expense, field, value)

        expense.save()

        return expense

    @staticmethod
    @transaction.atomic
    def delete_expense(user, trip_id, expense_id):
        expense = ExpenseService.get_expense(
            user=user,
            trip_id=trip_id,
            expense_id=expense_id,
        )

        expense.delete()

    @staticmethod
    def spent_by_trip(user):
        """Total spend per trip in one query, for the notification rules.

        Returning a mapping keeps the budget check for every trip to a single
        aggregate instead of one query per trip.
        """

        rows = (
            Expense.objects
            .filter(trip__user=user)
            .values("trip_id")
            .annotate(
                total=Coalesce(
                    Sum("amount"),
                    ZERO,
                    output_field=MONEY_FIELD,
                )
            )
        )

        return {
            row["trip_id"]: row["total"]
            for row in rows
        }

    @staticmethod
    def get_summary(user, trip_id):
        trip = TripService.get_user_trip(
            user=user,
            trip_id=trip_id,
        )

        return ExpenseService.build_summary(trip)

    @staticmethod
    def build_summary(trip):
        totals = Expense.objects.filter(trip=trip).aggregate(
            total=Coalesce(
                Sum("amount"),
                ZERO,
                output_field=MONEY_FIELD,
            ),
            count=Count("id"),
        )

        total_spent = totals["total"] or ZERO

        by_category = (
            Expense.objects
            .filter(trip=trip)
            .values("category")
            .annotate(
                total=Coalesce(
                    Sum("amount"),
                    ZERO,
                    output_field=MONEY_FIELD,
                ),
                count=Count("id"),
            )
            .order_by("-total", "category")
        )

        return {
            "currency": trip.currency,
            "budget": trip.budget,
            "total_spent": total_spent,
            "remaining": trip.budget - total_spent,
            "over_budget": total_spent > trip.budget,
            "expense_count": totals["count"] or 0,
            "by_category": [
                {
                    "category": row["category"],
                    "label": CATEGORY_LABELS.get(
                        row["category"],
                        row["category"].replace("_", " ").title(),
                    ),
                    "total": row["total"],
                    "count": row["count"],
                }
                for row in by_category
            ],
        }
