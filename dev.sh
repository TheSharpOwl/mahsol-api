#!/bin/bash
# Development startup script — SQLite + auto-reload
export DATABASE_URL="sqlite+aiosqlite:///./farming.db"
export DATABASE_URL_SYNC="sqlite:///./farming.db"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
