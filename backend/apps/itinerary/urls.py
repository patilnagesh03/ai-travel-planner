from django.urls import path
from backend.apps.itinerary.views import ItineraryView


urlpatterns = [
    path(
        "trips/<uuid:trip_id>/itinerary/",
        ItineraryView.as_view(),
        name="itinerary",
    ),
]