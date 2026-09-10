import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Ensure apps/ and apps/backend/ are on sys.path for imports
_this_file = os.path.abspath(__file__ if '__file__' in dir() else '.')
_app_dir = os.path.dirname(_this_file)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)
_backend_dir = os.path.join(_app_dir, "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import typer
from rich.console import Console
from rich.table import Table

from backend.shared.infrastructure.process.logging_config import setup_logging, get_logger

setup_logging(level='INFO')
log = get_logger('dev-cli')

app = typer.Typer(
    name="start",
    help="Job Search Application — Developer CLI",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Database operations")
docker_app = typer.Typer(help="Docker operations")
terraform_app = typer.Typer(help="Terraform operations")
app.add_typer(db_app, name="db")
app.add_typer(docker_app, name="docker")
app.add_typer(terraform_app, name="terraform")

console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "apps" / "backend"
CLIENT_DIR = REPO_ROOT / "apps" / "frontend"
BACKGROUND_DIR = REPO_ROOT / "apps" / "background"
VENV_DIR = REPO_ROOT / ".venv"
PID_FILE = REPO_ROOT / ".server.pid"
CLIENT_PID_FILE = REPO_ROOT / ".client.pid"
PID_BG_FILE = REPO_ROOT / ".background.pid"
PID_SCHED_FILE = REPO_ROOT / ".scheduler.pid"
PROD_PID_FILE = REPO_ROOT / ".server.prod.pid"
PROD_CLIENT_PID_FILE = REPO_ROOT / ".client.prod.pid"


def read_version() -> str:
    """Read the repo version from the VERSION file at the repository root."""
    version_file = REPO_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


def _load_port_from_env(key: str, default: int) -> int:
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    try:
                        return int(v.strip())
                    except ValueError:
                        pass
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _python_path() -> str:
    venv_python = VENV_DIR / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return "python3"


def _alembic_path() -> str:
    venv_alembic = VENV_DIR / "bin" / "alembic"
    if venv_alembic.exists():
        return str(venv_alembic)
    return "alembic"


def _read_pid(pid_file: Path) -> Optional[int]:
    try:
        return int(pid_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _kill_process(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    import time as _time
    _time.sleep(0.5)
    if _is_process_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _save_pid(pid_file: Path, pid: int):
    pid_file.write_text(str(pid))


def _stop_service(name: str, pid_file: Path):
    pid = _read_pid(pid_file)
    if pid is not None and _is_process_alive(pid):
        console.print(f"[yellow][job-search][/] Stopping {name} (PID: {pid})")
        _kill_process(pid)
    pid_file.unlink(missing_ok=True)


def _kill_by_pattern(pattern: str):
    subprocess.run(["pkill", "-f", pattern], capture_output=True)


def _log(msg: str):
    log.info(msg)
    console.print(f"[blue][job-search][/] {msg}")


def _ok(msg: str):
    log.info(msg)
    console.print(f"[green][job-search][/] {msg}")


def _warn(msg: str):
    log.warning(msg)
    console.print(f"[yellow][job-search][/] {msg}")


def _err(msg: str):
    log.error(msg)
    console.print(f"[red][job-search][/] {msg}")


def _header(msg: str):
    console.print()
    console.print(f"[blue]═══ {msg} ═══[/]")
    console.print()


def _check_tool(name: str, *args: str):
    if not shutil.which(name):
        return False, f"{name} not found"
    try:
        result = subprocess.run([name, *args], capture_output=True, text=True)
        version = result.stdout.strip()
        return True, f"{name} {version}"
    except FileNotFoundError:
        return False, f"{name} not found"


# ── Database helpers ──────────────────────────────────────────────

def _parse_database_url(url: str) -> dict:
    """Parse a DATABASE_URL into components."""
    import re
    url = url.strip()
    # Strip SQLAlchemy dialect suffix for libpq compatibility
    raw_url = re.sub(r'\+psycopg(?=://)', '', url)
    m = re.match(
        r"postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)",
        raw_url,
    )
    if not m:
        raise ValueError(f"Cannot parse DATABASE_URL: {url}")
    return {
        "user": m.group(1),
        "password": m.group(2),
        "host": m.group(3),
        "port": m.group(4) or "5432",
        "database": m.group(5),
        "raw_url": raw_url,
    }


def _ensure_database(target_db: str, source_url: str) -> str:
    """Create the target database if it doesn't exist. Returns the new DATABASE_URL."""
    import psycopg
    components = _parse_database_url(source_url)
    raw_base = components["raw_url"].rsplit("/", 1)[0]
    target_raw_url = raw_base + "/" + target_db
    # Re-add the +psycopg suffix for the SQLAlchemy DATABASE_URL
    target_url = source_url.strip().rsplit("/", 1)[0] + "/" + target_db

    try:
        conn = psycopg.connect(
            host=components["host"],
            port=components["port"],
            user=components["user"],
            password=components["password"],
            dbname="postgres",
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(f'CREATE DATABASE "{target_db}"')
            _ok(f"Created database: {target_db}")
        else:
            _log(f"Database already exists: {target_db}")
        cur.close()
        conn.close()
    except Exception as e:
        _err(f"Failed to create database: {e}")
        raise typer.Exit(code=1)

    return target_url


def _migrate_database(target_url: str):
    """Run Alembic migrations against the target database."""
    alembic = _alembic_path()
    env = os.environ.copy()
    env["DATABASE_URL"] = target_url
    result = subprocess.run(
        [alembic, "upgrade", "head"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result.returncode != 0:
        _err("Alembic migration failed.")
        raise typer.Exit(code=1)
    _ok("Migrations applied to target database.")


def _clone_rules(source_url: str, target_url: str):
    """Clone all rules from the source database to the target database."""
    import psycopg
    import psycopg.rows
    import re

    # Strip +psycopg dialect suffix for libpq connections
    src_raw = re.sub(r'\+psycopg(?=://)', '', source_url.strip())
    tgt_raw = re.sub(r'\+psycopg(?=://)', '', target_url.strip())

    source_conn = psycopg.connect(src_raw)
    source_cur = source_conn.cursor(row_factory=psycopg.rows.dict_row)
    source_cur.execute(
        "SELECT category, rule_type, scope, key, value, description, priority, enabled "
        "FROM shared.rules ORDER BY priority DESC"
    )
    rules = source_cur.fetchall()
    source_cur.close()
    source_conn.close()

    if not rules:
        _log("No rules to clone.")
        return

    target_conn = psycopg.connect(tgt_raw)
    target_conn.autocommit = True
    target_cur = target_conn.cursor()

    for rule in rules:
        target_cur.execute(
            "INSERT INTO shared.rules (category, rule_type, scope, key, value, description, priority, enabled) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (category, key) DO NOTHING",
            (
                rule["category"], rule["rule_type"], rule["scope"], rule["key"],
                rule["value"], rule["description"], rule["priority"], rule["enabled"],
            ),
        )

    target_cur.close()
    target_conn.close()
    _ok(f"Cloned {len(rules)} rules to target database.")


def _prepare_database(db_name: str) -> str:
    """Create target DB, run migrations, clone rules. Returns the new DATABASE_URL."""
    source_url = os.environ.get("DATABASE_URL", "")
    if not source_url:
        _err("DATABASE_URL not set in environment.")
        raise typer.Exit(code=1)

    _header(f"Preparing database: {db_name}")
    target_url = _ensure_database(db_name, source_url)
    _migrate_database(target_url)
    _clone_rules(source_url, target_url)
    return target_url


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        dev()


@app.command()
def dev(
    backend_port: Optional[int] = typer.Option(
        None, "--backend-port", help="Backend port"
    ),
    frontend_port: Optional[int] = typer.Option(
        None, "--frontend-port", help="Frontend port"
    ),
    with_background: bool = typer.Option(
        False, "--background", "-b", help="Also start the background worker + scheduler"
    ),
    db: Optional[str] = typer.Option(
        None, "--db", help="Use a different database (clones rules from default DB)"
    ),
):
    """Start backend + frontend in development mode (hot-reload)"""
    port_be = backend_port or _load_port_from_env("BACKEND_PORT", 5000)
    port_fe = frontend_port or _load_port_from_env("FRONTEND_PORT", 5173)

    db_env_override = {}
    if db:
        target_url = _prepare_database(db)
        db_env_override["DATABASE_URL"] = target_url

    _log("Starting all services (dev mode)...")
    console.print()

    _start_backend(port_be, env_extra=db_env_override)
    import time
    time.sleep(2)
    _start_frontend(port_fe)

    if with_background:
        time.sleep(1)
        _start_background(env_extra=db_env_override)

    console.print()
    _ok("All services started!")
    console.print()
    console.print(f"  Backend:  http://localhost:{port_be}")
    console.print(f"  Frontend: http://localhost:{port_fe}")
    if with_background:
        console.print("  Background: worker + scheduler running")
    console.print()
    console.print("  Press Ctrl+C to stop all services")
    console.print()

    try:
        signal.signal(signal.SIGINT, lambda s, f: (_stop_service("backend", PID_FILE), _stop_service("frontend", CLIENT_PID_FILE), _stop_service("background", PID_BG_FILE), _stop_service("scheduler", PID_SCHED_FILE), _kill_by_pattern("mimo run"), _ok("All processes stopped."), sys.exit(0)))
        signal.pause()
    except KeyboardInterrupt:
        pass

    _stop_service("backend", PID_FILE)
    _stop_service("frontend", CLIENT_PID_FILE)
    if with_background:
        _stop_service("background", PID_BG_FILE)
        _stop_service("scheduler", PID_SCHED_FILE)
    _kill_by_pattern("mimo run")
    _ok("All processes stopped.")


@app.command()
def prod(
    backend_port: Optional[int] = typer.Option(
        None, "--backend-port", help="Backend port"
    ),
    frontend_port: Optional[int] = typer.Option(
        None, "--frontend-port", help="Frontend port"
    ),
    with_background: bool = typer.Option(
        False, "--background", "-b", help="Also start the background worker + scheduler"
    ),
    db: Optional[str] = typer.Option(
        None, "--db", help="Use a different database (clones rules from default DB)"
    ),
):
    """Start backend + frontend in production mode"""
    port_be = backend_port or _load_port_from_env("BACKEND_PORT", 5000)
    port_fe = frontend_port or _load_port_from_env("FRONTEND_PORT", 3000)

    db_env_override = {}
    if db:
        target_url = _prepare_database(db)
        db_env_override["DATABASE_URL"] = target_url

    _log("Starting all services (production mode)...")
    console.print()

    _start_backend_prod(port_be, env_extra=db_env_override)
    import time
    time.sleep(2)
    _start_frontend_prod(port_fe)

    if with_background:
        time.sleep(1)
        _start_background(env_extra=db_env_override)

    console.print()
    _ok("All services started!")
    console.print()
    console.print(f"  Backend:  http://localhost:{port_be}")
    console.print(f"  Frontend: http://localhost:{port_fe}")
    if with_background:
        console.print("  Background: worker + scheduler running")
    console.print()
    console.print("  Press Ctrl+C to stop all services")
    console.print()

    try:
        signal.signal(signal.SIGINT, lambda s, f: (_stop_service("backend", PROD_PID_FILE), _stop_service("frontend", PROD_CLIENT_PID_FILE), _stop_service("background", PID_BG_FILE), _stop_service("scheduler", PID_SCHED_FILE), _kill_by_pattern("mimo run"), _ok("All processes stopped."), sys.exit(0)))
        signal.pause()
    except KeyboardInterrupt:
        pass

    _stop_service("backend", PROD_PID_FILE)
    _stop_service("frontend", PROD_CLIENT_PID_FILE)
    if with_background:
        _stop_service("background", PID_BG_FILE)
        _stop_service("scheduler", PID_SCHED_FILE)
    _kill_by_pattern("mimo run")
    _ok("All processes stopped.")


def _uvicorn_args(port: int) -> list[str]:
    """Build the uvicorn dev-server args with code reload that ignores test files."""
    return [
        "-m", "uvicorn", "apps.backend.entrypoints.api:app",
        "--host", "0.0.0.0", "--port", str(port), "--reload",
        "--reload-exclude", str(SERVER_DIR / "tests"),
        "--reload-exclude", "test_*.py",
        "--reload-exclude", "*_test.py",
        "--timeout-graceful-shutdown", "5",
    ]


def _uvicorn_prod_args(port: int) -> list[str]:
    """Build the uvicorn production args (no reload)."""
    return [
        "-m", "uvicorn", "apps.backend.entrypoints.api:app",
        "--host", "0.0.0.0", "--port", str(port),
        "--workers", "4",
        "--timeout-graceful-shutdown", "5",
    ]


def _start_backend(port: int, env_extra: dict | None = None):
    _log("Starting backend server...")
    python = _python_path()
    _log(f"Using Python: {python}")

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(
        [python, *_uvicorn_args(port)],
        cwd=str(REPO_ROOT),
        env=env,
    )
    _save_pid(PID_FILE, proc.pid)
    _ok(f"Backend started (PID: {proc.pid}) on http://localhost:{port}")


def _start_frontend(port: int):
    _log("Starting frontend dev server...")
    port_str = str(port)
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", port_str],
        cwd=str(CLIENT_DIR),
    )
    _save_pid(CLIENT_PID_FILE, proc.pid)
    _ok(f"Frontend started (PID: {proc.pid}) on http://localhost:{port}")


def _start_backend_prod(port: int, env_extra: dict | None = None):
    _log("Starting backend (production)...")
    python = _python_path()
    _log(f"Using Python: {python}")

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(
        [python, *_uvicorn_prod_args(port)],
        cwd=str(REPO_ROOT),
        env=env,
    )
    _save_pid(PROD_PID_FILE, proc.pid)
    _ok(f"Backend started (PID: {proc.pid}) on http://localhost:{port}")


def _start_frontend_prod(port: int):
    _log("Building frontend for production...")
    build_result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(CLIENT_DIR),
    )
    if build_result.returncode != 0:
        _err("Frontend build failed.")
        raise typer.Exit(code=1)
    _ok("Frontend build complete.")

    _log("Starting frontend (production)...")
    port_str = str(port)
    proc = subprocess.Popen(
        ["npm", "run", "start", "--", "--port", port_str],
        cwd=str(CLIENT_DIR),
    )
    _save_pid(PROD_CLIENT_PID_FILE, proc.pid)
    _ok(f"Frontend started (PID: {proc.pid}) on http://localhost:{port}")


def _background_env() -> dict:
    env = os.environ.copy()
    server_dir = str(REPO_ROOT / "apps" / "backend")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = server_dir + (f":{existing}" if existing else "")
    return env


def _start_background(env_extra: dict | None = None):
    _log("Starting background worker...")
    python = _python_path()
    env = _background_env()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(
        [
            python, "-m", "apps.backend.entrypoints.worker",
        ],
        cwd=str(REPO_ROOT),
        env=env,
    )
    _save_pid(PID_BG_FILE, proc.pid)
    _ok(f"Background worker started (PID: {proc.pid})")
    _start_scheduler(env)


def _start_scheduler(env: dict = None):
    _log("Starting background scheduler...")
    python = _python_path()
    if env is None:
        env = _background_env()
    proc = subprocess.Popen(
        [
            python, "-m", "taskiq", "scheduler",
            "apps.backend.entrypoints.scheduler:create_scheduler",
            "shared.infrastructure.taskiq.tasks",
        ],
        cwd=str(REPO_ROOT),
        env=env,
    )
    _save_pid(PID_SCHED_FILE, proc.pid)
    _ok(f"Background scheduler started (PID: {proc.pid})")


@app.command()
def backend(
    port: Optional[int] = typer.Option(
        None, "--port", help="Backend port"
    ),
):
    """Start only the FastAPI backend"""
    port_val = port or _load_port_from_env("BACKEND_PORT", 5000)

    _log("Starting backend server...")
    python = _python_path()
    _log(f"Using Python: {python}")

    env = os.environ.copy()
    proc = subprocess.Popen(
        [python, *_uvicorn_args(port_val)],
        cwd=str(REPO_ROOT),
        env=env,
    )
    _save_pid(PID_FILE, proc.pid)
    _ok(f"Backend started (PID: {proc.pid}) on http://localhost:{port_val}")

    try:
        signal.pause()
    except KeyboardInterrupt:
        pass

    _log("Shutting down backend...")
    _stop_service("backend", PID_FILE)
    _kill_by_pattern("mimo run")
    _ok("Backend stopped.")


@app.command()
def frontend(
    port: Optional[int] = typer.Option(
        None, "--port", help="Frontend port"
    ),
):
    """Start only the frontend dev server"""
    port_val = port or _load_port_from_env("FRONTEND_PORT", 5173)

    _log("Starting frontend dev server...")
    port_str = str(port_val)
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", port_str],
        cwd=str(CLIENT_DIR),
    )
    _save_pid(CLIENT_PID_FILE, proc.pid)
    _ok(f"Frontend started (PID: {proc.pid}) on http://localhost:{port_val}")

    try:
        signal.pause()
    except KeyboardInterrupt:
        pass

    _log("Shutting down frontend...")
    _stop_service("frontend", CLIENT_PID_FILE)
    _ok("Frontend stopped.")


@app.command()
def theme(
    code: str = typer.Argument(
        "b4ZVZIPi9h", help="Shadcn preset code to apply (default: b4ZVZIPi9h)"
    ),
):
    """Apply a shadcn preset code to the frontend theme"""
    _log(f"Applying shadcn preset ({code})...")
    result = subprocess.run(
        ["npx", "shadcn@latest", "apply", code, "-y"],
        cwd=str(CLIENT_DIR),
    )
    if result.returncode == 0:
        _ok("Preset applied.")
    else:
        _err("Failed to apply preset.")
        raise typer.Exit(code=1)


@app.command()
def background():
    """Start only the background worker + scheduler"""
    _log("Starting background worker...")
    python = _python_path()
    env = _background_env()
    proc = subprocess.Popen(
        [python, "-m", "apps.backend.entrypoints.worker"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    _save_pid(PID_BG_FILE, proc.pid)
    _ok(f"Background worker started (PID: {proc.pid})")
    _start_scheduler(env)

    try:
        signal.pause()
    except KeyboardInterrupt:
        pass

    _log("Shutting down background worker...")
    _stop_service("background", PID_BG_FILE)
    _stop_service("scheduler", PID_SCHED_FILE)
    _ok("Background worker stopped.")


test_app = typer.Typer(help="Run tests")
app.add_typer(test_app, name="test", no_args_is_help=True)


def _run_backend_tests(coverage: bool = False) -> bool:
    python = _python_path()
    _log("Running backend tests...")
    cmd = [python, "-m", "pytest", "apps/backend/tests", "-v", "--tb=short"]
    if coverage:
        cmd += ["--cov=apps/backend", "--cov-report=term-missing"]
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode == 0:
        return True
    _err("Backend tests failed.")
    return False


def _run_frontend_tests(coverage: bool = False) -> bool:
    _log("Running frontend tests...")
    script = "test:coverage" if coverage else "test"
    result = subprocess.run(
        ["npm", "run", script],
        cwd=str(CLIENT_DIR),
    )
    if result.returncode == 0:
        return True
    _err("Frontend tests failed.")
    return False


@test_app.command()
def all(
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Run tests with a coverage report"
    ),
):
    """Run backend + frontend tests"""
    ok = True
    if not _run_backend_tests(coverage):
        ok = False
    if not _run_frontend_tests(coverage):
        ok = False
    if ok:
        _ok("All tests passed.")
    else:
        raise typer.Exit(code=1)


@test_app.command()
def backend(
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Run tests with a coverage report"
    ),
):
    """Run backend tests only"""
    if _run_backend_tests(coverage):
        _ok("Backend tests passed.")
    else:
        raise typer.Exit(code=1)


@test_app.command()
def frontend(
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Run tests with a coverage report"
    ),
):
    """Run frontend tests only"""
    if _run_frontend_tests(coverage):
        _ok("Frontend tests passed.")
    else:
        raise typer.Exit(code=1)


@app.command()
def lint():
    """Run all linters"""
    _log("Running linters...")
    failed = False

    _log("Linting backend (ruff)...")
    python = _python_path()
    ruff = subprocess.run(
        [python, "-m", "ruff", "check", "apps/backend"],
        cwd=str(REPO_ROOT),
    )
    if ruff.returncode != 0:
        _warn("Ruff lint issues found")
        failed = True
    else:
        _ok("Ruff: OK")

    _log("Linting frontend (eslint)...")
    eslint = subprocess.run(
        ["npm", "run", "lint"],
        cwd=str(CLIENT_DIR),
    )
    if eslint.returncode != 0:
        _warn("ESLint issues found")
        failed = True
    else:
        _ok("ESLint: OK")

    if failed:
        raise typer.Exit(code=1)
    _ok("All linters passed.")


@app.command()
def format():
    """Run all formatters"""
    _log("Running formatters...")
    failed = False

    _log("Formatting backend (ruff)...")
    python = _python_path()
    ruff = subprocess.run(
        [python, "-m", "ruff", "format", "apps/backend"],
        cwd=str(REPO_ROOT),
    )
    if ruff.returncode != 0:
        _warn("Ruff format issues")
        failed = True
    else:
        _ok("Ruff format: OK")

    _log("Formatting frontend (prettier)...")
    prettier = subprocess.run(
        ["npm", "run", "format"],
        cwd=str(CLIENT_DIR),
    )
    if prettier.returncode != 0:
        _warn("Prettier format issues")
        failed = True
    else:
        _ok("Prettier: OK")

    if failed:
        raise typer.Exit(code=1)
    _ok("All formatters passed.")


@app.command()
def migrate():
    """Run database migrations"""
    _log("Running database migrations...")
    alembic = _alembic_path()
    env = os.environ.copy()
    result = subprocess.run(
        [alembic, "upgrade", "head"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result.returncode == 0:
        _ok("Migrations applied successfully.")
    else:
        raise typer.Exit(code=1)


@db_app.command()
def up():
    """Run pending migrations up"""
    _log("Running migrations up...")
    alembic = _alembic_path()
    env = os.environ.copy()
    result = subprocess.run(
        [alembic, "upgrade", "head"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result.returncode == 0:
        _ok("Migrations applied.")
    else:
        raise typer.Exit(code=1)


@db_app.command()
def down():
    """Rollback last migration"""
    _log("Rolling back last migration...")
    alembic = _alembic_path()
    env = os.environ.copy()
    result = subprocess.run(
        [alembic, "downgrade", "-1"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    if result.returncode == 0:
        _ok("Migration rolled back.")
    else:
        raise typer.Exit(code=1)


@db_app.command()
def new(name: str = typer.Argument(..., help="Migration name")):
    """Create a new migration"""
    _log(f"Creating migration: {name}")
    alembic = _alembic_path()
    result = subprocess.run(
        [alembic, "revision", "--autogenerate", "-m", name],
        cwd=str(REPO_ROOT),
    )
    if result.returncode == 0:
        _ok(f"Migration '{name}' created.")
    else:
        raise typer.Exit(code=1)


@docker_app.command()
def up(
    services: list[str] = typer.Argument(
        None, help="Specific services to start (e.g., db redis). Starts all if omitted."
    ),
):
    """Start docker containers (optionally specific services)"""
    cmd = ["docker", "compose", "up", "-d"]
    if services:
        cmd.extend(services)
        _log(f"Starting docker services: {', '.join(services)}...")
    else:
        _log("Starting all docker containers...")
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
    )
    if result.returncode == 0:
        if services:
            _ok(f"Docker services started: {', '.join(services)}")
        else:
            _ok("Docker containers started.")
    else:
        raise typer.Exit(code=1)


@docker_app.command()
def down():
    """Stop docker containers"""
    _log("Stopping docker containers...")
    result = subprocess.run(
        ["docker", "compose", "down"],
        cwd=str(REPO_ROOT),
    )
    if result.returncode == 0:
        _ok("Docker containers stopped.")
    else:
        raise typer.Exit(code=1)


@docker_app.command()
def status():
    """Show docker container status"""
    _log("Docker container status:")
    result = subprocess.run(
        ["docker", "compose", "ps"],
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise typer.Exit(code=1)


# ── Terraform commands ────────────────────────────────────────────

TERRAFORM_DIR = REPO_ROOT / "terraform"


def _build_images():
    """Build Docker images for terraform deployment."""
    _header("Building Docker images")

    import concurrent.futures

    def build_backend():
        _log("Building backend image...")
        result = subprocess.run(
            ["docker", "build", "-t", "job-search-backend:latest", "."],
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return False, "backend"
        _ok("Backend image built")
        return True, "backend"

    def build_background():
        _log("Building background image...")
        result = subprocess.run(
            ["docker", "build", "-t", "job-search-background:latest", "-f", "Dockerfile.background", "."],
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return False, "background"
        _ok("Background image built")
        return True, "background"

    def build_frontend():
        _log("Building frontend locally (npm run build)...")
        build_env = os.environ.copy()
        build_env["BACKEND_URL"] = "http://job-search-backend:5000"
        # NOTE: do NOT set NEXT_PUBLIC_API_URL — the browser must use the
        # relative /api rewrite (proxied server-side) so LAN/mobile clients
        # work. Baking localhost:5000 breaks phones (localhost = the phone).
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(REPO_ROOT / "apps" / "frontend"),
            env=build_env,
        )
        if result.returncode != 0:
            return False, "frontend-build"

        _log("Packaging frontend Docker image...")
        frontend_next = REPO_ROOT / "apps" / "frontend" / ".next"
        standalone_dir = frontend_next / "standalone"
        static_dir = frontend_next / "static"
        build_ctx = Path(tempfile.mkdtemp(prefix="frontend-build-"))
        try:
            shutil.copytree(standalone_dir, build_ctx, dirs_exist_ok=True)
            shutil.copytree(static_dir, build_ctx / ".next" / "static", dirs_exist_ok=True)
            shutil.copy(REPO_ROOT / "Dockerfile.frontend", build_ctx / "Dockerfile")
            result = subprocess.run(
                ["docker", "build", "-t", "job-search-frontend:latest", "."],
                cwd=str(build_ctx),
            )
        finally:
            shutil.rmtree(build_ctx, ignore_errors=True)
        if result.returncode != 0:
            return False, "frontend-docker"
        _ok("Frontend image built")
        return True, "frontend"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_backend = executor.submit(build_backend)
        f_background = executor.submit(build_background)
        f_frontend = executor.submit(build_frontend)

        results = [f_backend.result(), f_background.result(), f_frontend.result()]

    failed = [name for ok, name in results if not ok]
    if failed:
        _err(f"Failed to build: {', '.join(failed)}")
        raise typer.Exit(code=1)


def _run_terraform(args: list[str], auto_approve: bool = False) -> subprocess.CompletedProcess:
    """Run a terraform command in the terraform directory."""
    cmd = ["terraform"] + args
    if auto_approve:
        cmd.append("-auto-approve")
    return subprocess.run(
        cmd,
        cwd=str(TERRAFORM_DIR),
    )


def _run_terraform_with_vars(args: list[str], auto_approve: bool = False) -> subprocess.CompletedProcess:
    """Run a terraform command with the default vars file."""
    cmd = args.copy()
    vars_file = TERRAFORM_DIR / "terraform.tfvars.example"
    if vars_file.exists():
        cmd.extend(["-var-file", "terraform.tfvars.example"])
    if auto_approve:
        cmd.append("-auto-approve")
    return _run_terraform(cmd, auto_approve=False)


@terraform_app.command()
def up(
    build: bool = typer.Option(
        True, "--build/--no-build", "-b", help="Rebuild Docker images from current code before applying (default: on)"
    ),
):
    """Deploy to production with Terraform (rebuild images + apply).

    Does NOT run tests — run 'start terraform test' first; deploying
    untested code is the user's own responsibility.
    """
    _header("Terraform: Starting infrastructure")

    if build:
        _build_images()
    else:
        _warn("Skipping image rebuild (--no-build). Containers may run STALE code!")

    _log("Initializing Terraform...")
    result = _run_terraform(["init", "-backend=false"])
    if result.returncode != 0:
        _err("Terraform init failed")
        raise typer.Exit(code=1)

    # The image tags (:latest) never change, so plain `apply` sees no diff
    # and keeps STALE containers running. After a rebuild, force-recreate the
    # image-based containers so production actually runs the new code.
    # (Postgres/redis have no build step and keep their state — never replaced.)
    apply_args = ["apply"]
    if build:
        _log("Recreating app containers from rebuilt images...")
        for resource in (
            "docker_container.alembic",
            "docker_container.backend",
            "docker_container.background",
            "docker_container.frontend",
        ):
            apply_args.append(f"-replace={resource}")

    _log("Applying Terraform configuration...")
    result = _run_terraform_with_vars(apply_args, auto_approve=True)
    if result.returncode != 0:
        _err("Terraform apply failed")
        raise typer.Exit(code=1)

    console.print()
    _ok("Infrastructure started!")
    console.print()
    console.print("  Backend:  http://localhost:5000")
    console.print("  Frontend: http://localhost:5173")
    console.print("  Swagger:  http://localhost:5000/api/docs")
    console.print()


@terraform_app.command()
def test(
    suite: str = typer.Argument(
        "all", help="Test suite: backend, frontend, or all"
    ),
):
    """Run the test suites in capped Docker containers (backend/frontend/all).

    Run this BEFORE 'start terraform up' — deploying is production-only and
    never runs tests. It is the user's responsibility to test first.
    """
    if suite not in ("backend", "frontend", "all"):
        _err(f"Unknown suite '{suite}'. Choose: backend, frontend, all.")
        raise typer.Exit(code=2)
    _header(f"Terraform: Running {suite} tests (Docker, capped resources)")
    result = subprocess.run(
        ["./scripts/docker-test.sh", suite],
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        _err(f"'{suite}' tests FAILED. Fix failures before deploying.")
        raise typer.Exit(code=1)
    _ok(f"'{suite}' tests passed")


@terraform_app.command()
def down():
    """Stop and destroy Terraform infrastructure"""
    _header("Terraform: Destroying infrastructure")
    _log("Destroying Terraform resources...")

    result = _run_terraform_with_vars(["destroy"], auto_approve=True)
    if result.returncode != 0:
        _err("Terraform destroy failed")
        raise typer.Exit(code=1)

    _ok("Infrastructure destroyed (data volume preserved)")


@terraform_app.command()
def destroy():
    """Destroy everything including the data volume (WARNING: data loss!)"""
    _header("Terraform: Destroy everything")
    _warn("This will destroy infrastructure AND the data volume!")

    confirm = typer.confirm("Are you sure you want to destroy everything?")
    if not confirm:
        _log("Aborted.")
        raise typer.Exit()

    result = _run_terraform_with_vars(["destroy"], auto_approve=True)
    if result.returncode != 0:
        _err("Terraform destroy failed")
        raise typer.Exit(code=1)

    _log("Removing data volume...")
    subprocess.run(["docker", "volume", "rm", "jobsearch-pg-data"], capture_output=True)

    _ok("Everything destroyed (including data)")


@terraform_app.command()
def build():
    """Build Docker images for Terraform deployment"""
    _build_images()


@terraform_app.command()
def status():
    """Show Terraform infrastructure status"""
    _header("Terraform Status")

    _log("Checking running containers...")
    subprocess.run(
        ["docker", "ps", "--filter", "name=job-search", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
    )

    console.print()
    _log("Terraform outputs:")
    result = _run_terraform(["output"])
    if result.returncode != 0:
        _warn("No Terraform state found. Run 'start terraform up' first.")


@terraform_app.command()
def logs(
    service: str = typer.Argument(
        "backend", help="Service to show logs for (backend, frontend, postgres, redis, background)"
    ),
    tail: int = typer.Option(
        50, "--tail", "-n", help="Number of lines to show"
    ),
):
    """Show logs from a Terraform-managed container"""
    container_name = f"job-search-{service}"
    result = subprocess.run(
        ["docker", "logs", "--tail", str(tail), container_name],
    )
    if result.returncode != 0:
        _err(f"Failed to get logs for {container_name}")
        _log("Available services: backend, frontend, postgres, redis, background")
        raise typer.Exit(code=1)


@app.command()
def clean():
    """Remove build artifacts and caches"""
    _log("Cleaning build artifacts...")
    dirs = [
        REPO_ROOT / "apps" / "backend" / "__pycache__",
        REPO_ROOT / "apps" / "frontend" / "node_modules" / ".cache",
        REPO_ROOT / "target",
        REPO_ROOT / "tmp",
        REPO_ROOT / ".pytest_cache",
    ]
    for d in dirs:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            _ok(f"Removed: {d}")
    _ok("Clean completed.")


@app.command()
def doctor():
    """Validate development environment"""
    _header("Environment Check")
    all_ok = True

    tools = [
        ("rustc", ("--version",)),
        ("cargo", ("--version",)),
        ("python3", ("--version",)),
        ("node", ("--version",)),
        ("npm", ("--version",)),
        ("docker", ("--version",)),
        ("git", ("--version",)),
    ]
    for tool_name, args in tools:
        ok, msg = _check_tool(tool_name, *args)
        if ok:
            _ok(msg)
        else:
            _err(msg)
            all_ok = False

    if VENV_DIR.exists():
        _ok(f"Python venv: {VENV_DIR}")
    else:
        _warn("Python venv not found (expected at .venv/)")

    if SERVER_DIR.exists():
        _ok(f"Server dir: {SERVER_DIR}")
    else:
        _err("Server directory not found")
        all_ok = False

    if CLIENT_DIR.exists():
        _ok(f"Client dir: {CLIENT_DIR}")
    else:
        _err("Client directory not found")
        all_ok = False

    if (REPO_ROOT / ".env").exists():
        _ok(".env file found")
    else:
        _warn(".env file not found")

    console.print()
    if all_ok:
        _ok("All checks passed! Environment is ready.")
    else:
        _warn("Some checks failed. Please fix the issues above.")


@app.command()
def logs():
    """Stream logs from running services"""
    _log("Streaming logs...")
    log_file = REPO_ROOT / "tmp" / "app.log"
    if log_file.exists():
        subprocess.run(["tail", "-f", str(log_file)])
    else:
        _warn("No log file found at tmp/app.log")
        _log("Starting log tail from journalctl...")
        subprocess.run(["journalctl", "-f", "-u", "job-search"])


@app.command()
def version():
    """Show version information"""
    _header("Job Search Developer CLI")
    console.print(f"  Version: {read_version()}")
    console.print("  Binary:  start")
    console.print()


@app.command()
def stop():
    """Stop all running processes (dev and production)"""
    _log("Stopping all processes...")
    _stop_service("backend", PID_FILE)
    _stop_service("frontend", CLIENT_PID_FILE)
    _stop_service("backend (prod)", PROD_PID_FILE)
    _stop_service("frontend (prod)", PROD_CLIENT_PID_FILE)
    _stop_service("background", PID_BG_FILE)
    _stop_service("scheduler", PID_SCHED_FILE)
    _kill_by_pattern("mimo run")
    _ok("All processes stopped.")


@app.command()
def status():
    """Show status of running processes"""
    _header("Job Search App Status")

    backend_pid = _read_pid(PID_FILE)
    if backend_pid is not None and _is_process_alive(backend_pid):
        port = _load_port_from_env("BACKEND_PORT", 5000)
        _ok(f"Backend (dev):  Running (PID: {backend_pid}) — http://localhost:{port}")
    else:
        _warn("Backend (dev):  Not running")

    frontend_pid = _read_pid(CLIENT_PID_FILE)
    if frontend_pid is not None and _is_process_alive(frontend_pid):
        port = _load_port_from_env("FRONTEND_PORT", 5173)
        _ok(f"Frontend (dev): Running (PID: {frontend_pid}) — http://localhost:{port}")
    else:
        _warn("Frontend (dev): Not running")

    prod_be_pid = _read_pid(PROD_PID_FILE)
    if prod_be_pid is not None and _is_process_alive(prod_be_pid):
        port = _load_port_from_env("BACKEND_PORT", 5000)
        _ok(f"Backend (prod):  Running (PID: {prod_be_pid}) — http://localhost:{port}")
    else:
        _warn("Backend (prod):  Not running")

    prod_fe_pid = _read_pid(PROD_CLIENT_PID_FILE)
    if prod_fe_pid is not None and _is_process_alive(prod_fe_pid):
        port = _load_port_from_env("FRONTEND_PORT", 3000)
        _ok(f"Frontend (prod): Running (PID: {prod_fe_pid}) — http://localhost:{port}")
    else:
        _warn("Frontend (prod): Not running")

    background_pid = _read_pid(PID_BG_FILE)
    if background_pid is not None and _is_process_alive(background_pid):
        _ok(f"Background: Running (PID: {background_pid})")
    else:
        _warn("Background: Not running")

    scheduler_pid = _read_pid(PID_SCHED_FILE)
    if scheduler_pid is not None and _is_process_alive(scheduler_pid):
        _ok(f"Scheduler:  Running (PID: {scheduler_pid})")
    else:
        _warn("Scheduler:  Not running")

    mimo = subprocess.run(
        ["pgrep", "-f", "mimo run"], capture_output=True, text=True
    )
    count = len([l for l in mimo.stdout.splitlines() if l.strip()])
    if count > 0:
        _warn(f"Mimo AI:  {count} process(es) running")
    else:
        _ok("Mimo AI:  No processes running")

    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("AI_PROVIDER="):
                provider = line.split("=", 1)[1]
                _ok(f"AI Provider: {provider}")
                break

    console.print()


if __name__ == "__main__":
    app()
