from django.contrib import admin

from backend.apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "kind",
        "user",
        "trip",
        "read_at",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "user__email",
        "trip__title",
    )

    list_filter = (
        "kind",
        "read_at",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    ordering = (
        "-created_at",
    )
