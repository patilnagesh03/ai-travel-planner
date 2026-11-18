"""
The normalized structure of a generated itinerary.

The model returns a rough shape. This module defines what a *validated*
plan looks like, and the service layer is responsible for turning one into
the other.

Two rules shape everything here:

* The model never supplies a date. We assign the trip dates ourselves, so
  the model cannot invent a day that is outside the trip.
* The model never supplies coordinates. Every item points at a place we
  already offered it, and the coordinates come from our own data.
"""

from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Optional


@dataclass
class GeneratedItem:
    """One activity in a generated day."""

    title: str
    description: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    activity_type: str = "other"
    place_source_id: Optional[str] = None
    place_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None

    @property
    def place(self):
        """The place this activity refers to.

        The coordinates and the address come from our own place data, never
        from the model, so this is always safe to show.
        """

        return {
            "source_id": self.place_source_id,
            "name": self.place_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
        }


@dataclass
class GeneratedDay:
    """One day of a generated plan."""

    date: date
    items: List[GeneratedItem] = field(default_factory=list)


@dataclass
class GeneratedPlan:
    """A complete, validated itinerary plan."""

    title: str
    description: Optional[str] = None
    days: List[GeneratedDay] = field(default_factory=list)

    @property
    def item_count(self):
        return sum(len(day.items) for day in self.days)


__all__ = [
    "GeneratedItem",
    "GeneratedDay",
    "GeneratedPlan",
]
