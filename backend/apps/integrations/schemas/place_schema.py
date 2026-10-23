"""
Normalized, provider-agnostic representations of place data.

The Overpass API returns raw OSM elements. Those elements are an implementation
detail of the provider: they use different shapes for nodes, ways and
relations, they carry a lot of tags we do not care about, and they will change
if the provider changes.

Everything above this layer therefore works with the dataclasses defined here.
They are the stable internal contract of the integration.
"""

from dataclasses import dataclass
from typing import Optional

from django.db import models


class PlaceSource:
    """Identifiers for the upstream data source of a place."""

    OPENSTREETMAP = "openstreetmap"


class PlaceCategory(models.TextChoices):
    """The deliberately constrained set of place types we search for.

    Keeping this list small is deliberate. Every category adds another clause
    to the Overpass query, and the Overpass public instances are shared,
    finite infrastructure. We only ask for things that are genuinely useful
    when planning a trip.
    """

    ATTRACTION = "attraction", "Attraction"
    MUSEUM = "museum", "Museum"
    VIEWPOINT = "viewpoint", "Viewpoint"
    MONUMENT = "monument", "Monument"
    RELIGIOUS_SITE = "religious_site", "Religious Site"
    PARK = "park", "Park"
    RESTAURANT = "restaurant", "Restaurant"
    CAFE = "cafe", "Cafe"

    # Defensive fallback only. `OTHER` is never queried for, it only exists
    # so that an element we cannot categorise is reported honestly instead
    # of being mislabelled as something it is not.
    OTHER = "other", "Other"


# OSM tag selectors used to BUILD the Overpass query.
#
# One clause per category keeps the query narrow, which is what limits the
# amount of work the provider has to do.
CATEGORY_SELECTORS = {
    PlaceCategory.ATTRACTION: '["tourism"="attraction"]',
    PlaceCategory.MUSEUM: '["tourism"="museum"]',
    PlaceCategory.VIEWPOINT: '["tourism"="viewpoint"]',
    PlaceCategory.MONUMENT: '["historic"="monument"]',
    PlaceCategory.RELIGIOUS_SITE: '["amenity"="place_of_worship"]',
    PlaceCategory.PARK: '["leisure"="park"]',
    PlaceCategory.RESTAURANT: '["amenity"="restaurant"]',
    PlaceCategory.CAFE: '["amenity"="cafe"]',
}


# Rules used to work out the category of a RETURNED element.
#
# The provider does not tell us which clause matched, so we derive it from
# the element's own tags. Order matters: the first matching rule wins.
CATEGORY_TAG_RULES = (
    ("tourism", "attraction", PlaceCategory.ATTRACTION),
    ("tourism", "museum", PlaceCategory.MUSEUM),
    ("tourism", "viewpoint", PlaceCategory.VIEWPOINT),
    ("tourism", "gallery", PlaceCategory.ATTRACTION),
    ("historic", "monument", PlaceCategory.MONUMENT),
    ("historic", "memorial", PlaceCategory.MONUMENT),
    ("amenity", "place_of_worship", PlaceCategory.RELIGIOUS_SITE),
    ("leisure", "park", PlaceCategory.PARK),
    ("amenity", "restaurant", PlaceCategory.RESTAURANT),
    ("amenity", "cafe", PlaceCategory.CAFE),
)


@dataclass(frozen=True)
class BoundingBox:
    """A geographic area to search within.

    Overpass expects the bounding box as ``south,west,north,east`` (note the
    order: it is *not* the usual latitude/longitude pairing).
    """

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self):
        if not -90 <= self.south <= 90 or not -90 <= self.north <= 90:
            raise ValueError(
                "Bounding box latitudes must be between -90 and 90."
            )

        if not -180 <= self.west <= 180 or not -180 <= self.east <= 180:
            raise ValueError(
                "Bounding box longitudes must be between -180 and 180."
            )

        if self.south >= self.north:
            raise ValueError(
                "Bounding box south must be lower than north."
            )

        if self.west >= self.east:
            raise ValueError(
                "Bounding box west must be lower than east."
            )

    def as_overpass_tuple(self):
        """Return the ``south,west,north,east`` string Overpass expects."""

        return (
            f"{self.south},{self.west},"
            f"{self.north},{self.east}"
        )


@dataclass(frozen=True)
class Place:
    """A single point of interest, normalized for application use.

    Optional fields are ``None`` when the source genuinely does not provide
    the information. They are never filled with invented values.
    """

    source: str
    source_id: str
    name: str
    category: PlaceCategory
    latitude: float
    longitude: float
    address: Optional[str] = None
    opening_hours: Optional[str] = None


__all__ = [
    "PlaceSource",
    "PlaceCategory",
    "CATEGORY_SELECTORS",
    "CATEGORY_TAG_RULES",
    "BoundingBox",
    "Place",
]
