"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVER_DIR = os.path.abspath(os.path.join(_SERVER_DIR, '..', '..', '..'))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SERVER_DIR, '..', '..'))

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Set it to a PostgreSQL connection string, e.g.:\n"
        "  DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/jobsearch\n"
        "Or use Docker Compose: docker compose up -d postgres"
    )

# Normalize to use psycopg v3 dialect if plain postgresql:// was given
if DATABASE_URL.startswith('postgresql://') and '+psycopg' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)

PROJECT_ROOT = _PROJECT_ROOT
STATIC_FOLDER = os.path.join(_SERVER_DIR, '..', 'frontend', 'dist')

AI_PROVIDER = os.environ.get('AI_PROVIDER', 'mimo')

# Dev DB backup scheduler
DB_BACKUP_INTERVAL_MINUTES = int(os.environ.get('DB_BACKUP_INTERVAL_MINUTES', '10'))
DB_BACKUP_KEEP_COUNT = int(os.environ.get('DB_BACKUP_KEEP_COUNT', '3'))
_DB_BACKUP_DIR = os.environ.get('DB_BACKUP_DIR', os.path.join(_PROJECT_ROOT, 'backups'))
DB_BACKUP_DIR = os.path.abspath(_DB_BACKUP_DIR) if os.path.isabs(_DB_BACKUP_DIR) else os.path.join(_PROJECT_ROOT, _DB_BACKUP_DIR)
DB_BACKUP_CONTAINER = os.environ.get('DB_BACKUP_CONTAINER', 'job-search-postgres')

# Authentication
JWT_SECRET = os.environ.get('JWT_SECRET', 'js-auth-secret-change-in-production-2026')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
DEFAULT_USER_USERNAME = os.environ.get('DEFAULT_USER_USERNAME', 'hassan')
DEFAULT_USER_PASSWORD = os.environ.get('DEFAULT_USER_PASSWORD', 'hassan')
DEFAULT_USER_DISPLAY_NAME = os.environ.get('DEFAULT_USER_DISPLAY_NAME', 'Hassan')

# ── AI / LLM ────────────────────────────────────────────────────────────────
LLM_DEFAULT_TIMEOUT = int(os.environ.get('LLM_DEFAULT_TIMEOUT', '300'))
LLM_FETCH_TIMEOUT = int(os.environ.get('LLM_FETCH_TIMEOUT', '30'))
LLM_FETCH_MAX_RETRIES = int(os.environ.get('LLM_FETCH_MAX_RETRIES', '2'))
LLM_EXTRACT_JOB_TIMEOUT = int(os.environ.get('LLM_EXTRACT_JOB_TIMEOUT', '90'))
LLM_EXTRACT_COMPANY_TIMEOUT = int(os.environ.get('LLM_EXTRACT_COMPANY_TIMEOUT', '180'))
LLM_ANALYZE_COMPANY_TIMEOUT = int(os.environ.get('LLM_ANALYZE_COMPANY_TIMEOUT', '300'))
LLM_CANDIDATE_EXTRACT_TIMEOUT = int(os.environ.get('LLM_CANDIDATE_EXTRACT_TIMEOUT', '240'))
LLM_BACKFILL_TIMEOUT = int(os.environ.get('LLM_BACKFILL_TIMEOUT', '60'))

# ── AI retry / backoff ──────────────────────────────────────────────────────
LLM_RETRY_MAX_ATTEMPTS = int(os.environ.get('LLM_RETRY_MAX_ATTEMPTS', '10'))
LLM_RETRY_BACKOFF_CAP = float(os.environ.get('LLM_RETRY_BACKOFF_CAP', '16.0'))
LLM_RETRY_BASE_DELAY = float(os.environ.get('LLM_RETRY_BASE_DELAY', '1.0'))
LLM_RETRY_MAX_DELAY = float(os.environ.get('LLM_RETRY_MAX_DELAY', '30.0'))

# ── Fetch / web scraping ────────────────────────────────────────────────────
FETCH_MIN_CONTENT_LENGTH = int(os.environ.get('FETCH_MIN_CONTENT_LENGTH', '100'))
FETCH_MAX_CONTENT_LENGTH = int(os.environ.get('FETCH_MAX_CONTENT_LENGTH', '5000'))
FETCH_COMPANY_MAX_LENGTH = int(os.environ.get('FETCH_COMPANY_MAX_LENGTH', '8000'))
FETCH_USER_AGENT = os.environ.get(
    'FETCH_USER_AGENT',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
)

# ── Cache ────────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', str(3600 * 6)))
CACHE_DIR = os.environ.get('CACHE_DIR', 'tmp/ai_tool_cache')

# ── Context budget (LLM prompt sizing) ─────────────────────────────────────
CONTEXT_MAX_SOURCE_CHARS = int(os.environ.get('CONTEXT_MAX_SOURCE_CHARS', '8000'))
CONTEXT_MAX_COMBINED_CHARS = int(os.environ.get('CONTEXT_MAX_COMBINED_CHARS', '48000'))

# ── Scoring ──────────────────────────────────────────────────────────────────
SCORING_FIT_WEIGHT = float(os.environ.get('SCORING_FIT_WEIGHT', '0.6'))
SCORING_SUCCESS_WEIGHT = float(os.environ.get('SCORING_SUCCESS_WEIGHT', '0.4'))
COMPANY_FUZZY_THRESHOLD = float(os.environ.get('COMPANY_FUZZY_THRESHOLD', '0.88'))
COMPANY_ROOT_DOMAIN_THRESHOLD = float(os.environ.get('COMPANY_ROOT_DOMAIN_THRESHOLD', '0.6'))

# ── Pagination ───────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', '25'))
MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', '200'))

# ── SSE keepalive ────────────────────────────────────────────────────────────
SSE_KEEPALIVE_SECONDS = int(os.environ.get('SSE_KEEPALIVE_SECONDS', '15'))

# ── Process management ──────────────────────────────────────────────────────
PROCESS_GRACEFUL_KILL_TIMEOUT = float(os.environ.get('PROCESS_GRACEFUL_KILL_TIMEOUT', '5.0'))
PROCESS_KILL_POLL_INTERVAL = float(os.environ.get('PROCESS_KILL_POLL_INTERVAL', '0.2'))
PROCESS_WAIT_AFTER_KILL = int(os.environ.get('PROCESS_WAIT_AFTER_KILL', '3'))
SUBPROCESS_STDIN_JOIN_TIMEOUT = int(os.environ.get('SUBPROCESS_STDIN_JOIN_TIMEOUT', '5'))
QUEUE_STOP_TIMEOUT = float(os.environ.get('QUEUE_STOP_TIMEOUT', '15.0'))