from django.contrib import admin

from backend.apps.expenses.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "trip",
        "category",
        "amount",
        "spent_on",
    )

    search_fields = (
        "title",
        "notes",
        "trip__title",
        "trip__destination",
        "trip__user__email",
    )

    list_filter = (
        "category",
        "spent_on",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-spent_on",
        "-created_at",
    )
