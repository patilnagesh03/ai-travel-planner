from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone

from backend.apps.expenses.services import ExpenseService
from backend.apps.notifications.enums import NotificationKind
from backend.apps.notifications.models import Notification
from backend.apps.trips.models import Trip


ZERO = Decimal("0.00")

# How far ahead a trip must be to earn a "starting soon" notice.
TRIP_REMINDER_DAYS = 7

# Past trips older than this no longer earn a "record your expenses" notice;
# otherwise every historical trip would notify as soon as this feature ships.
TRIP_ENDED_WINDOW_DAYS = 30

# One page is enough for the bell dropdown. The oldest notifications fall off
# rather than growing the payload without bound.
LIST_LIMIT = 50


def _money(amount):
    return f"{amount:,.2f}"


class NotificationService:

    @staticmethod
    def sync_for_user(user, today=None):
        """Create any notification the user's current data implies.

        This is idempotent: the dedupe key includes the state being reported,
        so repeated calls insert nothing. It is also the only place messages
        are produced, which keeps "why did I get this?" answerable from the
        trip and its expenses alone.
        """

        today = today or timezone.localdate()

        spent = ExpenseService.spent_by_trip(user)

        # One query for every key already present beats a SELECT (and possible
        # INSERT) per trip and rule. The unread badge polls every minute, so
        # this keeps that request cheap for users with many trips.
        existing_keys = set(
            Notification.objects
            .filter(user=user)
            .values_list("dedupe_key", flat=True)
        )

        created = []

        for trip in Trip.objects.filter(user=user):
            created.extend(
                NotificationService._sync_budget(
                    trip,
                    spent.get(trip.id, ZERO),
                    existing_keys,
                )
            )
            created.extend(
                NotificationService._sync_reminders(
                    trip,
                    today,
                    existing_keys,
                )
            )

        return created

    @staticmethod
    def _sync_budget(trip, total_spent, existing_keys):
        if total_spent <= trip.budget:
            return []

        key = f"budget-exceeded:{trip.id}:{trip.budget}"

        return NotificationService._ensure(
            trip=trip,
            kind=NotificationKind.BUDGET_EXCEEDED,
            dedupe_key=key,
            title="Budget exceeded",
            message=(
                f"Spending on {trip.title} has reached "
                f"{trip.currency} {_money(total_spent)}, above the "
                f"{trip.currency} {_money(trip.budget)} budget."
            ),
            existing_keys=existing_keys,
        )

    @staticmethod
    def _sync_reminders(trip, today, existing_keys):
        created = []

        days_until_start = (trip.start_date - today).days

        if 0 <= days_until_start <= TRIP_REMINDER_DAYS:
            if days_until_start == 0:
                timing = "today"
            elif days_until_start == 1:
                timing = "tomorrow"
            else:
                timing = (
                    f"in {days_until_start} days, on "
                    f"{trip.start_date:%d %b %Y}"
                )

            created.extend(
                NotificationService._ensure(
                    trip=trip,
                    kind=NotificationKind.TRIP_SOON,
                    dedupe_key=(
                        f"trip-soon:{trip.id}:"
                        f"{trip.start_date.isoformat()}"
                    ),
                    title="Trip starting soon",
                    message=(
                        f"Your trip to {trip.destination} starts {timing}. "
                        "Check the forecast and your itinerary."
                    ),
                    existing_keys=existing_keys,
                )
            )

        days_since_end = (today - trip.end_date).days

        if 0 < days_since_end <= TRIP_ENDED_WINDOW_DAYS:
            created.extend(
                NotificationService._ensure(
                    trip=trip,
                    kind=NotificationKind.TRIP_ENDED,
                    dedupe_key=(
                        f"trip-ended:{trip.id}:"
                        f"{trip.end_date.isoformat()}"
                    ),
                    title="Trip ended",
                    message=(
                        f"Your trip to {trip.destination} ended on "
                        f"{trip.end_date:%d %b %Y}. Add any remaining "
                        "expenses so your totals stay accurate."
                    ),
                    existing_keys=existing_keys,
                )
            )

        return created

    @staticmethod
    def _ensure(trip, kind, dedupe_key, title, message, existing_keys):
        if dedupe_key in existing_keys:
            return []

        notification, created = Notification.objects.get_or_create(
            user=trip.user,
            dedupe_key=dedupe_key,
            defaults={
                "trip": trip,
                "kind": kind,
                "title": title,
                "message": message,
            },
        )

        existing_keys.add(dedupe_key)

        return [notification] if created else []

    @staticmethod
    def list_for_user(user, unread_only=False):
        notifications = (
            Notification.objects
            .filter(user=user)
            .select_related("trip")
        )

        if unread_only:
            notifications = notifications.filter(read_at__isnull=True)

        return notifications.order_by("-created_at")[:LIST_LIMIT]

    @staticmethod
    def unread_count(user):
        return Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).count()

    @staticmethod
    def mark_read(user, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=user,
        )

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])

        return notification

    @staticmethod
    def mark_all_read(user):
        return Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())

    @staticmethod
    def delete(user, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=user,
        )

        notification.delete()
