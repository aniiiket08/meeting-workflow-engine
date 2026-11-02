#!/bin/sh
# Meeting Organizer Agent - Backend container entrypoint
# Applies database migrations, seeds baseline data, then serves the API.
set -e

cd /app

echo "[entrypoint] applying database migrations..."
migration_started_at=$(date +%s)
alembic upgrade head
echo "[entrypoint] database migrations completed in $(( $(date +%s) - migration_started_at ))s"

echo "[entrypoint] seeding baseline data..."
seed_started_at=$(date +%s)
python -m app.db.seed
echo "[entrypoint] baseline seeding completed in $(( $(date +%s) - seed_started_at ))s"

echo "[entrypoint] starting uvicorn on ${HOST:-0.0.0.0}:${PORT:-8000}"
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
