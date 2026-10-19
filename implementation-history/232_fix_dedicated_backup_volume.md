# Prompt 232 - Persist DB backups in a dedicated external volume

## Objective

Scheduled PostgreSQL backups currently fail in Docker (`docker` CLI is absent
inside the worker container) and, even if they ran, the writer service has no
persistent backup mount. Give backups their own dedicated external Docker
volume that survives `docker compose down -v` / `terraform destroy`, make the
worker dump directly with `pg_dump`, and mount the volume into both the writer
(background) and reader (backend).

## Current State

- `apps/backend/shared/infrastructure/database/backup_service.py:43-55` always
  shells out to `docker exec <DB_BACKUP_CONTAINER> pg_dump`; inside the
  `background` container this fails with
  `[Errno 2] No such file or directory: 'docker'` (verified in worker logs).
- `docker-compose.yml:57` mounts `jobsearch-backups` into **backend** only;
  the `background` service (line 59) that runs `periodic_db_backup` has no
  mount, and the volume is not external (line 107).
- `Dockerfile.background` has no `postgresql-client`, so `pg_dump` is missing.
- `Dockerfile:15-22` still installs a cron job that runs `backup.sh`, whose
  rotation (`ls -tp | tail -n +4`) deletes any file beyond the newest three —
  including the scheduler's `.dump` files. `backup.sh` is unused elsewhere.
- `terraform/main.tf` mounts only the opencode binary into backend/background;
  no backup volume exists in the Terraform stack.
- `.env:35` points `DB_BACKUP_CONTAINER` at `job-search-postgres-1`, but the
  actual container is `job-search-postgres`.
- Only stale host files exist in `backups/` (Sep 3); nothing is being written.

## Changes

1. `apps/backend/shared/infrastructure/database/backup_service.py`
   - Prefer a local `pg_dump` when available (`shutil.which`), connecting from
     `DATABASE_URL` host/port/user/db with `PGPASSWORD` in the child env.
   - Keep `docker exec` as the host-dev fallback.
   - Wrap `OSError` (missing binary/CLI) in a `RuntimeError` and never leave a
     partial/empty dump file behind.
2. `Dockerfile.background`
   - Install `postgresql-client` so the worker can run `pg_dump`.
3. `Dockerfile`
   - Drop the cron backup install and the `backup.sh` chmod; delete
     `apps/backend/scripts/backup.sh` (superseded by `periodic_db_backup`).
4. `docker-compose.yml`
   - Mark `jobsearch-backups` **external**.
   - Mount it at `/app/backups` in `background` as well as `backend`.
   - Set `DB_BACKUP_DIR=/app/backups` on both services.
5. `terraform/main.tf` + `variables.tf` + `outputs.tf`
   - Add `backup_volume_name` (default `jobsearch-backups`).
   - Mount it at `/app/backups` in `backend` and `background`; set
     `DB_BACKUP_DIR=/app/backups`.
   - Output the volume name and its external persistence.
6. `apps/start.py`
   - Add an idempotent `docker volume create jobsearch-backups` bootstrap,
     called by `start docker up` and `start terraform up` before the stack
     starts (external volumes are not created by Compose/Terraform).
7. `.env`
   - Fix `DB_BACKUP_CONTAINER=job-search-postgres`.
8. Docs: `docs/queue/processing/taskiq-processing.md`, `terraform/README.md`,
   `README.md` — document the volume, write/read mounts, how to inspect and
   restore, and that only `docker volume rm jobsearch-backups` deletes it.

## Testing Requirements

- `apps/backend/tests/shared/infrastructure/database/test_backup_service.py`:
  update the command test for both modes (local `pg_dump` + `docker exec`
  fallback), `PGPASSWORD` propagation, missing-binary `RuntimeError`, and
  empty-dump cleanup.
- Run `./scripts/docker-test.sh backend` (rule 18 — Docker only).
- Manual check on the Docker stack: `docker volume ls | grep jobsearch-backups`,
  `docker exec job-search-background ls -lh /app/backups`, and a forced
  `run_db_backup()`/scheduler tick showing a new `.dump`.

## Constraints

- Respect AGENTS.md rules 1, 11, 15, 18.
- No database or migration changes; no cross-context imports.
- The backup volume must never be removed by Compose or Terraform teardown.
