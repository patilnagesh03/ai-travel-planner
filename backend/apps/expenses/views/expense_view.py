import logging

from django.http import Http404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.expenses.serializers import (
    ExpenseSerializer,
    ExpenseSummarySerializer,
)
from backend.apps.expenses.services import ExpenseService
from backend.apps.expenses.services.expense_service import CATEGORY_LABELS
from backend.apps.notifications.services import NotificationService


logger = logging.getLogger(__name__)


class TripExpenseListCreateView(APIView):
    """List or record expenses for one trip.

    The list response carries the summary as well, so the UI never has to
    stitch a list and a total together from two requests that could disagree
    if one of them is stale.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        category = request.query_params.get("category") or None

        if category and category not in CATEGORY_LABELS:
            raise ValidationError(
                {
                    "category": (
                        "Unknown expense category. Use one of: "
                        f"{', '.join(CATEGORY_LABELS)}."
                    )
                }
            )

        try:
            trip = ExpenseService.get_user_trip(
                user=request.user,
                trip_id=trip_id,
            )

            expenses = ExpenseService.list_for_trip(
                trip=trip,
                category=category,
            )

            summary = ExpenseService.build_summary(trip)

            return Response(
                {
                    "success": True,
                    "message": "Expenses retrieved successfully.",
                    "data": {
                        "expenses": ExpenseSerializer(
                            expenses,
                            many=True,
                        ).data,
                        "summary": ExpenseSummarySerializer(
                            summary
                        ).data,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Http404:
            # A missing or foreign trip. DRF turns this into a 404 rather
            # than letting it become a generic 500.
            raise

        except Exception:
            logger.exception(
                "Unexpected error while retrieving trip expenses."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving expenses."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, trip_id):
        serializer = ExpenseSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        try:
            expense = ExpenseService.create_expense(
                user=request.user,
                trip_id=trip_id,
                validated_data=serializer.validated_data,
            )

            # Recording an expense can push the trip over budget. Syncing
            # here means the bell updates without waiting for the next visit
            # to the notifications endpoint.
            NotificationService.sync_for_user(request.user)

            return Response(
                {
                    "success": True,
                    "message": "Expense added successfully.",
                    "data": ExpenseSerializer(expense).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Http404:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while creating trip expense."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while adding the expense."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TripExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, trip_id, expense_id):
        try:
            expense = ExpenseService.get_expense(
                user=request.user,
                trip_id=trip_id,
                expense_id=expense_id,
            )

            serializer = ExpenseSerializer(
                expense,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(raise_exception=True)

            updated_expense = ExpenseService.update_expense(
                user=request.user,
                trip_id=trip_id,
                expense_id=expense_id,
                validated_data=serializer.validated_data,
            )

            NotificationService.sync_for_user(request.user)

            return Response(
                {
                    "success": True,
                    "message": "Expense updated successfully.",
                    "data": ExpenseSerializer(updated_expense).data,
                },
                status=status.HTTP_200_OK,
            )

        except Http404:
            raise

        except ValidationError:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while updating trip expense."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while updating the expense."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, trip_id, expense_id):
        try:
            ExpenseService.delete_expense(
                user=request.user,
                trip_id=trip_id,
                expense_id=expense_id,
            )

            # Removing an expense can bring a trip back under budget.
            NotificationService.sync_for_user(request.user)

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        except Http404:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while deleting trip expense."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while deleting the expense."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TripExpenseSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        try:
            summary = ExpenseService.get_summary(
                user=request.user,
                trip_id=trip_id,
            )

            return Response(
                {
                    "success": True,
                    "message": "Expense summary retrieved successfully.",
                    "data": ExpenseSummarySerializer(summary).data,
                },
                status=status.HTTP_200_OK,
            )

        except Http404:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while retrieving expense summary."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving the summary."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
