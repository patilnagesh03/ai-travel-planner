from django.urls import path
from backend.apps.trips.views.trip_view import TripView
from backend.apps.trips.views.trip_detail_view import TripDetailView


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
]