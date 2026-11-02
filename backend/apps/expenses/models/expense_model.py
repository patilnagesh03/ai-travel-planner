import uuid

from django.db import models
from django.utils import timezone

from backend.apps.expenses.enums import ExpenseCategory


class Expense(models.Model):
    """One thing a traveller paid for, recorded against a trip.

    Every expense is stored in the trip's own currency. The trip is the single
    source of truth for the currency and the budget, so a summary never has to
    mix rates and an expense cannot drift away from the trip it belongs to.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.CASCADE,
        related_name="expenses",
    )

    title = models.CharField(
        max_length=200,
    )

    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    spent_on = models.DateField(
        default=timezone.localdate,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "expenses"
        ordering = ["-spent_on", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="expense_amount_greater_than_zero",
            ),
        ]
        indexes = [
            models.Index(
                fields=["trip", "category"],
                name="expense_trip_category_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.amount}"
