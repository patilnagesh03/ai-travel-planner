"""
Resolves a user-supplied destination into a searchable area.

The Overpass API searches by coordinates. Users type names. This service is
the bridge between the two, and it is deliberately explicit about the cases
it cannot handle:

* A destination that matches a curated city resolves to that city's
  bounding box.
* A caller who supplies coordinates gets a box built around those
  coordinates, bypassing the curated list entirely.
* A destination that matches nothing raises `UnsupportedDestinationError`
  with a message that says so, rather than silently returning no results.

We never fall back to a whole-country or whole-region search. Those queries
are exactly the kind of heavy, broad request that shared public
infrastructure should not receive.
"""

import math
import re

from backend.apps.integrations.data import INDIA_CITIES, City
from backend.apps.integrations.exceptions import UnsupportedDestinationError
from backend.apps.integrations.schemas import BoundingBox


# Average length of one degree of latitude, in kilometres.
KM_PER_DEGREE_LATITUDE = 111.32

# Default radius used when a caller searches by coordinates.
DEFAULT_SEARCH_RADIUS_KM = 5.0

# Upper bound on the radius, so a coordinate search cannot turn into a
# region-sized query.
MAX_SEARCH_RADIUS_KM = 25.0

# Tokens that are allowed to follow a city name but do not identify a state.
IGNORED_STATE_TOKENS = frozenset({"india", "in", "republic of india"})

# Two-letter state codes, so "Mumbai MH" resolves as well as
# "Mumbai, Maharashtra".
#
# The values are lower-cased because they are only ever used for
# comparison, and `_normalize_state` always returns a lower-cased string.
STATE_CODES = {
    "an": "andaman and nicobar islands",
    "ap": "andhra pradesh",
    "br": "bihar",
    "cg": "chhattisgarh",
    "ch": "chandigarh",
    "dl": "delhi",
    "ga": "goa",
    "gj": "gujarat",
    "hp": "himachal pradesh",
    "jh": "jharkhand",
    "jk": "jammu and kashmir",
    "ka": "karnataka",
    "kl": "kerala",
    "la": "ladakh",
    "mh": "maharashtra",
    "mp": "madhya pradesh",
    "od": "odisha",
    "pb": "punjab",
    "py": "puducherry",
    "rj": "rajasthan",
    "sk": "sikkim",
    "tn": "tamil nadu",
    "ts": "telangana",
    "uk": "uttarakhand",
    "up": "uttar pradesh",
    "wb": "west bengal",
}


def _normalize(value):
    """Lower-case, collapse whitespace and trim stray punctuation."""

    if not value:
        return ""

    text = str(value).strip().lower()

    text = text.replace("&", " and ")

    text = re.sub(r"\s+", " ", text)

    return text.strip(" .,;")


def _normalize_state(value):
    """Normalize a state name or code to its canonical form."""

    text = _normalize(value)

    if not text:
        return ""

    return STATE_CODES.get(text, text)


def _build_index():
    """Map every accepted spelling of a city to its `City` entry."""

    index = {}

    for city in INDIA_CITIES:
        index[_normalize(city.name)] = city

        index[_normalize("{name}, {state}".format(
            name=city.name,
            state=city.state,
        ))] = city

        for alias in city.aliases:
            index[_normalize(alias)] = city

    return index


CITY_INDEX = _build_index()


class DestinationService:

    @staticmethod
    def resolve(
        destination=None,
        latitude=None,
        longitude=None,
        radius_km=None,
    ):
        """Resolve a destination into a `BoundingBox`.

        Coordinates take precedence over the destination name, so an explicit
        coordinate override always wins.
        """

        if latitude is not None or longitude is not None:
            return DestinationService.bounding_box_from_coordinates(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
            )

        if destination:
            return DestinationService.bounding_box_from_destination(
                destination,
            )

        raise UnsupportedDestinationError(
            "Provide either a destination name or a latitude and "
            "longitude pair."
        )

    @staticmethod
    def resolve_city(destination):
        """Return the `City` for a destination, or raise a clear error.

        Used by every feature that needs a destination's coordinates
        (place search, forecast, map), so they all report an unsupported
        destination the same way.
        """

        city = DestinationService.find_city(destination)

        if city is None:
            raise UnsupportedDestinationError(
                "'{value}' is not a destination we can search. We "
                "currently support {count} curated Indian cities. "
                "Supply a latitude and longitude to search any other "
                "location.".format(
                    value=str(destination).strip(),
                    count=len(INDIA_CITIES),
                )
            )

        return city

    @staticmethod
    def bounding_box_from_destination(destination):
        """Return the bounding box of a curated city."""

        city = DestinationService.resolve_city(destination)

        return BoundingBox(
            south=city.south,
            west=city.west,
            north=city.north,
            east=city.east,
        )

    @staticmethod
    def bounding_box_from_coordinates(
        latitude,
        longitude,
        radius_km=None,
    ):
        """Return a bounding box centred on the given coordinates."""

        if latitude is None or longitude is None:
            raise UnsupportedDestinationError(
                "Both latitude and longitude are required when "
                "searching by coordinates."
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError) as exc:
            raise UnsupportedDestinationError(
                "Latitude and longitude must be numeric."
            ) from exc

        if not -90 <= latitude <= 90:
            raise UnsupportedDestinationError(
                "Latitude must be between -90 and 90."
            )

        if not -180 <= longitude <= 180:
            raise UnsupportedDestinationError(
                "Longitude must be between -180 and 180."
            )

        radius = DestinationService._resolve_radius(radius_km)

        latitude_delta = radius / KM_PER_DEGREE_LATITUDE

        # A degree of longitude covers less ground as you move away from
        # the equator, so the delta has to grow with the latitude.
        cosine = math.cos(math.radians(latitude))

        if abs(cosine) < 1e-9:
            # At the poles, a degree of longitude covers no ground at all.
            longitude_delta = 180.0
        else:
            longitude_delta = radius / (
                KM_PER_DEGREE_LATITUDE * cosine
            )

        south = max(-90.0, latitude - latitude_delta)
        north = min(90.0, latitude + latitude_delta)
        west = max(-180.0, longitude - longitude_delta)
        east = min(180.0, longitude + longitude_delta)

        # Clamping at the poles can collapse one edge of the box.
        if south >= north:
            south = min(-90.0, north - 1e-6)

        if west >= east:
            west = min(-180.0, east - 1e-6)

        return BoundingBox(
            south=south,
            west=west,
            north=north,
            east=east,
        )

    @staticmethod
    def find_city(destination):
        """Return the `City` matching a destination string, or None.

        Accepts "Mumbai", "mumbai", "Bombay", "Mumbai, Maharashtra",
        "Mumbai MH" and similar spellings.
        """

        if not destination:
            return None

        normalized = _normalize(destination)

        if not normalized:
            return None

        # 1. An exact match on the whole string. This runs first so that
        #    multi-word names like "New Delhi" are not split apart.
        city = CITY_INDEX.get(normalized)

        if city is not None:
            return city

        parts = [part.strip() for part in normalized.split(",")]

        city_token = parts[0]

        if not city_token:
            return None

        # 2. "Mumbai Maharashtra" - a space instead of a comma.
        candidate, state_token = DestinationService._split_city_and_state(
            city_token,
        )

        if candidate is None:
            return None

        # 3. An explicit state after a comma wins over the space form.
        if len(parts) > 1 and parts[1]:
            state_token = parts[1]

        if not state_token:
            return candidate

        if state_token in IGNORED_STATE_TOKENS:
            return candidate

        normalized_state = _normalize_state(state_token)

        if normalized_state == _normalize_state(candidate.state):
            return candidate

        # The city is known, but it is not in the state the caller gave.
        raise UnsupportedDestinationError(
            "'{value}' does not match a supported destination. "
            "{city} is in {state}, not {given}.".format(
                value=str(destination).strip(),
                city=candidate.name,
                state=candidate.state,
                given=state_token,
            )
        )

    @staticmethod
    def _split_city_and_state(token):
        """Split "mumbai maharashtra" into a city and a state, if possible."""

        words = token.split()

        if len(words) < 2:
            # A single word can only ever be a city name.
            return CITY_INDEX.get(token), None

        fallback = None

        # Try every split point, longest city name first.
        for index in range(len(words) - 1, 0, -1):
            city_token = " ".join(words[:index])
            state_token = " ".join(words[index:])

            candidate = CITY_INDEX.get(city_token)

            if candidate is None:
                continue

            if _normalize_state(state_token) == _normalize_state(
                candidate.state,
            ):
                return candidate, state_token

            if fallback is None:
                # The city is known, but the state does not match. Keep it
                # so the caller can report the contradiction clearly instead
                # of pretending the destination is unknown.
                fallback = (candidate, state_token)

        if fallback is not None:
            return fallback

        # No city matched with a state, so treat the whole token as a city.
        return CITY_INDEX.get(token), None

    @staticmethod
    def _resolve_radius(radius_km):
        if radius_km is None:
            return DEFAULT_SEARCH_RADIUS_KM

        try:
            radius = float(radius_km)
        except (TypeError, ValueError) as exc:
            raise UnsupportedDestinationError(
                "The search radius must be a number of kilometres."
            ) from exc

        if radius <= 0:
            raise UnsupportedDestinationError(
                "The search radius must be greater than zero."
            )

        if radius > MAX_SEARCH_RADIUS_KM:
            raise UnsupportedDestinationError(
                "The search radius cannot exceed {maximum} km.".format(
                    maximum=MAX_SEARCH_RADIUS_KM,
                )
            )

        return radius

    @staticmethod
    def supported_destinations():
        """Return the curated cities, ready to be listed by the API."""

        return [
            {
                "name": city.name,
                "state": city.state,
                "aliases": list(city.aliases),
                "latitude": city.center[0],
                "longitude": city.center[1],
            }
            for city in INDIA_CITIES
        ]


__all__ = [
    "DestinationService",
    "CITY_INDEX",
    "DEFAULT_SEARCH_RADIUS_KM",
    "MAX_SEARCH_RADIUS_KM",
]
