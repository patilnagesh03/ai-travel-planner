# Integrations App

External service integrations for the AI Travel Planner.

This app currently contains **three** provider integrations, none of which
needs an API key:

* Place discovery backed by OpenStreetMap data through the
  [Overpass API](https://overpass-api.de/).
* Daily weather forecasts from [Open-Meteo](https://open-meteo.com/).
* Exchange rates from the European Central Bank, published by
  [Frankfurter](https://frankfurter.dev/).

All three are read-through: nothing from a provider is stored in our database.

---

## Layout

```text
backend/apps/integrations/
├── config.py                     # Configuration read from Django settings
├── responses.py                  # Shared provider-error -> HTTP mapping
├── data/
│   └── india_cities.py           # Curated India-first destination boxes
├── clients/
│   ├── overpass_client.py        # HTTP transport for the Overpass API
│   ├── open_meteo_client.py      # HTTP transport for Open-Meteo
│   ├── frankfurter_client.py     # HTTP transport for Frankfurter
│   └── ...
├── schemas/
│   ├── place_schema.py           # Normalized Place / BoundingBox structures
│   └── ...
├── services/
│   ├── places_service.py         # Query building + normalization
│   ├── destination_service.py    # Destination name -> search area
│   ├── weather_service.py        # Forecast window + trip-date filtering
│   ├── currency_service.py       # Currency validation + rate caching
│   └── ...
├── serializers/
│   ├── place_serializer.py       # Query validation + JSON representation
│   ├── currency_serializer.py
│   ├── destination_serializer.py
│   └── ...
├── views/
│   ├── place_view.py             # Place discovery + destination resolution
│   ├── weather_view.py           # Trip weather endpoint
│   ├── currency_view.py          # Exchange-rate endpoint
│   └── ...
├── exceptions/
│   ├── integration_exceptions.py # Meaningful integration failures
│   └── ...
├── urls.py
└── tests/
    ├── test_overpass_client.py
    ├── test_open_meteo_client.py
    ├── test_frankfurter_client.py
    ├── test_places_service.py
    ├── test_destination_service.py
    ├── test_weather_service.py
    ├── test_currency_service.py
    ├── test_place_view.py
    ├── test_weather_view.py
    ├── test_currency_view.py
    ├── test_destination_resolve.py
    └── test_live_overpass.py     # Opt-in, hits the real provider
```

### Why the layers are split this way

| Layer | Responsibility |
|---|---|
| `clients/` | Talks HTTP. Knows nothing about trips, places or currencies. |
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
| `WEATHER_API_URL` | `https://api.open-meteo.com/v1/forecast` | Open-Meteo endpoint. |
| `WEATHER_CONNECT_TIMEOUT` | `5` | Client-side connect timeout (seconds). |
| `WEATHER_READ_TIMEOUT` | `15` | Client-side read timeout (seconds). |
| `WEATHER_FORECAST_DAYS` | `16` | Forecast window. Clamped to the provider's 16-day maximum. |
| `WEATHER_CACHE_TIMEOUT` | `900` | Seconds a forecast is reused. `0` disables caching. |
| `CURRENCY_API_URL` | `https://api.frankfurter.dev/v1` | Frankfurter endpoint. |
| `CURRENCY_CONNECT_TIMEOUT` | `5` | Client-side connect timeout (seconds). |
| `CURRENCY_READ_TIMEOUT` | `10` | Client-side read timeout (seconds). |
| `CURRENCY_CACHE_TIMEOUT` | `3600` | Seconds a rate set is reused. `0` disables caching. |
| `MAX_CURRENCY_SYMBOLS` | `12` | Hard cap on target currencies per request. |

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

### `GET /api/v1/trips/<trip_id>/flights/`

Deterministic flight search links for the trip. No provider is called and no
fare data is returned: the links are derived from the trip's `origin`,
`destination`, dates and traveller count, so the same trip always produces the
same URLs.

`trip.origin` is optional on the model, but it is required here. A trip
without one returns `400` with a message explaining how to add it, rather than
guessing a departure city.

```json
{
  "success": true,
  "message": "Flight links retrieved successfully.",
  "data": {
    "origin": "Delhi",
    "destination": "Goa",
    "start_date": "2026-11-10",
    "end_date": "2026-11-15",
    "travelers": 2,
    "disclaimer": "This app does not fetch or store live fares. ...",
    "links": [
      {
        "provider": "google_flights",
        "label": "Google Flights",
        "url": "https://www.google.com/travel/flights?q=..."
      },
      {
        "provider": "kayak",
        "label": "Kayak",
        "url": "https://www.kayak.co.in/flights/Delhi-Goa/2026-11-10/2026-11-15"
      }
    ]
  }
}
```

The traveller chooses the provider; any price or availability they see belongs
to that provider, not to this application.

### `GET /api/v1/trips/<trip_id>/hotels/`

Accommodation around the trip's destination, from the same OpenStreetMap /
Overpass pipeline as the place search. Results are restricted to `hotel`,
`guest_house`, `hostel` and `apartment`, then ordered by their haversine
distance from the curated city centre.

| Query parameter | Type | Notes |
|---|---|---|
| `limit` | int | `1`..`20`. Default `20`. Applied after distance sorting. |

Each hotel carries the normal `Place` fields plus `distance_km`. The response
also includes the resolved `destination`, an `attribution` string and a
`booking_url` that opens a Booking.com search for the same dates and party:

```json
{
  "success": true,
  "message": "Hotels retrieved successfully.",
  "data": {
    "destination": {
      "name": "Bengaluru",
      "state": "Karnataka",
      "latitude": 12.99,
      "longitude": 77.6
    },
    "hotels": [
      {
        "source": "openstreetmap",
        "source_id": "node/12345",
        "name": "Riverside Inn",
        "category": "guest_house",
        "latitude": 12.991,
        "longitude": 77.601,
        "address": "1 River Road",
        "opening_hours": null,
        "distance_km": 0.15
      }
    ],
    "booking_url": "https://www.booking.com/searchresults.html?...",
    "attribution": "Accommodation data © OpenStreetMap contributors."
  }
}
```

Because it uses Overpass, this endpoint shares the place search's error
mapping: an unsupported destination is a `400`, and a provider outage is a
`503`. Results are cached with the rest of the place searches.

### `GET /api/v1/places/destinations/`

Lists the curated destinations that can be searched by name. Useful for
building a dropdown in the frontend.

### `GET /api/v1/places/resolve/?destination=Jaipur`

Resolves a destination to the curated city's centre and bounding box. The map
uses this so the frontend does not have to duplicate the backend's spelling,
alias and state rules.

```json
{
  "success": true,
  "message": "Destination resolved successfully.",
  "data": {
    "name": "Jaipur",
    "state": "Rajasthan",
    "aliases": ["jpr", "jaipur city"],
    "latitude": 26.915,
    "longitude": 75.795,
    "bbox": {
      "south": 26.8,
      "west": 75.72,
      "north": 27.03,
      "east": 75.87
    }
  }
}
```

### `GET /api/v1/trips/<trip_id>/weather/`

Daily forecast for the trip's destination and dates. Ownership is enforced:
another user's trip returns `404`.

The provider publishes a fixed 16-day window starting today. A trip can be in
the past, far in the future, or longer than that window, so the response says
exactly what it could cover:

```json
{
  "success": true,
  "message": "Forecast retrieved successfully.",
  "data": {
    "destination": {
      "name": "Jaipur",
      "state": "Rajasthan",
      "latitude": 26.915,
      "longitude": 75.795
    },
    "timezone": "Asia/Kolkata",
    "units": {
      "temperature": "°C",
      "wind_speed": "km/h",
      "precipitation_probability": "%"
    },
    "forecast_window": {
      "starts_on": "2026-10-30",
      "ends_on": "2026-11-14"
    },
    "trip_days": 4,
    "covered_days": 4,
    "days": [
      {
        "date": "2026-11-02",
        "weather_code": 0,
        "condition": "Clear sky",
        "temperature_max": 28.4,
        "temperature_min": 18.0,
        "precipitation_probability": 0,
        "wind_speed_max": 12.1,
        "sunrise": "2026-11-02T06:36",
        "sunset": "2026-11-02T17:48"
      }
    ],
    "note": null,
    "attribution": "Weather data by Open-Meteo.com"
  }
}
```

* Only days that are both **inside the trip** and **inside the forecast
  window** are returned.
* A trip entirely outside the window returns `200` with `days: []` and a
  `note` explaining when weather will appear.
* A partially covered trip includes a note saying where coverage stops.
* An unsupported destination returns `400`. The same curated city list is used
  as for place search.

### `GET /api/v1/currency/rates/?base=INR&symbols=USD,EUR`

Latest reference rates for a base currency. `base` defaults to `INR`.
`symbols` is required, comma separated, and capped by `MAX_CURRENCY_SYMBOLS`.

```json
{
  "success": true,
  "message": "Rates retrieved successfully.",
  "data": {
    "base": "INR",
    "date": "2026-10-30",
    "rates": { "USD": 0.010532, "EUR": 0.0094268 },
    "attribution": "Rates from the European Central Bank via Frankfurter"
  }
}
```

* The base currency cannot also appear in `symbols`.
* Rates are reference rates, not a bank quote. The attribution is part of the
  payload and must be shown next to the numbers.
* Frankfurter answers `200` and silently omits a symbol it does not publish
  when at least one requested symbol is known. A partial response is reported
  as `400` naming the unsupported codes, not as a provider outage.
* If none of the requested symbols is published, the provider returns `404`,
  which is also a `400` to the caller.

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

### Place categories

| Value | OSM tag | Notes |
|---|---|---|
| `attraction` | `tourism=attraction` | Also matches `tourism=gallery`. |
| `museum` | `tourism=museum` | |
| `viewpoint` | `tourism=viewpoint` | |
| `monument` | `historic=monument` | Also matches `historic=memorial`. |
| `religious_site` | `amenity=place_of_worship` | |
| `park` | `leisure=park` | |
| `restaurant` | `amenity=restaurant` | |
| `cafe` | `amenity=cafe` | |
| `hotel` | `tourism=hotel` | Also matches `tourism=motel`. |
| `guest_house` | `tourism=guest_house` | |
| `hostel` | `tourism=hostel` | |
| `apartment` | `tourism=apartment` | |
| `other` | — | Defensive fallback; never queried for. |

The four accommodation categories are grouped in `HOTEL_CATEGORIES`, which is
what the hotel endpoint searches.

---

## Errors

Every provider failure is raised as one of the exceptions in
`exceptions/integration_exceptions.py`, and mapped to an HTTP status by the
views:

| Exception | Cause | HTTP status |
|---|---|---|
| `UnsupportedDestinationError` | Destination not in the curated list | `400` |
| `UnsupportedCurrencyError` | Currency code malformed or not published | `400` |
| `IntegrationRequestError` | HTTP 4xx (bad query/request) | `400` |
| `IntegrationRateLimitError` | HTTP 429 | `429` (+ `Retry-After`) |
| `IntegrationResponseError` | Invalid JSON, unexpected structure | `502` |
| `IntegrationTimeoutError` | Connect or read timeout | `503` |
| `IntegrationUnavailableError` | HTTP 500/502/503/504, connection failure | `503` |

`UnsupportedDestinationError` and `UnsupportedCurrencyError` are deliberately
**not** subclasses of `IntegrationError`. They are problems with the caller's
input, not a provider outage, and a caller that catches `IntegrationError` to
report "the provider is having trouble" must not accidentally report these.

The mapping itself lives in `responses.py` so the places, weather and currency
views cannot drift apart. Provider messages name the integration ("The weather
provider ...", "The currency provider ...") so a failure is actionable without
exposing URLs, response bodies or stack traces.

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
* **Nothing is persisted.** Place data, forecasts and rates are read through,
  normalized and returned. No provider data is stored in our database, which
  keeps the ODbL retention question out of scope.
* **OpenStreetMap data is ODbL licensed.** Any UI showing place data must
  display the attribution *"© OpenStreetMap contributors"*. The map component
  does this through Leaflet's attribution control.
* **Weather and rates are cached separately** from place results, with their
  own timeouts (15 minutes and 1 hour by default). Both caches are
  per-process `LocMemCache`, so a multi-worker deployment keeps one cache per
  worker.

### Weather specifics

* **The forecast is never extrapolated.** If the provider covers only part of
  a trip, the response contains only those days. A note explains the gap
  instead of inventing values.
* **Units are explicit.** Temperatures are Celsius, wind is km/h and
  precipitation is a probability percentage. The response carries the unit
  strings so the UI does not hardcode them.
* **Missing values stay `null`.** A missing temperature or probability is not
  turned into `0`, because `0 °C` and "no value" mean different things.
* **WMO codes are translated server-side.** The frontend receives a
  human-readable `condition` label, not a numeric code to interpret.
* **Attribution is required.** Open-Meteo asks clients to credit it; the
  payload includes `"Weather data by Open-Meteo.com"`.

### Currency specifics

* **Rates come from the ECB**, via Frankfurter, and change once per working
  day. A request is cached for an hour.
* **Codes are validated before the provider is called.** Malformed codes
  (anything that is not three ASCII letters) are rejected locally.
* **No conversion arithmetic is done by the provider client.** The client
  returns rates; the frontend multiplies the traveller's amount by a rate.
* **Only provider-supported currencies can be offered.** Frankfurter publishes
  a fixed set. Requesting an unsupported code is a `400`, not a silent zero.

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

* **Provider failover.** Each integration uses one configured endpoint.
  Overpass mirrors are not tried automatically, and there is no retry policy.
* **Live tests for weather and currency.** Their clients and services are
  covered with mocked HTTP; only place discovery has an opt-in live test.
* **Accommodation and routing discovery.**
* **Place persistence.** Places are returned, never stored.
* **A shared cache.** All caches use Django's per-process `LocMemCache`. A
  multi-worker deployment would need Redis or a database cache to share them.
