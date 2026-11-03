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

### Future Enhancements

* Flight Recommendations
* Hotel Recommendations
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

## Phase 5 (expenses and notifications implemented)

* Expense Tracker
* Notifications
* Flight & Hotel Recommendations (not started; live prices need a paid API)

## Phase 6 (performance and CI implemented)

* Performance Optimization
* CI/CD
* Docker
* Deployment

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
| `backend`  | Python 3.13 + PostgreSQL 17: `check`, `makemigrations --check`, `migrate`, `test --noinput` |
| `frontend` | Node.js 22: `npm ci`, `npm run lint`, `npm run build`                      |

The workflow starts a disposable PostgreSQL service and supplies test-only
`DB_*`, JWT lifetime and CORS values as job environment variables, so no
repository secrets are required. Pushing to `develop` produces the badge shown
at the top of this README.

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
