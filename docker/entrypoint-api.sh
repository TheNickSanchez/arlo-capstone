#!/usr/bin/env bash
# API container entrypoint (SAD §4; delivery-workflow.mdc "migrations run cleanly
# on startup"). Runs Alembic against the sync `psycopg` driver, then execs
# uvicorn as PID 1 so container signals still reach the app process.
set -euo pipefail

cd /app

echo "[entrypoint] running Alembic migrations..."
alembic -c backend/alembic.ini upgrade head

echo "[entrypoint] starting API server..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
