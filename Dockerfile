FROM python:3.14-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y cron postgresql-client && rm -rf /var/lib/apt/lists/*

# ── Dependency layer (cached when pyproject.toml/uv.lock unchanged) ──────
COPY pyproject.toml uv.lock alembic.ini ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

# ── Application layer (only invalidated when app code changes) ───────────
COPY apps/ ./apps/

# Make the backup script executable
RUN chmod +x ./apps/backend/scripts/backup.sh

# Set up cron job to run the backup script every 30 minutes
RUN touch /var/log/backup.log && chmod 644 /var/log/backup.log && \
    echo "*/30 * * * * root /app/apps/backend/scripts/backup.sh >> /var/log/backup.log 2>&1" > /etc/cron.d/db-backup && \
    chmod 0644 /etc/cron.d/db-backup && \
    crontab /etc/cron.d/db-backup

EXPOSE 5000

CMD cron -b && uv run uvicorn apps.backend.entrypoints.api:app --host 0.0.0.0 --port 5000