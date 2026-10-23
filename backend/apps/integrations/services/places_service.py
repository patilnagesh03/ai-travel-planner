"""
Application-level service for discovering places.

This layer sits between the API/business layer and the raw Overpass client.
Its job is to:

1. Translate a search request into a narrow, well-formed Overpass query.
2. Normalize the provider's raw elements into stable `Place` objects.
3. Drop duplicates and enforce the application's result limit.

External place data is **not** persisted. It is read through, normalized and
returned, so there is no provider data sitting in our database and no
open question about ODbL retention obligations.
"""

import hashlib
import logging

from django.core.cache import cache

from backend.apps.integrations.clients import OverpassClient
from backend.apps.integrations.config import (
    MAX_PLACES_PER_SEARCH,
    OVERPASS_QUERY_TIMEOUT,
    PLACES_CACHE_TIMEOUT,
)
from backend.apps.integrations.schemas import (
    CATEGORY_SELECTORS,
    CATEGORY_TAG_RULES,
    BoundingBox,
    Place,
    PlaceCategory,
    PlaceSource,
)


logger = logging.getLogger(__name__)


class PlacesService:

    @staticmethod
    def search_places(
        bbox,
        categories=None,
        limit=None,
        client=None,
    ):
        """Search for places inside ``bbox`` and return normalized places.

        ``bbox`` is a `BoundingBox`. ``categories`` is an optional list of
        `PlaceCategory` values; when omitted every supported category is
        searched. ``limit`` caps the number of places returned and can never
        exceed `MAX_PLACES_PER_SEARCH`.

        Results are cached for `PLACES_CACHE_TIMEOUT` seconds. The cache key
        is derived from the query itself, so two different searches never
        share an entry.
        """

        effective_limit = PlacesService._resolve_limit(limit)

        query = PlacesService.build_query(
            bbox=bbox,
            categories=categories,
            limit=effective_limit,
        )

        cache_key = PlacesService.cache_key(query)

        cached_places = PlacesService.read_cache(cache_key)

        if cached_places is not None:
            logger.info(
                "Serving %s place(s) for the requested area from cache.",
                len(cached_places),
            )

            return cached_places

        overpass_client = client or OverpassClient()

        elements = overpass_client.fetch_elements(query)

        places = PlacesService.normalize_elements(
            elements,
            limit=effective_limit,
        )

        logger.info(
            "Overpass returned %s element(s) for the requested area; "
            "%s place(s) kept after normalization.",
            len(elements),
            len(places),
        )

        PlacesService.write_cache(cache_key, places)

        return places

    @staticmethod
    def cache_key(query):
        """Build a stable cache key for an Overpass query.

        The query already encodes the bounding box, the categories and the
        limit, so hashing it gives a key that changes exactly when the
        request changes.
        """

        digest = hashlib.sha256(
            query.encode("utf-8"),
        ).hexdigest()

        return "places:v1:{digest}".format(digest=digest)

    @staticmethod
    def read_cache(cache_key):
        """Return cached places, or None when there is no usable entry.

        An empty list is a *valid* cached value (the query matched
        nothing), so a cache miss must be detected with ``is None`` and
        never with a truthiness check.
        """

        if PLACES_CACHE_TIMEOUT <= 0:
            return None

        return cache.get(cache_key)

    @staticmethod
    def write_cache(cache_key, places):
        """Store places in the cache, unless caching is disabled."""

        if PLACES_CACHE_TIMEOUT <= 0:
            return

        cache.set(
            cache_key,
            places,
            timeout=PLACES_CACHE_TIMEOUT,
        )

    @staticmethod
    def build_query(bbox, categories=None, limit=None):
        """Build the Overpass QL query for a bounded area and category set.

        The query is deliberately constrained in three ways, because the
        Overpass instances are shared public infrastructure:

        * a bounding box, so we never ask for a whole region;
        * a fixed set of tag selectors, so we never ask for "everything";
        * an output limit, so the provider stops work early.
        """

        if not isinstance(bbox, BoundingBox):
            raise ValueError(
                "bbox must be a BoundingBox instance."
            )

        selected_categories = PlacesService._resolve_categories(
            categories,
        )

        effective_limit = PlacesService._resolve_limit(limit)

        bbox_value = bbox.as_overpass_tuple()

        selectors = "\n".join(
            "  nwr{selector}({bbox});".format(
                selector=CATEGORY_SELECTORS[category],
                bbox=bbox_value,
            )
            for category in selected_categories
        )

        return (
            "[out:json][timeout:{timeout}];\n"
            "(\n"
            "{selectors}\n"
            ");\n"
            "out center {limit};"
        ).format(
            timeout=OVERPASS_QUERY_TIMEOUT,
            selectors=selectors,
            limit=effective_limit,
        )

    @staticmethod
    def normalize_elements(elements, limit=None):
        """Convert raw Overpass elements into normalized `Place` objects.

        Elements that cannot be turned into a usable place (no name, no
        resolvable coordinates) are skipped rather than returned with
        invented values.
        """

        if not isinstance(elements, list):
            raise ValueError(
                "elements must be a list."
            )

        effective_limit = PlacesService._resolve_limit(limit)

        places = []

        seen_source_ids = set()

        for element in elements:
            place = PlacesService._normalize_element(element)

            if place is None:
                continue

            if place.source_id in seen_source_ids:
                # Same OSM object reported twice by the provider.
                continue

            seen_source_ids.add(place.source_id)

            places.append(place)

            if len(places) >= effective_limit:
                break

        return places

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_element(element):
        """Return a `Place` for one Overpass element, or None if unusable."""

        if not isinstance(element, dict):
            return None

        element_type = element.get("type")
        element_id = element.get("id")

        if not element_type or element_id is None:
            return None

        tags = element.get("tags")

        if not isinstance(tags, dict):
            tags = {}

        name = PlacesService._extract_name(tags)

        if not name:
            # A place we cannot name is not usable for trip planning, and we
            # must not invent a name for it.
            return None

        coordinates = PlacesService._extract_coordinates(element)

        if coordinates is None:
            return None

        latitude, longitude = coordinates

        return Place(
            source=PlaceSource.OPENSTREETMAP,
            source_id="{type}/{id}".format(
                type=element_type,
                id=element_id,
            ),
            name=name,
            category=PlacesService._extract_category(tags),
            latitude=latitude,
            longitude=longitude,
            address=PlacesService._extract_address(tags),
            opening_hours=PlacesService._extract_opening_hours(tags),
        )

    @staticmethod
    def _extract_name(tags):
        """Return the best available name, or None when there is none."""

        for key in ("name", "name:en", "alt_name"):
            value = tags.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _extract_coordinates(element):
        """Return ``(latitude, longitude)`` for a node, way or relation.

        Nodes carry their own ``lat``/``lon``. Ways and relations are
        returned by the provider with a computed ``center`` instead, because
        they are made of many nodes.
        """

        latitude = element.get("lat")
        longitude = element.get("lon")

        center = element.get("center")

        if isinstance(center, dict):
            latitude = center.get("lat", latitude)
            longitude = center.get("lon", longitude)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return None

        if not -90 <= latitude <= 90:
            return None

        if not -180 <= longitude <= 180:
            return None

        return latitude, longitude

    @staticmethod
    def _extract_category(tags):
        """Derive the place category from the element's own tags."""

        for tag_key, tag_value, category in CATEGORY_TAG_RULES:
            if tags.get(tag_key) == tag_value:
                return category

        # The query only asks for categories we know about, so this is
        # defensive. We report it as `other` rather than mislabelling it.
        return PlaceCategory.OTHER

    @staticmethod
    def _extract_address(tags):
        """Build an address from the `addr:*` tags, if the source has them."""

        full_address = tags.get("addr:full")

        if isinstance(full_address, str) and full_address.strip():
            return full_address.strip()

        parts = []

        house_number = tags.get("addr:housenumber")
        street = tags.get("addr:street")

        if house_number and street:
            parts.append(
                "{number} {street}".format(
                    number=str(house_number).strip(),
                    street=str(street).strip(),
                )
            )
        elif street:
            parts.append(str(street).strip())
        elif house_number:
            parts.append(str(house_number).strip())

        for key in ("addr:city", "addr:town", "addr:suburb"):
            value = tags.get(key)

            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
                break

        for key in ("addr:state", "addr:country"):
            value = tags.get(key)

            if isinstance(value, str) and value.strip():
                parts.append(value.strip())

        parts = [part for part in parts if part]

        if not parts:
            return None

        return ", ".join(parts)

    @staticmethod
    def _extract_opening_hours(tags):
        """Return the raw `opening_hours` tag, or None when absent.

        The OSM `opening_hours` syntax is far too rich to parse reliably
        here, so the raw value is passed through untouched. Consumers that
        need to reason about opening times must interpret it themselves.
        """

        value = tags.get("opening_hours")

        if isinstance(value, str) and value.strip():
            return value.strip()

        return None

    @staticmethod
    def _resolve_categories(categories):
        """Validate and de-duplicate the requested categories."""

        if not categories:
            return list(CATEGORY_SELECTORS.keys())

        resolved = []

        for category in categories:
            try:
                key = PlacesService._parse_category(category)
            except ValueError as exc:
                raise ValueError(
                    "Unsupported place category: {value}".format(
                        value=category,
                    )
                ) from exc

            if key not in resolved:
                resolved.append(key)

        return resolved

    @staticmethod
    def _parse_category(value):
        """Turn a category name or value into a `PlaceCategory`.

        Both "attraction" and "ATTRACTION" are accepted, because a caller
        may send either the stored value or the enum member name.
        """

        if isinstance(value, PlaceCategory):
            return value

        try:
            return PlaceCategory(value)
        except ValueError:
            pass

        try:
            return PlaceCategory[str(value).strip().upper()]
        except KeyError as exc:
            raise ValueError(
                "Unsupported place category: {value}".format(value=value)
            ) from exc

    @staticmethod
    def _resolve_limit(limit):
        """Clamp the requested limit to the configured application maximum."""

        if limit is None:
            return MAX_PLACES_PER_SEARCH

        limit = int(limit)

        if limit < 1:
            raise ValueError(
                "limit must be a positive integer."
            )

        # The configured maximum is a safety valve for shared public
        # infrastructure, so a caller can ask for fewer places but never
        # for more.
        return min(limit, MAX_PLACES_PER_SEARCH)


__all__ = ["PlacesService"]
