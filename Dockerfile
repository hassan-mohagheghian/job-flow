FROM python:3.14-slim AS base

WORKDIR /app

# ── Dependency layer (cached when pyproject.toml/uv.lock unchanged) ──────
COPY pyproject.toml uv.lock alembic.ini ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

# ── Application layer (only invalidated when app code changes) ───────────
COPY apps/ ./apps/

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "apps.backend.entrypoints.api:app", "--host", "0.0.0.0", "--port", "5000"]
