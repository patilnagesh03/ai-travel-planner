# AI App

AI-assisted itinerary generation.

The provider is **Ollama**, which runs the model locally. There is no API
key, no cost, and no trip data leaving the machine.

---

## Layout

```text
backend/apps/ai/
├── config.py
├── clients/
│   ├── ollama_client.py        # HTTP transport for the Ollama server
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
| `AI_PROVIDER` | `ollama` | Which provider to use. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where the Ollama server is. |
| `OLLAMA_MODEL` | `llama3.1` | The model to use. |
| `OLLAMA_TIMEOUT` | `120` | Seconds allowed for one generation. |
| `OLLAMA_TEMPERATURE` | `0.4` | Lower is more predictable. |

### Setting up Ollama

```bash
# Install Ollama, then:
ollama serve
ollama pull llama3.1
```

Check that the model is present:

```bash
curl http://localhost:11434/api/tags
```

`GET /api/v1/ai/status/` reports the same thing from inside the app.

### The timeout is deliberately long

`OLLAMA_TIMEOUT` (120s) is much larger than the place search timeouts
(5s connect / 30s read). Asking a local model to plan a multi-day trip
takes far longer than asking Overpass for a list of nearby places. The two
budgets are unrelated and should not be tuned together.

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

Reports the configured provider and whether the model is actually
available. Useful while setting things up.

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
  OllamaClient.generate()        ──►  raw model output
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
| Model not pulled | `503` | The message says how to fix it. |
| Model timed out | `504` | The model was too slow. |
| Model produced no usable plan | `502` | The raw output stays in the server log. |

The raw model output is **never** returned to a client. When generation
fails, the output is written to the server log where it can be diagnosed.

---

## Limitations

* **Quality depends on the model.** A small local model will produce
  plainer itineraries than a large one. The validation guarantees the
  output is *safe*, not that it is *good*.
* **The place pool is small.** Generation uses the same 20-place search
  limit as the places API, so a long trip has a limited palette. The
  model may reuse a place on different days.
* **A local model can be slow.** On modest hardware a generation can take
  a minute. That is why the timeout is generous and the status is `504`
  rather than `500`.
* **No streaming.** The client waits for the whole plan.
* **Ollama must be running.** The app cannot start it for you.

---

## Tests

```bash
python manage.py test backend.apps.ai
```

The model and the places provider are always mocked, so the suite does
not need Ollama running and does not touch the public Overpass instance.

### Opt-in live tests

Two tests talk to a real Ollama server. They are skipped unless asked for:

```bash
$env:OLLAMA_LIVE_TEST = "1"
python manage.py test backend.apps.ai.tests.test_live_ollama
```

They create and destroy Django's throwaway `test_travel_planner_db`, so
your development data is never touched.

### Live verification results

Verified end to end against a real Ollama server at the configured
`OLLAMA_BASE_URL`, using a real 6-day trip and real Overpass places:

* the configured model was present and reachable;
* 6 days / 30 activities were generated;
* every date fell inside the trip window;
* every activity resolved to a real place with coordinates;
* an invented `node/999999999999` was dropped rather than persisted.

Models verified: `qwen2.5:0.5b` and `llama3.2:1b`.

**`llama3.1` (the default) could not be verified here.** Pulling the 4.7 GB
weights from `registry.ollama.ai` repeatedly failed: the 16-part download
stalled with connection resets, and a single resumable stream did no
better. This is a **network limitation of the machine, not a defect in the
app** — the generation path is model-agnostic and was verified with two
real models above. On a normal connection, `ollama pull llama3.1` and
rerunning the live test is all that is needed to close it.
