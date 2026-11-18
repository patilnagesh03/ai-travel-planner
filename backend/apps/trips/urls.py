from django.urls import path
from backend.apps.trips.views.trip_view import TripView
from backend.apps.trips.views.trip_detail_view import TripDetailView
from backend.apps.trips.views.trip_preference_view import TripPreferenceView


urlpatterns = [
    path(
        "",
        TripView.as_view(),
        name="trip",
    ),

    path(
        "<uuid:trip_id>/",
        TripDetailView.as_view(),
        name="trip-detail",
    ),

    path(
        "<uuid:trip_id>/preferences/",
        TripPreferenceView.as_view(),
        name="trip-preferences",
    ),
]