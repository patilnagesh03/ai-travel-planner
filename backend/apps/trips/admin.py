from django.contrib import admin

from backend.apps.trips.models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "destination",
        "user",
        "start_date",
        "end_date",
        "budget",
        "currency",
        "travelers",
        "created_at",
    )

    search_fields = (
        "title",
        "destination",
        "user__email",
    )

    list_filter = (
        "currency",
        "start_date",
        "end_date",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )