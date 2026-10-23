from django.urls import path

from backend.apps.ai.views import (
    AIStatusView,
    ItineraryGenerationView,
)


urlpatterns = [
    path(
        "trips/<uuid:trip_id>/itinerary/generate/",
        ItineraryGenerationView.as_view(),
        name="itinerary-generate",
    ),

    path(
        "ai/status/",
        AIStatusView.as_view(),
        name="ai-status",
    ),
]
