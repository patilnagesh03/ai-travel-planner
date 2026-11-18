"""
HTTP client for the OpenStreetMap Nominatim search API.

Nominatim is the official search and geocoding engine for OpenStreetMap.
It is fast, stable, globally available, 100% free, and requires no API key.

This client queries Nominatim within a bounded viewbox and converts the
returned points of interest into raw OSM element dicts, matching the shape
expected by ``PlacesService.normalize_elements``.
"""

import logging
import socket
from contextlib import contextmanager

import requests
from urllib3.util import connection as urllib3_connection

from backend.apps.integrations.config import (
    INTEGRATIONS_USER_AGENT,
    OVERPASS_IPV4_ONLY,
)
from backend.apps.integrations.exceptions import (
    IntegrationError,
    IntegrationRateLimitError,
    IntegrationRequestError,
    IntegrationResponseError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)
from backend.apps.integrations.schemas import HOTEL_CATEGORIES, PlaceCategory


logger = logging.getLogger(__name__)

DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_TIMEOUT = 10


@contextmanager
def ipv4_only(enabled):
    if not enabled:
        yield
        return

    original = urllib3_connection.allowed_gai_family
    urllib3_connection.allowed_gai_family = lambda: socket.AF_INET

    try:
        yield
    finally:
        urllib3_connection.allowed_gai_family = original


class NominatimClient:
    """Thin, synchronous HTTP client for the OSM Nominatim search API."""

    def __init__(
        self,
        api_url=None,
        timeout=None,
        user_agent=None,
        ipv4_only_enabled=None,
    ):
        self.api_url = api_url or DEFAULT_NOMINATIM_URL
        self.timeout = DEFAULT_TIMEOUT if timeout is None else timeout
        self.user_agent = user_agent or INTEGRATIONS_USER_AGENT
        self.ipv4_only = (
            OVERPASS_IPV4_ONLY if ipv4_only_enabled is None else ipv4_only_enabled
        )

    def fetch_elements_for_bbox(self, bbox, categories=None, limit=20):
        """Search Nominatim within ``bbox`` and return raw OSM elements."""
        viewbox = f"{bbox.west},{bbox.north},{bbox.east},{bbox.south}"

        # Determine search keywords based on requested categories
        query_terms = self._determine_query_terms(categories)

        elements = []
        seen_ids = set()

        for term in query_terms:
            if len(elements) >= limit:
                break

            params = {
                "q": term,
                "viewbox": viewbox,
                "bounded": 1,
                "format": "jsonv2",
                "limit": min(limit, 20),
            }

            try:
                items = self._get(params)
            except Exception as exc:
                logger.warning(
                    "Nominatim query failed for term %r: %s",
                    term,
                    exc,
                )
                continue

            for item in items:
                element = self._convert_to_element(item)
                if element is None:
                    continue

                source_key = (element["type"], element["id"])
                if source_key in seen_ids:
                    continue

                seen_ids.add(source_key)
                elements.append(element)

                if len(elements) >= limit:
                    break

        return elements

    def fetch_elements(self, query=None, bbox=None, categories=None, limit=20):
        """Generic adapter method matching the interface used by PlacesService."""
        if bbox is not None:
            return self.fetch_elements_for_bbox(
                bbox=bbox,
                categories=categories,
                limit=limit,
            )

        # Fallback if only query is passed
        return []

    def _determine_query_terms(self, categories):
        """Map PlaceCategory values to optimal Nominatim search queries."""
        if not categories:
            return ["attractions", "museum", "monument", "park"]

        cat_set = set(categories)

        # Check for hotel-specific searches
        if cat_set.issubset(set(HOTEL_CATEGORIES)):
            return ["hotel", "guest house", "hostel"]

        terms = []
        if PlaceCategory.ATTRACTION in cat_set:
            terms.append("attractions")
        if PlaceCategory.MUSEUM in cat_set:
            terms.append("museum")
        if PlaceCategory.PARK in cat_set:
            terms.append("park")
        if PlaceCategory.MONUMENT in cat_set:
            terms.append("monument")
        if PlaceCategory.RELIGIOUS_SITE in cat_set:
            terms.append("temple")
        if PlaceCategory.RESTAURANT in cat_set:
            terms.append("restaurant")
        if PlaceCategory.CAFE in cat_set:
            terms.append("cafe")
        if PlaceCategory.VIEWPOINT in cat_set:
            terms.append("viewpoint")

        return terms or ["attractions", "museum", "park"]

    def _convert_to_element(self, item):
        """Convert a single Nominatim JSON item to an OSM element dict."""
        if not isinstance(item, dict):
            return None

        osm_type = item.get("osm_type")
        osm_id = item.get("osm_id") or item.get("place_id")

        if not osm_type or osm_id is None:
            return None

        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            return None

        name = item.get("name")
        display_name = item.get("display_name", "")
        if not name and display_name:
            name = display_name.split(",")[0].strip()

        if not name:
            return None

        category = item.get("category", "tourism")
        category_type = item.get("type", "attraction")

        tags = {
            "name": name,
            category: category_type,
            "addr:full": display_name,
        }

        return {
            "type": osm_type,
            "id": osm_id,
            "lat": lat,
            "lon": lon,
            "tags": tags,
        }

    def _get(self, params):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        try:
            with ipv4_only(self.ipv4_only):
                response = requests.get(
                    self.api_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
        except requests.exceptions.Timeout as exc:
            raise IntegrationTimeoutError(
                "Nominatim places provider did not respond in time."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise IntegrationUnavailableError(
                "Could not connect to Nominatim places provider."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise IntegrationError(
                "Unexpected failure calling Nominatim places provider."
            ) from exc

        if response.status_code == 429:
            raise IntegrationRateLimitError(
                "Nominatim places provider is rate limiting requests."
            )
        if response.status_code >= 500:
            raise IntegrationUnavailableError(
                "Nominatim places provider is temporarily unavailable."
            )
        if not response.ok:
            raise IntegrationRequestError(
                f"Nominatim places provider returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise IntegrationResponseError(
                "Nominatim returned invalid JSON."
            ) from exc

        if not isinstance(data, list):
            return []

        return data


__all__ = ["NominatimClient"]
