from django.urls import path

from backend.apps.expenses.views import (
    TripExpenseDetailView,
    TripExpenseListCreateView,
    TripExpenseSummaryView,
)


urlpatterns = [
    path(
        "trips/<uuid:trip_id>/expenses/",
        TripExpenseListCreateView.as_view(),
        name="trip-expense-list-create",
    ),

    path(
        "trips/<uuid:trip_id>/expenses/summary/",
        TripExpenseSummaryView.as_view(),
        name="trip-expense-summary",
    ),

    path(
        "trips/<uuid:trip_id>/expenses/<uuid:expense_id>/",
        TripExpenseDetailView.as_view(),
        name="trip-expense-detail",
    ),
]
