#!/bin/bash
# Production startup script for Farming Assistant API
# - Sets SQLite defaults if no DATABASE_URL is provided
# - Uses multiple workers in production (no --reload)
# - Run with: bash start.sh

export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./farming.db}"
export DATABASE_URL_SYNC="${DATABASE_URL_SYNC:-sqlite:///./farming.db}"
export SECRET_KEY="${SECRET_KEY:-change-me-in-production}"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 4
