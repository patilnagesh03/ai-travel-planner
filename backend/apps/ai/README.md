# AI App

AI-assisted itinerary generation.

The provider is **Groq**, which serves open-weight models over an
OpenAI-compatible API. A Groq account and API key are required; the key
lives in `backend/.env`, which git ignores.

---

## Layout

```text
backend/apps/ai/
├── config.py
├── clients/
│   ├── groq_client.py          # HTTP transport for the Groq API
│   └── ...
├── schemas/
│   └── itinerary_schema.py     # The validated plan structures
├── services/
│   ├── prompt_service.py       # Builds the prompt
│   ├── itinerary_generation_service.py
│   └── ...
├── serializers/
│   └── generation_serializer.py
├── views/
│   └── generation_view.py
├── exceptions/
│   ├── ai_exceptions.py
│   └── ...
└── tests/
```

---

## Configuration

| Setting | Default | Meaning |
|---|---|---|
| `AI_PROVIDER` | `groq` | Which provider to use. |
| `GROQ_API_KEY` | *(empty)* | Your Groq API key. Required. |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | The API base URL. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | The model to use. |
| `GROQ_TIMEOUT` | `60` | Seconds allowed for one generation. |
| `GROQ_TEMPERATURE` | `0.4` | Lower is more predictable. |

### Setting up Groq

1. Create a key at <https://console.groq.com/keys>.
2. Put it in `backend/.env` — never in a committed file:

   ```dotenv
   AI_PROVIDER=groq
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-120b
   ```

3. Check that the key and model work:

   ```bash
   curl -H "Authorization: Bearer $GROQ_API_KEY" \
     https://api.groq.com/openai/v1/models
   ```

`GET /api/v1/ai/status/` reports the same thing from inside the app,
including whether the configured model is listed for your key.

Free-tier models change over time. Any chat model your key can see in
`/models` can be used by setting `GROQ_MODEL`; the response format below
requires one that supports JSON mode.

### The timeout is deliberately generous

`GROQ_TIMEOUT` (60s) is much larger than the place search timeouts
(5s connect / 30s read). A full multi-day itinerary is a long completion,
and the two budgets are unrelated. In practice a generation takes a few
seconds.

---

## API

### `POST /api/v1/trips/<trip_id>/itinerary/generate/`

Generates an itinerary for one of your trips. Ownership is enforced; a
trip that belongs to somebody else returns `404`.

| Body field | Type | Default | Meaning |
|---|---|---|---|
| `dry_run` | bool | `false` | Generate and return the plan without saving it. |
| `replace` | bool | `false` | Allow an existing itinerary to be replaced. |

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' \
  "http://127.0.0.1:8000/api/v1/trips/<trip_id>/itinerary/generate/"
```

Response:

```json
{
  "success": true,
  "message": "Itinerary generated successfully. Nothing was saved.",
  "data": {
    "itinerary_id": null,
    "persisted": false,
    "plan": {
      "title": "Bengaluru Getaway",
      "description": "A couple of days in the city.",
      "days": [
        {
          "date": "2026-11-01",
          "items": [
            {
              "title": "Visit Cubbon Park",
              "description": "A green park.",
              "start_time": "09:00",
              "end_time": "11:00",
              "activity_type": "attraction",
              "place": {
                "source_id": "node/12345",
                "name": "Cubbon Park",
                "latitude": 12.9763,
                "longitude": 77.6033,
                "address": "MG Road, Bengaluru"
              }
            }
          ]
        }
      ]
    }
  }
}
```

### `GET /api/v1/ai/status/`

Reports the configured provider and whether the key and model are
actually usable. Useful while setting things up.

---

## How a plan is generated

```text
  trip + preferences
          │
          ▼
  DestinationService.resolve()   ──►  a search area
          │
          ▼
  PlacesService.search_places()  ──►  the places we may use
          │
          ▼
  PromptService.build_prompt()    ──►  the prompt
          │
          ▼
  GroqClient.generate()          ──►  raw model output
          │
          ▼
  validate_plan()                 ──►  a validated plan
          │
          ▼
  persist_plan()                  ──►  Itinerary + ItineraryItem
```

The AI layer never makes its own external place requests. It uses the
integrations app, so there is exactly one code path to the places
provider.

---

## What the model is allowed to decide

This is the important part. A language model will happily invent a
restaurant that does not exist, a date outside the trip, or a time that
makes no sense. The design keeps the model on a short leash:

| The model decides | We decide |
|---|---|
| Which places to visit | The places it may choose from |
| The order of activities | The dates of every day |
| The activity titles and descriptions | Every coordinate and address |
| The start and end times | The activity type, when it is invalid |
| — | Whether an activity is kept at all |

### The rules

* **The model never chooses the dates.** It returns days in order, and we
  assign `trip.start_date + index`. A day outside the trip is therefore
  impossible.
* **The model never states a coordinate.** Every activity references a
  place by the stable id we supplied (`node/12345`). The coordinates and
  the address come from our own place data.
* **An activity that references a place we did not offer is dropped.** It
  is not stored with an invented location.
* **Reversed times are swapped**, and unparseable times are discarded
  rather than guessed at.
* **An unknown `activity_type` falls back to `other`.**

### Not destructive by default

If the trip already has an itinerary, generation returns `409 Conflict` and
nothing is changed. The caller has to send `replace: true` to overwrite it.
`dry_run: true` shows the plan without saving anything at all, which gives
the user a confirmation step without needing a "draft itinerary" model.

---

## Errors

| Cause | Status | Meaning |
|---|---|---|
| Unsupported destination | `400` | The trip's destination cannot be searched. |
| Invalid request body | `400` | Standard DRF validation error. |
| Trip already has an itinerary | `409` | Send `replace: true`. |
| Places provider rate limited | `429` | (+ `Retry-After`) |
| Places provider unavailable | `503` | Come back later. |
| Missing or rejected API key | `503` | The message names `GROQ_API_KEY`. |
| Unknown model | `503` | The message names `GROQ_MODEL`. |
| Groq rate limited | `503` | Free-tier quota; try again shortly. |
| Model timed out | `504` | The model was too slow. |
| Model produced no usable plan | `502` | The raw output stays in the server log. |

The raw model output is **never** returned to a client. When generation
fails, the output is written to the server log where it can be diagnosed.

---

## Limitations

* **Quality depends on the model.** The validation guarantees the output
  is *safe*, not that it is *good*.
* **The place pool is small.** Generation uses the same 20-place search
  limit as the places API, so a long trip has a limited palette. The
  model may reuse a place on different days.
* **Generation needs network access and quota.** The free tier is rate
  limited; the app turns that into a readable `503` rather than a broken
  page.
* **No streaming.** The client waits for the whole plan.
* **Trip data leaves the machine.** Unlike a local model, the prompt
  (destination, dates, budget and the list of nearby places) is sent to
  Groq. Do not enable this for data you cannot share with a third party.

---

## Tests

```bash
python manage.py test backend.apps.ai
```

The model and the places provider are always mocked, so the suite needs
no API key and does not touch the public Overpass instance.

### Opt-in live tests

`test_live_groq` talks to the real Groq API. It is skipped unless asked
for:

```powershell
$env:GROQ_LIVE_TEST = "1"
python manage.py test backend.apps.ai.tests.test_live_groq
```

It creates and destroys Django's throwaway test database, so your
development data is never touched. It does spend a small amount of
free-tier quota.
