"""
Configuration for external service integrations.

Every value here is read from Django settings so that it can be overridden
per environment (``.env`` -> ``settings.py`` -> this module).

Two different kinds of timeout live in this project and they are NOT
interchangeable:

* ``OVERPASS_CONNECT_TIMEOUT`` / ``OVERPASS_READ_TIMEOUT``
  Client-side transport timeouts enforced by ``requests``. They bound how long
  *we* wait on the network.

* ``OVERPASS_QUERY_TIMEOUT``
  A server-side budget handed to Overpass inside the query itself
  (``[out:json][timeout:N]``). It bounds how long *the provider* keeps working.
"""

from django.conf import settings


OVERPASS_API_URL = settings.OVERPASS_API_URL

OVERPASS_CONNECT_TIMEOUT = settings.OVERPASS_CONNECT_TIMEOUT

OVERPASS_READ_TIMEOUT = settings.OVERPASS_READ_TIMEOUT

OVERPASS_QUERY_TIMEOUT = settings.OVERPASS_QUERY_TIMEOUT

MAX_PLACES_PER_SEARCH = settings.MAX_PLACES_PER_SEARCH

INTEGRATIONS_USER_AGENT = settings.INTEGRATIONS_USER_AGENT

# How long (seconds) a place search result is reused before the provider is
# called again. 0 disables caching entirely.
PLACES_CACHE_TIMEOUT = settings.PLACES_CACHE_TIMEOUT

# Force the IPv4 address family when talking to the provider.
#
# Some networks publish IPv6 addresses for a host but cannot route IPv6
# traffic, which makes every request hang until it times out. Turning this
# on works around that. It is off by default because forcing IPv4 would
# break a network that is genuinely IPv6-only.
OVERPASS_IPV4_ONLY = settings.OVERPASS_IPV4_ONLY


__all__ = [
    "OVERPASS_API_URL",
    "OVERPASS_CONNECT_TIMEOUT",
    "OVERPASS_READ_TIMEOUT",
    "OVERPASS_QUERY_TIMEOUT",
    "MAX_PLACES_PER_SEARCH",
    "INTEGRATIONS_USER_AGENT",
    "PLACES_CACHE_TIMEOUT",
    "OVERPASS_IPV4_ONLY",
]
