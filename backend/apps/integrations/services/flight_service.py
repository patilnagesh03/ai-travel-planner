"""
Deterministic flight search links for a trip.

This service does **not** call a flight provider. Live fares require a paid
API (and an account), so instead of guessing at prices we build links to the
search pages of well-known providers. The links are derived only from the
trip's own fields, which makes them reproducible and testable: the same trip
always produces exactly the same URL.

The user chooses the provider from the result, and any price or availability
they see there belongs to that provider, not to us.
"""

import re
from urllib.parse import quote_plus

from backend.apps.integrations.exceptions import MissingTripOriginError


# Both providers accept a plain city name, so no IATA code lookup is needed.
GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights"

KAYAK_FLIGHTS_URL = "https://www.kayak.co.in/flights"

# Shown next to the links so the source of any price is unambiguous.
FLIGHT_LINK_DISCLAIMER = (
    "This app does not fetch or store live fares. Prices and availability "
    "are shown by the provider you open, not by AI Travel Planner."
)


def _slugify(value):
    """Turn a free-text place name into a URL path segment.

    "New Delhi" becomes "New-Delhi". Characters that are not letters or
    digits are collapsed into a single hyphen. If nothing usable is left
    (for example a name written entirely in a non-Latin script) the original
    text is percent-encoded instead, so the link still points at the place
    the traveller typed.
    """

    text = str(value).strip()

    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")

    if slug:
        return slug

    return quote_plus(text)


class FlightService:

    @staticmethod
    def build_links(trip):
        """Return deterministic search links for ``trip``.

        Raises `MissingTripOriginError` when the trip has no departure city,
        because a route cannot be built without one. The view maps that to a
        400 with a message explaining how to fix it.
        """

        origin = str(getattr(trip, "origin", "") or "").strip()
        destination = str(trip.destination or "").strip()

        if not origin:
            raise MissingTripOriginError(
                "This trip has no departure city. Add an origin to the trip "
                "to see flight links."
            )

        start_date = trip.start_date.isoformat()
        end_date = trip.end_date.isoformat()

        query = (
            "Flights from {origin} to {destination} "
            "on {start} through {end}"
        ).format(
            origin=origin,
            destination=destination,
            start=start_date,
            end=end_date,
        )

        travelers = int(trip.travelers or 1)

        if travelers > 1:
            query += " for {count} adults".format(count=travelers)

        google_url = "{base}?q={query}".format(
            base=GOOGLE_FLIGHTS_URL,
            query=quote_plus(query),
        )

        kayak_url = "{base}/{origin}-{destination}/{start}/{end}".format(
            base=KAYAK_FLIGHTS_URL,
            origin=_slugify(origin),
            destination=_slugify(destination),
            start=start_date,
            end=end_date,
        )

        return {
            "origin": origin,
            "destination": destination,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
            "travelers": travelers,
            "disclaimer": FLIGHT_LINK_DISCLAIMER,
            "links": [
                {
                    "provider": "google_flights",
                    "label": "Google Flights",
                    "url": google_url,
                },
                {
                    "provider": "kayak",
                    "label": "Kayak",
                    "url": kayak_url,
                },
            ],
        }


__all__ = [
    "FLIGHT_LINK_DISCLAIMER",
    "GOOGLE_FLIGHTS_URL",
    "KAYAK_FLIGHTS_URL",
    "FlightService",
]
