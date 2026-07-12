# Mahsol-API

The full backend of mahsol (refreshed)

FastAPI + PostgreSQL, running in Docker.

## Prerequisites

- Docker Desktop (running)
- A `.env` file in the project root (never committed) with:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname?sslmode=verify-full&sslrootcert=system
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<long random value, used to sign JWTs>
```

## Run with Docker (recommended)

```powershell
.\build.ps1          # build image, restart container, follow logs (Ctrl+C to detach)
.\build.ps1 -Silent  # same, but return to the prompt instead of following logs
```

The API is then available at http://localhost:8000 — interactive docs at http://localhost:8000/docs.

Useful commands:

```powershell
docker logs -f mahsol-api   # watch logs
docker rm -f mahsol-api     # stop and remove the container
```

## Run locally (without Docker)

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload
```

## Endpoints

| Method | Path             | Description                                        |
| ------ | ---------------- | -------------------------------------------------- |
| GET    | `/health`        | Health check                                       |
| POST   | `/api/v1/signup` | Create account (email, password, role)             |
| POST   | `/api/v1/signin` | Sign in, returns a bearer token and the role       |
| GET    | `/api/v1/me`     | Current user info (requires `Authorization` header)|

Roles: `pharmacist`, `company`, `farmer`, `admin`.

Authenticated requests send the token from signin as a header:

```
Authorization: Bearer <access_token>
```
