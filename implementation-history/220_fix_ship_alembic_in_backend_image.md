# Prompt 220 - Ship Alembic Files in the Backend Image

## Objective
Make the terraform one-shot alembic container actually run migrations: the backend image must contain `alembic.ini` and `apps/alembic/`, which `.dockerignore` / `Dockerfile` currently exclude (every migration so far had to be applied by hand; the alembic service exits 255).

## Current State
- `Dockerfile:3-14`: `COPY pyproject.toml uv.lock` + `COPY apps/`; never copies root `alembic.ini`.
- `.dockerignore`: excludes `apps/alembic` (and `apps/frontend`).
- In-image check `ls /app/alembic.ini /app/apps/alembic/env.py` → both missing; `uv run alembic upgrade head` in the image fails with `No 'script_location' key found in configuration`; `job-search-alembic` exits 255 on every deploy.

## Changes
1. `Dockerfile`: add `COPY alembic.ini ./` (root config; `script_location = apps/alembic` resolves under `WORKDIR /app`).
2. `.dockerignore`: stop excluding `apps/alembic` (migration scripts must ship; keep `apps/frontend` excluded).
3. Rebuild `job-search-backend:latest`, verify the files exist in the image, run the migration one-shot, verify `opportunity_003` applied, `terraform apply` to reconcile.

## Testing Requirements
- `docker run --rm <image> ls /app/alembic.ini /app/apps/alembic/env.py` succeeds.
- Alembic one-shot exits 0 and stamps the new head; `GET` detail + dismiss endpoints smoke-tested live.
- No pytest/vitest impact (deploy-only files); note in this file that backend/frontend suites were last green at `0355fdd`.

## Constraints
- Respect AGENTS.md rules 11, 14 (migration content itself untouched — only packaging), 18.
- Do not ship `.env`, credentials, or the frontend into the backend image (existing excludes stay).
