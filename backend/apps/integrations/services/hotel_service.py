"""
Accommodation discovery for a trip.

Hotels come from the same OpenStreetMap/Overpass pipeline as every other
place, so there is no additional provider, no API key and no persisted
provider data. The only extra work here is:

1. Restricting the search to accommodation categories.
2. Ordering the results by their distance from the trip's destination centre,
   which is what a traveller actually wants to see first.
3. Building a deterministic Booking.com search link for live prices. Like the
   flight links, it is a search link, not a price feed.
"""

import math
from dataclasses import dataclass
from urllib.parse import urlencode

from backend.apps.integrations.config import MAX_PLACES_PER_SEARCH
from backend.apps.integrations.schemas import (
    HOTEL_CATEGORIES,
    BoundingBox,
    Place,
)
from backend.apps.integrations.services.destination_service import (
    DestinationService,
)
from backend.apps.integrations.services.places_service import PlacesService


# Mean Earth radius in kilometres, used by the haversine formula.
EARTH_RADIUS_KM = 6371.0088

BOOKING_SEARCH_URL = "https://www.booking.com/searchresults.html"

HOTEL_ATTRIBUTION = "Accommodation data © OpenStreetMap contributors."


@dataclass(frozen=True)
class Hotel(Place):
    """A `Place` that is somewhere to stay, plus its distance from centre."""

    distance_km: float = 0.0


class HotelService:

    @staticmethod
    def search_hotels(trip, limit=None, client=None):
        """Return accommodation around the trip's destination.

        ``limit`` caps how many hotels are returned. The provider is asked
        for the configured maximum so that distance ordering happens over a
        full candidate set, and only then is the caller's limit applied.
        """

        effective_limit = HotelService._resolve_limit(limit)

        city = DestinationService.resolve_city(trip.destination)

        bbox = BoundingBox(
            south=city.south,
            west=city.west,
            north=city.north,
            east=city.east,
        )

        places = PlacesService.search_places(
            bbox=bbox,
            categories=list(HOTEL_CATEGORIES),
            limit=MAX_PLACES_PER_SEARCH,
            client=client,
        )

        centre_latitude, centre_longitude = city.center

        hotels = [
            Hotel(
                source=place.source,
                source_id=place.source_id,
                name=place.name,
                category=place.category,
                latitude=place.latitude,
                longitude=place.longitude,
                address=place.address,
                opening_hours=place.opening_hours,
                distance_km=round(
                    HotelService.distance_km(
                        centre_latitude,
                        centre_longitude,
                        place.latitude,
                        place.longitude,
                    ),
                    2,
                ),
            )
            for place in places
        ]

        hotels.sort(key=lambda hotel: (hotel.distance_km, hotel.name.lower()))

        return {
            "destination": {
                "name": city.name,
                "state": city.state,
                "latitude": centre_latitude,
                "longitude": centre_longitude,
            },
            "hotels": hotels[:effective_limit],
            "booking_url": HotelService.build_booking_url(
                destination=city.name,
                start_date=trip.start_date,
                end_date=trip.end_date,
                travelers=trip.travelers,
            ),
            "attribution": HOTEL_ATTRIBUTION,
        }

    @staticmethod
    def build_booking_url(destination, start_date, end_date, travelers):
        """Build a Booking.com search URL for the trip's dates and party."""

        query = urlencode(
            {
                "ss": destination,
                "checkin": start_date.isoformat(),
                "checkout": end_date.isoformat(),
                "group_adults": int(travelers or 1),
                "no_rooms": 1,
            }
        )

        return "{base}?{query}".format(
            base=BOOKING_SEARCH_URL,
            query=query,
        )

    @staticmethod
    def distance_km(latitude_a, longitude_a, latitude_b, longitude_b):
        """Great-circle distance between two points, in kilometres."""

        latitude_a = math.radians(float(latitude_a))
        longitude_a = math.radians(float(longitude_a))
        latitude_b = math.radians(float(latitude_b))
        longitude_b = math.radians(float(longitude_b))

        delta_latitude = latitude_b - latitude_a
        delta_longitude = longitude_b - longitude_a

        haversine = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(latitude_a)
            * math.cos(latitude_b)
            * math.sin(delta_longitude / 2) ** 2
        )

        # Clamp rounding noise so a value just above 1 cannot make asin fail.
        haversine = min(1.0, max(0.0, haversine))

        return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))

    @staticmethod
    def _resolve_limit(limit):
        if limit is None:
            return MAX_PLACES_PER_SEARCH

        limit = int(limit)

        if limit < 1:
            raise ValueError("limit must be a positive integer.")

        return min(limit, MAX_PLACES_PER_SEARCH)


__all__ = [
    "BOOKING_SEARCH_URL",
    "EARTH_RADIUS_KM",
    "HOTEL_ATTRIBUTION",
    "Hotel",
    "HotelService",
]
