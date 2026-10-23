# Integrations App

External service integrations for the AI Travel Planner.

This app currently contains **one** provider integration: place discovery
backed by OpenStreetMap data through the
[Overpass API](https://overpass-api.de/).

---

## Layout

```text
backend/apps/integrations/
├── config.py                     # Configuration read from Django settings
├── data/
│   └── india_cities.py           # Curated India-first destination boxes
├── clients/
│   ├── overpass_client.py        # HTTP transport for the Overpass API
│   └── ...
├── schemas/
│   ├── place_schema.py           # Normalized Place / BoundingBox structures
│   └── ...
├── services/
│   ├── places_service.py         # Query building + normalization
│   ├── destination_service.py    # Destination name -> search area
│   └── ...
├── serializers/
│   └── place_serializer.py       # Query validation + JSON representation
├── views/
│   └── place_view.py             # Place discovery endpoints
├── exceptions/
│   ├── integration_exceptions.py # Meaningful integration failures
│   └── ...
├── urls.py
└── tests/
    ├── test_overpass_client.py
    ├── test_places_service.py
    ├── test_destination_service.py
    ├── test_place_view.py
    └── test_live_overpass.py     # Opt-in, hits the real provider
```

### Why the layers are split this way

| Layer | Responsibility |
|---|---|
| `clients/` | Talks HTTP. Knows nothing about places. |
| `services/` | Application logic: what to ask for, how to interpret the answer. |
| `schemas/` | The stable, provider-agnostic data contract. |
| `serializers/` | The only place where internal structures become JSON. |
| `views/` | HTTP concerns: auth, status codes, error mapping. |
| `data/` | Curated reference data with no runtime dependency. |
| `exceptions/` | Meaningful failures the layer above can map to HTTP statuses. |

---

## Configuration

All values live in `backend/settings.py` and can be overridden through
`.env`:

| Setting | Default | Meaning |
|---|---|---|
| `OVERPASS_API_URL` | `https://overpass-api.de/api/interpreter` | Overpass endpoint. |
| `OVERPASS_CONNECT_TIMEOUT` | `5` | Client-side connect timeout (seconds). |
| `OVERPASS_READ_TIMEOUT` | `30` | Client-side read timeout (seconds). |
| `OVERPASS_QUERY_TIMEOUT` | `20` | Server-side query budget (seconds). |
| `MAX_PLACES_PER_SEARCH` | `20` | Hard cap on places returned per search. |
| `INTEGRATIONS_USER_AGENT` | `AITravelPlanner/1.0 (nageshpatil7311@gmail.com)` | Identifies us to the provider. |
| `PLACES_CACHE_TIMEOUT` | `600` | Seconds a result is reused. `0` disables caching. |
| `OVERPASS_IPV4_ONLY` | `False` | Force the IPv4 address family. See below. |

### Two different timeouts, on purpose

`OVERPASS_CONNECT_TIMEOUT` / `OVERPASS_READ_TIMEOUT` are enforced **by us**
through `requests`. `OVERPASS_QUERY_TIMEOUT` is a budget we hand **to the
provider** inside the query (`[out:json][timeout:20]`). They are not
interchangeable, and the read timeout is deliberately larger than the query
timeout so that a slow-but-finite provider query still has room to return.

### IPv4-only networks

Some networks publish IPv6 addresses for a host but cannot actually route
IPv6 traffic. A request to such a host then hangs until it times out, even
though IPv4 would have worked. Set `OVERPASS_IPV4_ONLY=True` to work
around that. The change is scoped to this one integration and is restored
afterwards.

It is off by default, because forcing IPv4 would break a network that is
genuinely IPv6-only, and because most systems already fall back to IPv4 on
their own. It is a safety net for a broken network, not a default.

### The public instance is shared and often busy

`overpass-api.de` runs a small number of query workers for the whole
internet. When they are all busy it answers with **HTTP 502** and a message
saying it is at capacity. That is a *temporary* provider failure, and the
client maps it to `IntegrationUnavailableError`.

The client deliberately does not retry on its own (see below), so a busy
moment surfaces as a `503` to the API caller rather than being hidden.

The shared instance is also **slow**. A simple query can take 30-40 seconds
from a cold start, because the request waits for a worker to become free.
The default `OVERPASS_READ_TIMEOUT` of 30 seconds is therefore marginal
against this particular public instance, and a longer value is often
needed for the live test. That is a property of the shared infrastructure,
not of the query.

If you need higher throughput or predictable latency, run your own Overpass
instance and point `OVERPASS_API_URL` at it.

### The User-Agent

The Overpass usage policy asks every client to identify itself with a
meaningful `User-Agent` that offers a way to reach the operator. Set
`INTEGRATIONS_USER_AGENT` in your `.env` if you want to change it:

```dotenv
INTEGRATIONS_USER_AGENT=AITravelPlanner/1.0 (contact@example.com)
```

---

## API

All endpoints require a Bearer token (`Authorization: Bearer <access token>`).

### `GET /api/v1/places/search/`

Search for places by destination name **or** by coordinates.

| Query parameter | Type | Notes |
|---|---|---|
| `destination` | string | Curated city name. Optional if coordinates are given. |
| `latitude` | float | `-90`..`90`. Must be given together with `longitude`. |
| `longitude` | float | `-180`..`180`. Must be given together with `latitude`. |
| `radius_km` | float | `0.1`..`25`. Only used with coordinates. Default `5`. |
| `categories` | string | Comma separated. e.g. `attraction,museum`. |
| `limit` | int | `1`..`20`. Default `20`. |

```bash
curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/api/v1/places/search/?destination=Bengaluru&categories=attraction,museum"
```

Coordinates act as an **override**: when both are supplied, the coordinates
win.

```bash
curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/api/v1/places/search/?latitude=12.9716&longitude=77.5946&radius_km=5"
```

Response:

```json
{
  "success": true,
  "message": "Places retrieved successfully.",
  "data": [
    {
      "source": "openstreetmap",
      "source_id": "node/12345",
      "name": "Cubbon Park",
      "category": "park",
      "latitude": 12.9763,
      "longitude": 77.6033,
      "address": "MG Road, Bengaluru",
      "opening_hours": null
    }
  ]
}
```

### `GET /api/v1/trips/<trip_id>/places/`

The same search, scoped to the destination of one of your trips. Ownership is
enforced; another user's trip returns `404`. A `destination` query parameter
is ignored — the trip's own destination always wins.

### `GET /api/v1/places/destinations/`

Lists the curated destinations that can be searched by name. Useful for
building a dropdown in the frontend.

---

## Destinations

`Trip.destination` is free text, but Overpass needs coordinates. The
resolution order is:

1. **Coordinates** (`latitude` + `longitude`) — used directly, building a
   box of `radius_km` around the point. Coordinates always win.
2. **Curated city list** — `data/india_cities.py` maps city names, aliases,
   state names and state codes onto a bounding box.
3. **Otherwise** — `UnsupportedDestinationError`, surfaced as a `400` with a
   message that says exactly what went wrong.

Accepted spellings include `Mumbai`, `mumbai`, `Bombay`, `Mumbai,
Maharashtra`, `Mumbai Maharashtra`, `Mumbai MH` and `Mumbai, India`.

A destination that names a known city but contradicts its state is reported
explicitly:

```
"Mumbai, Karnataka" does not match a supported destination.
Mumbai is in Maharashtra, not karnataka.
```

### Why a curated list and not geocoding

* The public Overpass instances are shared infrastructure. Geocoding every
  request separately doubles the external calls we make.
* A curated list keeps the search area small and predictable. Every entry
  describes one city, never a region or a whole state.
* It needs no new provider, no API key and no extra infrastructure.

The trade-off is honest: a city that is not in the list cannot be searched
by name. That is reported explicitly rather than silently returning nothing.

---

## The `Place` structure

| Field | Type | Notes |
|---|---|---|
| `source` | `str` | Always `"openstreetmap"`. |
| `source_id` | `str` | Stable id, e.g. `"node/12345"`, `"way/678"`, `"relation/9"`. |
| `name` | `str` | Always present; elements without a name are dropped. |
| `category` | `PlaceCategory` | One of the constrained categories. |
| `latitude` / `longitude` | `float` | Always present. |
| `address` | `str \| None` | `None` when OSM has no `addr:*` tags. |
| `opening_hours` | `str \| None` | Raw `opening_hours` tag, passed through unparsed. |

---

## Errors

Every provider failure is raised as one of the exceptions in
`exceptions/integration_exceptions.py`, and mapped to an HTTP status by the
views:

| Exception | Cause | HTTP status |
|---|---|---|
| `UnsupportedDestinationError` | Destination not in the curated list | `400` |
| `IntegrationRequestError` | HTTP 4xx (bad query/request) | `400` |
| `IntegrationRateLimitError` | HTTP 429 | `429` (+ `Retry-After`) |
| `IntegrationResponseError` | Invalid JSON, unexpected structure | `502` |
| `IntegrationTimeoutError` | Connect or read timeout | `503` |
| `IntegrationUnavailableError` | HTTP 500/502/503/504, connection failure | `503` |

`UnsupportedDestinationError` is deliberately **not** a subclass of
`IntegrationError`. It is a problem with the caller's input, not a provider
outage, and a caller that catches `IntegrationError` to report "the provider
is having trouble" must not accidentally report this one.

`IntegrationRateLimitError` and `IntegrationUnavailableError` carry a
`retry_after` attribute holding the provider's `Retry-After` value (in
seconds) when it supplied one.

Unexpected exceptions are **not** caught. They propagate to Django, which
logs the traceback and returns a generic `500`. The views only handle
failures they can actually explain.

---

## Behaviour and deliberate limitations

* **No automatic retries.** The public Overpass instances are shared and
  already heavily loaded. A retry policy can multiply load on an overloaded
  service. `retry_after` is surfaced so a caller can decide for itself.
* **Results are cached.** A search is cached for `PLACES_CACHE_TIMEOUT`
  seconds, keyed on the query itself. The public Overpass instances are
  shared infrastructure, and repeating the same search should not cost the
  provider another request. The cache uses Django's built-in `LocMemCache`,
  so there is no Redis to run. It is per-process, which means a multi-worker
  deployment keeps one cache per worker. Set the timeout to `0` to turn it
  off. Only successful results are cached; a failure is never replayed.
* **A valid query with no matches returns an empty list**, not an error.
* **The query is constrained three ways** — a bounding box, a fixed set of
  tag selectors, and an output limit. Limiting the final response alone
  would not be enough; the provider must also be spared the work.
* **`MAX_PLACES_PER_SEARCH` is a ceiling, not a default.** A caller may ask
  for fewer places, never more. The API rejects an oversized `limit` with a
  `400` rather than silently clamping it.
* **Nothing is persisted.** Place data is read through, normalized and
  returned. No provider data is stored in our database, which keeps the
  ODbL retention question out of scope.
* **No caching.** Every request reaches the provider. Adding a cache is a
  deliberate decision that has not been made yet.
* **OpenStreetMap data is ODbL licensed.** Any UI showing place data must
  display the attribution *"© OpenStreetMap contributors"*.

### Data quality

OpenStreetMap coverage is uneven. Rural areas, small towns and recent
developments are often sparse or missing entirely. The integration therefore
**never invents** data: a place with no name or no coordinates is dropped,
and optional fields are `None` when the source does not supply them. In
particular, do not expect ratings or descriptions — they do not exist in the
OSM data model and are never generated.

---

## Tests

```bash
# Unit tests (mocked HTTP, no network needed)
python manage.py test backend.apps.integrations

# Opt-in live test against the real provider
# Windows PowerShell
$env:OVERPASS_LIVE_TEST = "1"
python manage.py test backend.apps.integrations.tests.test_live_overpass

# Linux / macOS
OVERPASS_LIVE_TEST=1 python manage.py test backend.apps.integrations.tests.test_live_overpass
```

The live test needs a working internet connection. Two things can get in the
way, and both are handled by configuration rather than by code changes:

* **A busy public instance.** The shared workers sometimes need 30-40
  seconds to pick a query up, which is longer than the 30 second default
  read timeout. Set `OVERPASS_READ_TIMEOUT=90`.
* **A network that advertises IPv6 but cannot route it.** Set
  `OVERPASS_IPV4_ONLY=True`. Most systems do not need this.

```powershell
$env:OVERPASS_LIVE_TEST = "1"
$env:OVERPASS_READ_TIMEOUT = "90"
$env:OVERPASS_IPV4_ONLY = "True"
python manage.py test backend.apps.integrations.tests.test_live_overpass
```

---

## Not implemented yet

* **Caching.** Every call goes to the provider.
* **Other providers.** Weather, routing, currency and accommodation
  discovery are not implemented.
* **Place persistence.** Places are returned, never stored.
