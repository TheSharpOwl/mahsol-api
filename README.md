# Farming Assistant API

An AI-powered backend service for a farming assistant mobile application. Built with FastAPI and MySQL, this service helps farmers diagnose crop diseases, interact with an AI chatbot, and receive daily reports based on weather and land data.

---

## Tech Stack

- **FastAPI** — async Python web framework
- **MySQL** — primary database via SQLAlchemy ORM (async)
- **WebSockets** — real-time chat
- **Celery + Redis** — background jobs and daily scheduled tasks
- **Pydantic** — schema validation
- **Docker** — containerized deployment

---

## Project Structure

```
app/
├── main.py                    # FastAPI app entrypoint
├── core/
│   ├── config.py              # Settings (loaded from .env)
│   └── security.py            # JWT + password hashing
├── models/
│   ├── user.py                # User model
│   ├── land_info.py           # LandInfo model
│   ├── conversation.py        # Conversation model
│   ├── message.py             # Message model (indexed on message_type)
│   └── report.py              # Report model
├── schemas/
│   ├── user.py                # Auth request/response schemas
│   ├── land_info.py           # Land info schemas
│   ├── conversation.py        # Chat/conversation schemas
│   └── report.py              # Report schemas
├── api/routes/
│   ├── auth.py                # POST /auth/signup, POST /auth/login
│   ├── land_info.py           # POST /land-info, GET /land-info/me
│   ├── conversations.py       # GET/POST /conversations
│   ├── reports.py             # GET /reports, GET /reports/latest
│   └── chat.py                # WebSocket /ws/chat/{conversation_id}
├── services/
│   ├── ai_service.py          # AI chat + report generation (OpenAI or mocked)
│   └── weather_service.py     # OpenWeatherMap (or mocked)
├── db/
│   ├── base.py                # SQLAlchemy declarative base
│   └── session.py             # Async engine + session factory
└── workers/
    ├── celery.py              # Celery app + Beat schedule
    └── tasks.py               # Daily report generation task
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Application
DEBUG=false

# Database (MySQL)
DATABASE_URL=mysql+asyncmy://farmer:farmerpass@db:3306/farming_db
DATABASE_URL_SYNC=mysql+pymysql://farmer:farmerpass@db:3306/farming_db

# Security — MUST change in production
SECRET_KEY=your-super-secret-key-change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# External APIs (optional — app works with mock data if not set)
OPENWEATHER_API_KEY=your_openweathermap_api_key
OPENAI_API_KEY=your_openai_api_key
```

> **Note:** If `OPENWEATHER_API_KEY` or `OPENAI_API_KEY` are not set, the app returns realistic mock data automatically — perfect for development.

---

## Running with Docker (Recommended)

This is the easiest way to run all services (API, MySQL, Redis, Celery worker, Celery Beat, Flower).

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env with your secrets

# 2. Start all services
docker compose up --build

# 3. The API is now running at:
#    http://localhost:8000
#    Interactive docs: http://localhost:8000/docs
#    Flower (task monitor): http://localhost:5555
```

To stop:
```bash
docker compose down
```

To stop and remove all data (including the MySQL volume):
```bash
docker compose down -v
```

---

## Running Locally (without Docker)

### Prerequisites

- Python 3.12+
- MySQL 8.0+
- Redis 7+

### Setup

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment
cp .env.example .env
# Edit DATABASE_URL and DATABASE_URL_SYNC to point to your local MySQL
# e.g.: mysql+asyncmy://user:pass@localhost:3306/farming_db

# 4. Create the MySQL database
mysql -u root -p -e "CREATE DATABASE farming_db; CREATE USER 'farmer'@'localhost' IDENTIFIED BY 'farmerpass'; GRANT ALL ON farming_db.* TO 'farmer'@'localhost';"
```

### Run the FastAPI Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The app auto-creates all database tables on startup.

API docs available at: `http://localhost:8000/docs`

### Run Celery Worker

In a separate terminal:

```bash
celery -A app.workers.celery.celery_app worker --loglevel=info
```

### Run Celery Beat (scheduler)

In another terminal:

```bash
celery -A app.workers.celery.celery_app beat --loglevel=info
```

Beat runs the daily report task every day at **06:00 UTC**.

### Run Flower (optional task monitor)

```bash
celery -A app.workers.celery.celery_app flower --port=5555
```

Access at: `http://localhost:5555`

---

## API Reference

### Authentication

#### POST `/auth/signup`
Register a new farmer or expert account.

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Farmer",
    "email": "john@farm.com",
    "password": "securepassword123",
    "role": "farmer"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "John Farmer",
    "email": "john@farm.com",
    "role": "farmer",
    "created_at": "2025-01-01T06:00:00Z"
  }
}
```

#### POST `/auth/login`
Login and receive a JWT token.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john@farm.com", "password": "securepassword123"}'
```

---

### Land Info

All endpoints require `Authorization: Bearer <token>` header.

#### POST `/land-info`
Create or update land info (one record per user).

```bash
curl -X POST http://localhost:8000/land-info \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 37.7749,
    "longitude": -122.4194,
    "soil_type": "loamy",
    "crop_type": "tomatoes",
    "additional_notes": "Field near the river"
  }'
```

Response includes current weather data for the location.

#### GET `/land-info/me`
Get your land info with live weather data.

```bash
curl http://localhost:8000/land-info/me \
  -H "Authorization: Bearer <token>"
```

---

### Conversations & Chat

#### POST `/conversations`
Start a new chat conversation.

```bash
curl -X POST http://localhost:8000/conversations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### GET `/conversations`
List all your conversations with messages.

```bash
curl http://localhost:8000/conversations \
  -H "Authorization: Bearer <token>"
```

#### WebSocket `/ws/chat/{conversation_id}?token=<jwt>`
Connect for real-time AI chat.

```javascript
// JavaScript example
const token = "your_jwt_token";
const conversationId = "your_conversation_id";
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}?token=${token}`);

ws.onopen = () => {
  // Send a text message
  ws.send(JSON.stringify({
    message_type: "text",
    content: "My tomato plants have yellow spots, what could it be?"
  }));

  // Send an image URL
  ws.send(JSON.stringify({
    message_type: "image",
    content: "https://example.com/crop-photo.jpg"
  }));
};

ws.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);
  console.log(`${data.sender_type}: ${data.content}`);
};
```

---

### Reports

#### GET `/reports`
Get all your daily reports.

```bash
curl http://localhost:8000/reports \
  -H "Authorization: Bearer <token>"
```

#### GET `/reports/latest`
Get the most recent report.

```bash
curl http://localhost:8000/reports/latest \
  -H "Authorization: Bearer <token>"
```

---

## Daily Report System

The Celery Beat scheduler runs **every day at 06:00 UTC** and automatically:

1. Queries all farmers who have land info registered
2. Fetches live weather data for each farmer's location
3. Sends the land + weather data to AI for analysis
4. Generates a `warning` (risk alert) and `report_text` (recommendations)
5. Saves the report to the database
6. Logs a notification (extend `_notify_farmer` in `tasks.py` to send push notifications, emails, etc.)

---

## Interactive API Documentation

FastAPI auto-generates interactive docs:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Health Check

```bash
curl http://localhost:8000/healthz
# {"status": "ok", "service": "Farming Assistant API"}
```
