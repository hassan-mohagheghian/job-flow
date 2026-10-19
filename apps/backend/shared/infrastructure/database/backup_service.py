"""Database backup service — PostgreSQL backup + retention pruning.

Backups are produced with ``pg_dump``. Inside Docker the worker ships its own
``pg_dump`` and connects straight to PostgreSQL; on a host without a local
client it falls back to ``docker exec`` against the Postgres container. The
dump is written to ``DB_BACKUP_DIR`` (``/app/backups`` in the Docker stacks,
which is a dedicated persistent volume).

Retention policy: keep only the N most recent backups (default 3) and delete
the rest, so the backup scheduler never fills the volume.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from datetime import datetime

from sqlalchemy.engine import make_url

from shared.infrastructure.config.app_config import (
    DATABASE_URL,
    DB_BACKUP_CONTAINER,
    DB_BACKUP_DIR,
    DB_BACKUP_KEEP_COUNT,
)
from shared.infrastructure.process.logging_config import get_logger

log = get_logger("db.backup")

BACKUP_PREFIX = "jobsearch"
BACKUP_EXT = ".dump"
BACKUP_GLOB = f"{BACKUP_PREFIX}_*.{BACKUP_EXT.lstrip('.')}"


def _database_url():
    return make_url(DATABASE_URL)


def _db_credentials() -> tuple[str, str]:
    url = _database_url()
    return url.username or "postgres", url.database or "postgres"


def _backup_filename(now: datetime) -> str:
    return f"{BACKUP_PREFIX}_{now.strftime('%Y%m%d_%H%M%S')}{BACKUP_EXT}"


def _uses_local_pg_dump() -> bool:
    """True when ``pg_dump`` is installed (Docker worker, or a dev machine)."""
    return shutil.which("pg_dump") is not None


def _dump_command(database: str, username: str) -> list[str]:
    if _uses_local_pg_dump():
        url = _database_url()
        return [
            "pg_dump",
            "--host",
            url.host or "localhost",
            "--port",
            str(url.port or 5432),
            "--username",
            username,
            "--dbname",
            database,
            "--format=custom",
            "--no-owner",
        ]
    # Host-dev fallback: the postgres client lives inside the DB container.
    return [
        "docker",
        "exec",
        DB_BACKUP_CONTAINER,
        "pg_dump",
        "-U",
        username,
        "-d",
        database,
        "--format=custom",
        "--no-owner",
    ]


def _dump_env() -> dict[str, str] | None:
    """Child env with ``PGPASSWORD`` for a local ``pg_dump`` call."""
    if not _uses_local_pg_dump():
        return None
    url = _database_url()
    if not url.password:
        return None
    env = os.environ.copy()
    env["PGPASSWORD"] = url.password
    return env


def create_db_backup() -> str:
    """Create a new PostgreSQL dump and return the backup file path."""
    os.makedirs(DB_BACKUP_DIR, exist_ok=True)
    username, database = _db_credentials()
    backup_path = os.path.join(DB_BACKUP_DIR, _backup_filename(datetime.now()))

    try:
        with open(backup_path, "wb") as fh:
            proc = subprocess.run(
                _dump_command(database, username),
                stdout=fh,
                stderr=subprocess.PIPE,
                check=False,
                env=_dump_env(),
            )
    except OSError as e:
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise RuntimeError(
            f"could not run pg_dump for {database}: {e}"
        ) from e

    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="replace").strip()
        os.remove(backup_path)
        raise RuntimeError(
            f"pg_dump failed (exit {proc.returncode}) for {database}: {stderr}"
        )

    if os.path.getsize(backup_path) == 0:
        os.remove(backup_path)
        raise RuntimeError(f"pg_dump produced an empty dump for {database}")

    log.info("backup.created", path=backup_path)
    return backup_path


def list_backups() -> list[str]:
    """List existing backup files, oldest first."""
    return sorted(glob.glob(os.path.join(DB_BACKUP_DIR, BACKUP_GLOB)))


def prune_old_backups(keep: int = DB_BACKUP_KEEP_COUNT) -> list[str]:
    """Delete backups beyond the N most recent and return the removed paths."""
    backups = list_backups()
    if keep < 0:
        keep = 0
    stale = backups[:-keep] if keep > 0 else backups
    removed: list[str] = []
    for path in stale:
        try:
            os.remove(path)
            removed.append(path)
            log.info("backup.pruned", path=path)
        except OSError as e:  # pragma: no cover - fs error
            log.error("backup.prune_failed", path=path, error=str(e))
    return removed


def run_db_backup() -> dict:
    """Create a backup and enforce retention. Returns a summary dict."""
    backup_path = create_db_backup()
    removed = prune_old_backups(DB_BACKUP_KEEP_COUNT)
    return {
        "created": backup_path,
        "removed": removed,
        "retained": len(list_backups()),
    }
