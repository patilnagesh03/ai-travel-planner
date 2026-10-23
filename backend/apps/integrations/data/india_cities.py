"""
Curated destination data for India-first place discovery.

The Overpass API searches by *coordinates*, but a user types a destination
name ("Mumbai", "Bengaluru, Karnataka"). This module holds a small, curated
mapping from destination names to the bounding boxes we are willing to
search.

Why a curated list instead of a geocoding service
--------------------------------------------------
* The public Overpass instances are shared infrastructure. Geocoding every
  request separately doubles the number of external calls we make.
* A curated list keeps the search area small and predictable. Every entry
  here describes one city, never a region or a whole state.
* It needs no new provider, no API key and no extra infrastructure.

The trade-off is honest: a destination that is not in this list cannot be
searched by name. That is reported explicitly rather than silently failing.
A caller who knows the coordinates can always search those instead.

Each entry is deliberately a *city*, and the bounding boxes are sized to
cover the main urban area (including well-known suburbs), not the entire
district or state.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class City:
    """A curated, searchable destination."""

    name: str
    state: str
    south: float
    west: float
    north: float
    east: float
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def center(self):
        """The geographic centre of the bounding box."""

        return (
            (self.south + self.north) / 2,
            (self.west + self.east) / 2,
        )


# The curated set. Ordered by how likely a traveller is to search for them.
INDIA_CITIES = (
    City(
        name="Mumbai",
        state="Maharashtra",
        south=18.8930,
        west=72.7850,
        north=19.2760,
        east=72.9900,
        aliases=("bombay", "mum", "mumbai city", "navi mumbai"),
    ),
    City(
        name="Delhi",
        state="Delhi",
        south=28.4000,
        west=76.8400,
        north=28.7400,
        east=77.3500,
        aliases=("new delhi", "ndls", "delhi ncr", "ncr"),
    ),
    City(
        name="Bengaluru",
        state="Karnataka",
        south=12.8300,
        west=77.4500,
        north=13.1500,
        east=77.7500,
        aliases=("bangalore", "blr", "bengaluru urban"),
    ),
    City(
        name="Hyderabad",
        state="Telangana",
        south=17.2400,
        west=78.3000,
        north=17.5600,
        east=78.6200,
        aliases=("hyd", "secunderabad", "hyderabad city"),
    ),
    City(
        name="Chennai",
        state="Tamil Nadu",
        south=12.9800,
        west=80.1500,
        north=13.2400,
        east=80.3600,
        aliases=("madras", "chennai city"),
    ),
    City(
        name="Kolkata",
        state="West Bengal",
        south=22.4200,
        west=88.2000,
        north=22.6300,
        east=88.4700,
        aliases=("calcutta", "kolkata city"),
    ),
    City(
        name="Pune",
        state="Maharashtra",
        south=18.4400,
        west=73.7800,
        north=18.6200,
        east=74.0200,
        aliases=("poona", "pune city"),
    ),
    City(
        name="Ahmedabad",
        state="Gujarat",
        south=23.0100,
        west=72.5000,
        north=23.2400,
        east=72.6500,
        aliases=("amd", "ahmedabad city"),
    ),
    City(
        name="Jaipur",
        state="Rajasthan",
        south=26.8000,
        west=75.7200,
        north=27.0300,
        east=75.8700,
        aliases=("jpr", "jaipur city"),
    ),
    City(
        name="Lucknow",
        state="Uttar Pradesh",
        south=26.7900,
        west=80.8600,
        north=26.9400,
        east=81.0300,
        aliases=("lko", "lucknow city"),
    ),
    City(
        name="Kochi",
        state="Kerala",
        south=9.9000,
        west=76.2000,
        north=10.1600,
        east=76.3600,
        aliases=("cochin", "kochi city"),
    ),
    City(
        name="Thiruvananthapuram",
        state="Kerala",
        south=8.4700,
        west=76.9200,
        north=8.5500,
        east=77.0200,
        aliases=("trivandrum", "tvm", "thiruvananthapuram city"),
    ),
    City(
        name="Goa",
        state="Goa",
        south=14.9000,
        west=73.7000,
        north=15.7500,
        east=74.4000,
        aliases=("goa state", "north goa", "south goa"),
    ),
    City(
        name="Agra",
        state="Uttar Pradesh",
        south=27.1600,
        west=78.0200,
        north=27.2400,
        east=78.1000,
        aliases=("agra city",),
    ),
    City(
        name="Varanasi",
        state="Uttar Pradesh",
        south=25.2800,
        west=82.9600,
        north=25.4000,
        east=83.0400,
        aliases=("banaras", "kashi", "varanasi city"),
    ),
    City(
        name="Amritsar",
        state="Punjab",
        south=31.5800,
        west=74.8200,
        north=31.6800,
        east=74.9300,
        aliases=("amritsar city",),
    ),
    City(
        name="Chandigarh",
        state="Chandigarh",
        south=30.7200,
        west=76.7700,
        north=30.7900,
        east=76.8600,
        aliases=("chandigarh city",),
    ),
    City(
        name="Indore",
        state="Madhya Pradesh",
        south=22.6600,
        west=75.8100,
        north=22.7800,
        east=75.9200,
        aliases=("indore city",),
    ),
    City(
        name="Bhopal",
        state="Madhya Pradesh",
        south=23.1900,
        west=77.3900,
        north=23.2800,
        east=77.4500,
        aliases=("bhopal city",),
    ),
    City(
        name="Patna",
        state="Bihar",
        south=25.5300,
        west=85.1000,
        north=25.6400,
        east=85.2000,
        aliases=("patna city",),
    ),
    City(
        name="Nagpur",
        state="Maharashtra",
        south=20.9600,
        west=79.0200,
        north=21.1000,
        east=79.1600,
        aliases=("nagpur city",),
    ),
    City(
        name="Bhubaneswar",
        state="Odisha",
        south=20.2600,
        west=85.7600,
        north=20.3800,
        east=85.8500,
        aliases=("bhubaneshwar", "bhubaneswar city"),
    ),
    City(
        name="Coimbatore",
        state="Tamil Nadu",
        south=11.0000,
        west=76.9300,
        north=11.0800,
        east=77.0200,
        aliases=("coimbatore city", "kovai"),
    ),
    City(
        name="Madurai",
        state="Tamil Nadu",
        south=9.9000,
        west=78.0800,
        north=10.0000,
        east=78.1800,
        aliases=("madurai city", "madura"),
    ),
    City(
        name="Visakhapatnam",
        state="Andhra Pradesh",
        south=17.6800,
        west=83.2000,
        north=17.7500,
        east=83.3200,
        aliases=("vizag", "visakhapatnam city"),
    ),
    City(
        name="Mysuru",
        state="Karnataka",
        south=12.2900,
        west=76.6000,
        north=12.3400,
        east=76.6800,
        aliases=("mysore", "mysuru city"),
    ),
    City(
        name="Udaipur",
        state="Rajasthan",
        south=24.5600,
        west=73.6600,
        north=24.6400,
        east=73.7300,
        aliases=("udaipur city",),
    ),
    City(
        name="Jaisalmer",
        state="Rajasthan",
        south=26.8800,
        west=70.9000,
        north=26.9600,
        east=71.0200,
        aliases=("jaisalmer city", "golden city"),
    ),
    City(
        name="Pushkar",
        state="Rajasthan",
        south=26.4800,
        west=74.8000,
        north=26.5100,
        east=74.8600,
        aliases=("pushkar city",),
    ),
    City(
        name="Rishikesh",
        state="Uttarakhand",
        south=30.0800,
        west=78.2600,
        north=30.1200,
        east=78.3200,
        aliases=("rishikesh city",),
    ),
    City(
        name="Haridwar",
        state="Uttarakhand",
        south=29.9400,
        west=78.1500,
        north=30.0000,
        east=78.2400,
        aliases=("haridwar city",),
    ),
    City(
        name="Dehradun",
        state="Uttarakhand",
        south=30.2800,
        west=77.7000,
        north=30.3800,
        east=77.9000,
        aliases=("dehradoon", "dehradun city"),
    ),
    City(
        name="Dharamshala",
        state="Himachal Pradesh",
        south=32.1900,
        west=76.3000,
        north=32.2500,
        east=76.4000,
        aliases=("dharamshala city",),
    ),
    City(
        name="Manali",
        state="Himachal Pradesh",
        south=32.2000,
        west=77.1600,
        north=32.3200,
        east=77.2800,
        aliases=("manali town",),
    ),
    City(
        name="Shimla",
        state="Himachal Pradesh",
        south=31.1000,
        west=77.1400,
        north=31.1400,
        east=77.2000,
        aliases=("shimla city",),
    ),
    City(
        name="Kedarnath",
        state="Uttarakhand",
        south=30.7200,
        west=79.0400,
        north=30.7600,
        east=79.1000,
        aliases=("kedarnath temple", "kedarnath yatra"),
    ),
    City(
        name="Badrinath",
        state="Uttarakhand",
        south=30.7300,
        west=79.4900,
        north=30.7600,
        east=79.5300,
        aliases=("badrinath temple",),
    ),
    City(
        name="Ooty",
        state="Tamil Nadu",
        south=11.3800,
        west=76.6800,
        north=11.4500,
        east=76.7800,
        aliases=("ooty city", "udagamandalam"),
    ),
    City(
        name="Munnar",
        state="Kerala",
        south=10.0600,
        west=77.0500,
        north=10.1000,
        east=77.1000,
        aliases=("munnar town",),
    ),
    City(
        name="Madikeri",
        state="Karnataka",
        south=12.4200,
        west=75.7200,
        north=12.4600,
        east=75.7800,
        aliases=("coorg", "kodagu", "madikeri city"),
    ),
    City(
        name="Leh",
        state="Ladakh",
        south=34.1300,
        west=77.5300,
        north=34.1800,
        east=77.6000,
        aliases=("leh ladakh", "leh city"),
    ),
    City(
        name="Srinagar",
        state="Jammu and Kashmir",
        south=34.0600,
        west=74.7800,
        north=34.1200,
        east=74.8600,
        aliases=("srinagar city",),
    ),
    City(
        name="Gangtok",
        state="Sikkim",
        south=27.3000,
        west=88.6000,
        north=27.3600,
        east=88.6800,
        aliases=("gangtok city",),
    ),
    City(
        name="Port Blair",
        state="Andaman and Nicobar Islands",
        south=11.6000,
        west=92.6300,
        north=11.6800,
        east=92.7500,
        aliases=("port blair city",),
    ),
    City(
        name="Ranchi",
        state="Jharkhand",
        south=23.3400,
        west=85.2800,
        north=23.4000,
        east=85.3600,
        aliases=("ranchi city",),
    ),
    City(
        name="Raipur",
        state="Chhattisgarh",
        south=21.1800,
        west=81.5500,
        north=21.2600,
        east=81.6500,
        aliases=("raipur city",),
    ),
    City(
        name="Mahabaleshwar",
        state="Maharashtra",
        south=20.0000,
        west=73.6200,
        north=20.0600,
        east=73.6800,
        aliases=("mahabaleshwar city",),
    ),
    City(
        name="Rameswaram",
        state="Tamil Nadu",
        south=9.2800,
        west=79.3000,
        north=9.3000,
        east=79.3400,
        aliases=("rameswaram island", "ramaswaram", "rameshwaram"),
    ),
)


__all__ = ["City", "INDIA_CITIES"]
