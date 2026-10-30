from django.urls import path

from backend.apps.integrations.views import (
    CurrencyRatesView,
    DestinationResolveView,
    PlaceSearchView,
    SupportedDestinationsView,
    TripPlaceSearchView,
    TripWeatherView,
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
        "places/resolve/",
        DestinationResolveView.as_view(),
        name="place-resolve",
    ),

    path(
        "trips/<uuid:trip_id>/places/",
        TripPlaceSearchView.as_view(),
        name="trip-places",
    ),

    path(
        "trips/<uuid:trip_id>/weather/",
        TripWeatherView.as_view(),
        name="trip-weather",
    ),

    path(
        "currency/rates/",
        CurrencyRatesView.as_view(),
        name="currency-rates",
    ),
]
