"""Health endpoint used by deployment platforms and uptime checks."""

import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_safe


logger = logging.getLogger(__name__)


@require_safe
def health_check(request):
    """Report whether the application can reach its database.

    The endpoint is intentionally unauthenticated: a platform probe cannot
    log in. It exposes only coarse status values, never exception details.
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check failed: the database is unreachable.")

        return JsonResponse(
            {
                "status": "unavailable",
                "database": "down",
            },
            status=503,
        )

    return JsonResponse(
        {
            "status": "ok",
            "database": "up",
        }
    )
