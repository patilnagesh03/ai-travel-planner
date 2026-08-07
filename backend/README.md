# 🌍 AI Travel Planner

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

### Travel Information

* Weather Forecast
* Currency Conversion
* Nearby Places
* Maps Integration

### Future Enhancements

* Flight Recommendations
* Hotel Recommendations
* Expense Tracking
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

* Weather API
* Currency Exchange API
* OpenStreetMap
* Geocoding API
* Places API

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
│   ├── ai/
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

## Phase 4

* Weather Integration
* Currency Conversion
* Maps Integration

## Phase 5

* Flight & Hotel Recommendations
* Expense Tracker
* Notifications

## Phase 6

* Docker
* CI/CD
* Deployment
* Performance Optimization

---

# 🔒 Environment Variables

Configure the following variables inside the `.env` file:

* `SECRET_KEY`
* `DEBUG`
* `ALLOWED_HOSTS`
* `DB_NAME`
* `DB_USER`
* `DB_PASSWORD`
* `DB_HOST`
* `DB_PORT`
* `WEATHER_API_KEY`
* `CURRENCY_API_KEY`
* `OPENAI_API_KEY`
* `OLLAMA_BASE_URL`

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
