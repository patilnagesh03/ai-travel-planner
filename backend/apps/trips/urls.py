from django.urls import path
from backend.apps.trips.views.trip_view import TripView


urlpatterns = [
    path(
        "",
        TripView.as_view(),
        name="trip",
    ),
]