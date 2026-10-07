from django.urls import path

from backend.apps.itinerary.views import (
    ItineraryItemDetailView,
    ItineraryItemListCreateView,
    ItineraryView,
)

urlpatterns = [
    path(
        "trips/<uuid:trip_id>/itinerary/",
        ItineraryView.as_view(),
        name="itinerary",
    ),

    path(
        "itineraries/<uuid:itinerary_id>/items/",
        ItineraryItemListCreateView.as_view(),
        name="itinerary-item-list-create",
    ),

    path(
        "itineraries/<uuid:itinerary_id>/items/<uuid:item_id>/",
        ItineraryItemDetailView.as_view(),
        name="itinerary-item-detail",
    ),
]