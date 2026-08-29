from django.contrib import admin
from backend.apps.itinerary.models import Itinerary, ItineraryItem


@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "trip",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "title",
        "trip__title",
        "trip__destination",
        "trip__user__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(ItineraryItem)
class ItineraryItemAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "itinerary",
        "date",
        "start_time",
        "end_time",
        "activity_type",
        "order",
    )

    search_fields = (
        "title",
        "location_name",
        "location_address",
        "itinerary__title",
        "itinerary__trip__title",
    )

    list_filter = (
        "activity_type",
        "date",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "date",
        "order",
        "start_time",
    )