from django.urls import path

from backend.apps.integrations.views import (
    PlaceSearchView,
    SupportedDestinationsView,
    TripPlaceSearchView,
)


urlpatterns = [
    path(
        "places/search/",
        PlaceSearchView.as_view(),
        name="place-search",
    ),

    path(
        "places/destinations/",
        SupportedDestinationsView.as_view(),
        name="place-destinations",
    ),

    path(
        "trips/<uuid:trip_id>/places/",
        TripPlaceSearchView.as_view(),
        name="trip-places",
    ),
]
