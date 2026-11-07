# 🌍 AI Travel Planner

[![CI](https://github.com/patilnagesh03/ai-travel-planner/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/patilnagesh03/ai-travel-planner/actions/workflows/ci.yml)

An AI-powered travel planning application that helps users create personalized travel itineraries based on their destination, budget, travel dates, and interests.

The application leverages Artificial Intelligence along with external services such as weather, maps, and currency exchange to provide a complete travel planning experience.

---

## 🚀 Features

### Authentication

* User Registration
* User Login
* JWT Authentication
* User Profile Management

### Trip Management

* Create a New Trip
* View All Trips
* Update Trip Details
* Delete Trips
* Save Travel Preferences

### AI Itinerary Generator

* Personalized Day-wise Itinerary
* Budget-based Recommendations
* Interest-based Suggestions
* Travel Tips
* Generated locally with Ollama (no API key, no cost, no data leaves the machine)
* See `backend/apps/ai/README.md`

### Travel Information (implemented)

* Daily weather forecast for the trip destination and dates (Open-Meteo)
* Currency conversion using ECB reference rates (Frankfurter)
* Nearby places from OpenStreetMap via the Overpass API
* Interactive destination and itinerary map (Leaflet + OpenStreetMap tiles)
* See `backend/apps/integrations/README.md` for endpoints and limitations

### Place Discovery (implemented)

* Search places by destination name (curated India-first city list)
* Search places by latitude / longitude, as an override
* Normalized place data from OpenStreetMap via the Overpass API
* Category filtering, result limits and rate-limit aware error handling

### Expenses and Notifications (implemented)

* Record what was actually spent on a trip: title, category, amount, date, notes
* Amounts are stored in the trip's own currency, so totals never mix rates
* Budget-versus-actual summary with remaining budget and per-category totals
* In-app notifications for budget overruns, trips starting within a week and
  recently ended trips
* Read, mark-all-read and dismiss, with an unread badge in the header

### Flights and Accommodation (implemented)

* Deterministic Google Flights and Kayak deep links built from the trip's
  origin, destination and dates
* Optional departure city on a trip; the flight endpoint explains how to add
  one instead of guessing
* Accommodation around the destination from the existing OpenStreetMap /
  Overpass pipeline
* Hotels, guest houses, hostels and apartments ordered by distance from the
  city centre
* A Booking.com search link for live prices. This app does not fetch or store
  fares or availability; the provider shows those.

### Future Enhancements

* PDF Itinerary Export
* Email Notifications
* Collaborative Trip Planning
* AI Chat Assistant

---

# 🛠 Tech Stack

## Frontend

* React
* React Router
* Axios
* Tailwind CSS

## Backend

* Django
* Django REST Framework
* JWT Authentication
* Waitress (cross-platform WSGI server)

## Database

* PostgreSQL

## AI

* Ollama (Local LLM)
* OpenAI (Optional)
## External APIs

* Open-Meteo — implemented, weather forecast, no key
* Frankfurter (European Central Bank rates) — implemented, no key
* OpenStreetMap tiles — implemented, map rendering
* OpenStreetMap (Overpass API) — implemented, see `backend/apps/integrations/README.md`
* Geocoding API — not used; destinations come from a curated city list
* Places API — not used; places come from OpenStreetMap

## Development Tools

* VS Code
* Postman / Thunder Client
* Git
* GitHub

---

# 📂 Project Structure

```text
backend/
│
├── config/
│   ├── settings/
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│
├── apps/
│   ├── accounts/
│   ├── trips/
│   ├── itinerary/
│   ├── expenses/            # trip expenses and budget summaries
│   ├── notifications/       # in-app reminders and alerts
│   ├── integrations/        # OpenStreetMap / Overpass places
│   ├── ai/                  # Ollama itinerary generation
│   ├── external_services/
│   └── common/
│
├── requirements/
├── media/
├── static/
├── logs/
│
├── manage.py
├── .env
├── .env.example
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone <repository-url>
```

```bash
cd ai-travel-planner
```

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements/base.txt
```

---

## 4. Configure environment variables

Create a `.env` file using `.env.example`.

---

## 5. Run migrations

```bash
python manage.py makemigrations
```

```bash
python manage.py migrate
```

---

## 6. Start the development server

```bash
python manage.py runserver
```

The backend will be available at:

```
http://127.0.0.1:8000/
```

---

# 📌 Development Roadmap

## Phase 1

* Project Setup
* Authentication
* PostgreSQL Configuration
* User Profile

## Phase 2

* Trip Management
* CRUD APIs
* Dashboard

## Phase 3

* AI Itinerary Generator
* Prompt Engineering
* Save Generated Plans

## Phase 4 (implemented)

* Weather Integration
* Currency Conversion
* Maps Integration

## Phase 5 (implemented)

* Expense Tracker
* Notifications
* Flight & Hotel Recommendations (deterministic search links and
  OpenStreetMap accommodation; live prices open on the provider's site)

## Phase 6 (performance, CI and deployment readiness implemented)

* Performance Optimization
* CI/CD
* Deployment readiness
* Docker
* Live deployment (not started; needs a hosting account)

---

# 🔒 Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill it in. The project
reads configuration with `python-decouple`, so nothing has to be exported
by hand.

## Required

* `SECRET_KEY` — **required when `DEBUG=False`.** The project refuses to
  start without it, and rejects placeholder or `django-insecure-` values.
  Generate one with:
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
* `DB_NAME`
* `DB_USER`
* `DB_PASSWORD`
* `DB_HOST`
* `DB_PORT`

## Common

* `DEBUG` — defaults to `False`; set `True` for local development.
* `ALLOWED_HOSTS` — comma separated. Required when `DEBUG=False`.
* `CORS_ALLOWED_ORIGINS` — comma separated browser origins allowed to call
  the API (no wildcard). Falls back to `FRONTEND_URL`.
* `FRONTEND_URL` — the frontend origin, used for CORS when
  `CORS_ALLOWED_ORIGINS` is unset.
* `ACCESS_TOKEN_LIFETIME`, `REFRESH_TOKEN_LIFETIME`

## Integrations and AI

* `OVERPASS_*`, `MAX_PLACES_PER_SEARCH`, `INTEGRATIONS_USER_AGENT`
* `AI_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`,
  `OLLAMA_TEMPERATURE`

`backend/.env` is ignored by git; only `backend/.env.example` is committed.

---

# 💸 Expenses and Notifications

## Expenses

| Method   | Path                                       | Purpose                          |
| -------- | ------------------------------------------ | -------------------------------- |
| `GET`    | `/api/v1/trips/<trip_id>/expenses/`        | List expenses **and** the summary |
| `POST`   | `/api/v1/trips/<trip_id>/expenses/`        | Record an expense                |
| `PATCH`  | `/api/v1/trips/<trip_id>/expenses/<id>/`   | Update an expense                |
| `DELETE` | `/api/v1/trips/<trip_id>/expenses/<id>/`   | Delete an expense                |
| `GET`    | `/api/v1/trips/<trip_id>/expenses/summary/`| Summary only                     |

`GET .../expenses/` returns `{expenses, summary}` in one envelope so a list and
its totals can never disagree. `?category=food` filters the list, while the
summary stays trip-wide. Categories are `transport`, `stay`, `food`,
`activities`, `shopping` and `other`; an unknown one is a `400`.

Expenses use the trip's currency and budget — there is no per-expense currency,
so a summary never has to combine exchange rates. `remaining` is allowed to be
negative and `over_budget` is explicit; an over-budget trip is not clamped to
zero.

## Notifications

| Method   | Path                                          | Purpose                     |
| -------- | --------------------------------------------- | --------------------------- |
| `GET`    | `/api/v1/notifications/?unread=true`          | List notifications          |
| `GET`    | `/api/v1/notifications/unread-count/`         | Unread badge count          |
| `POST`   | `/api/v1/notifications/<id>/read/`            | Mark one as read            |
| `POST`   | `/api/v1/notifications/read-all/`             | Mark every unread item read |
| `DELETE` | `/api/v1/notifications/<id>/`                 | Dismiss one                 |

Notifications are **derived from current data**, not pushed by a worker.
`NotificationService.sync_for_user()` runs when the list or unread count is
requested, and after every expense mutation. It applies three rules:

* **Budget exceeded** — spending is strictly greater than the trip budget.
* **Trip starting soon** — the trip starts within 7 days (including today).
* **Trip ended** — the trip ended 1–30 days ago.

Each message carries a `dedupe_key` that encodes the state it describes (for
example the budget or the start date) with a unique constraint on
`(user, dedupe_key)`. Repeated syncs insert nothing, and a change to the
underlying state (a new budget, a moved start date) produces exactly one new
message. Marking as read is idempotent; "read all" only touches unread rows;
dismissing deletes the row. The list is capped at the 50 newest items.

Sync reads the user's existing dedupe keys in one query and only inserts keys
that are genuinely new. A repeat sync therefore runs three queries — spending,
existing keys, trips — no matter how many trips the user has, which matters
because the UI polls the unread count every minute.

---

# 📚 API Documentation

API documentation will be available after implementation.

* Swagger UI
* ReDoc

---

# 🧪 Testing

Future testing stack:

* Pytest
* Django Test Framework
* Coverage Reports

---

# 🔁 Continuous Integration

`.github/workflows/ci.yml` runs on pushes to `main` and `develop`, on every
pull request and on manual dispatch.

| Job        | What it does                                                              |
| ---------- | ------------------------------------------------------------------------- |
| `backend`  | Python 3.13 + PostgreSQL 17: `check`, `check --deploy`, `makemigrations --check`, `migrate`, `test --noinput` |
| `frontend` | Node.js 22: `npm ci`, `npm run lint`, `npm run build`                      |

The workflow starts a disposable PostgreSQL service and supplies test-only
`DB_*`, JWT lifetime and CORS values as job environment variables, so no
repository secrets are required. The deployment check step temporarily sets
`DEBUG=False` and a long test key, which is how the production security
defaults are exercised on every run. Pushing to `develop` produces the badge
shown at the top of this README.

---

# 🚀 Deployment

The backend is a standard Django WSGI application and the frontend is a static
SPA build. No container runtime is required.

## 1. Build the frontend

```bash
cd frontend
npm ci
VITE_API_BASE_URL=https://api.example.com npm run build
```

`VITE_API_BASE_URL` is compiled into the bundle, so it must be set before
`npm run build`. Serve `frontend/dist/` from a static host or the reverse proxy
with an SPA fallback: unknown paths return `index.html`, while hashed files
under `/assets/` can be cached indefinitely.

## 2. Prepare the backend

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy
```

`collectstatic` writes to `backend/staticfiles/`. Production Django does not
serve static or media files: point the reverse proxy (or a storage backend) at
`backend/staticfiles/` for `/static/` and `backend/media/` for `/media/`.

## 3. Run the application server

Waitress is included for a cross-platform WSGI server:

```bash
waitress-serve --listen=0.0.0.0:8000 backend.wsgi:application
```

On Linux, gunicorn is an equally good choice:

```bash
pip install gunicorn
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
```

## 4. Health checks

`GET /health` (or `/health/`) answers:

```json
{"status": "ok", "database": "up"}
```

with status `200` when the database responds to `SELECT 1`, and `503` with
`{"status": "unavailable", "database": "down"}` when it does not. The endpoint
is unauthenticated and never exposes exception details, so it is safe for
platform liveness and readiness probes.

## 5. Production environment

Set at least:

* `DEBUG=False`
* `SECRET_KEY` — a real key of 50+ characters
* `ALLOWED_HOSTS` — the public hostnames
* `CORS_ALLOWED_ORIGINS` — the frontend origin(s)
* `DB_*` — the managed database connection

With `DEBUG=False`, HTTPS redirect, secure cookies and one year of HSTS are
enabled by default. When TLS terminates at a proxy, also set
`TRUST_PROXY_HEADERS=True` so Django trusts `X-Forwarded-Proto`; leave it off
for a directly reachable server. `CSRF_TRUSTED_ORIGINS` defaults to the CORS
origins.

## 6. Checklist before the first deploy

- [ ] `python manage.py check --deploy` reports no issues
- [ ] `python manage.py migrate --noinput` succeeds against the production DB
- [ ] `collectstatic` succeeds and the proxy serves `/static/` and `/media/`
- [ ] `DEBUG=False`, a real `SECRET_KEY`, and the production `ALLOWED_HOSTS`
- [ ] The frontend was built with the production `VITE_API_BASE_URL`
- [ ] `/health` returns `200` through the public hostname
- [ ] HTTPS works end to end before the first production start; lower
      `SECURE_HSTS_SECONDS` during rollout if one year is too aggressive

---

# 🤝 Contributing

Contributions, feature requests, and suggestions are welcome.

Please create a new branch before making changes and submit a pull request after testing.

---

# 📄 License

This project is intended for learning and portfolio purposes.

---

# 👨‍💻 Author

**Nagesh Patil**

Built as a production-style portfolio project to demonstrate Django backend development, REST APIs, PostgreSQL integration, AI integration, and modern software engineering practices.
