// ── Pagination ──────────────────────────────────────────────────────────────
export const PAGE_SIZE = 10
export const PAGE_SIZE_SMALL = 10
/** User-facing rows-per-page choices, in consistent steps of 10. */
export const PAGE_SIZE_OPTIONS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] as const
export const HISTORY_PAGE_SIZE = 100
export const MAX_PAGE_SIZE = 200

// ── API ─────────────────────────────────────────────────────────────────────
export const API_BASE = '/api'
export const WORKFLOW_WS_PORT = 8765

// ── Auth / localStorage keys ───────────────────────────────────────────────
export const AUTH_TOKEN_KEY = 'js_auth_token'
export const AUTH_USER_KEY = 'js_auth_user'
export const COLUMN_WIDTHS_KEY = 'jobs-table-column-widths'
export const SIDEBAR_COLLAPSED_KEY = 'job-search.sidebar.collapsed'

// ── Sorting ─────────────────────────────────────────────────────────────────
export const SORT_FIELDS = ['created_at', 'overall_score', 'fit_score', 'success_score', 'company', 'location', 'applicants', 'posted_at', 'apply_time', 'response_time'] as const
export type SortField = typeof SORT_FIELDS[number]

// ── React Query defaults ────────────────────────────────────────────────────
export const DEFAULT_STALE_TIME = 30_000
export const DEFAULT_REFETCH_INTERVAL = 10_000
export const DEFAULT_RETRY_COUNT = 1

// ── SSE reconnect ───────────────────────────────────────────────────────────
export const SSE_RECONNECT_BASE_DELAY = 3000
export const SSE_RECONNECT_MAX_DELAY = 30000

// ── Polling intervals ──────────────────────────────────────────────────────
export const LOCAL_HISTORY_POLL_INTERVAL = 3000
export const GENERATION_HISTORY_POLL_INTERVAL = 5000

// ── UI feedback ────────────────────────────────────────────────────────────
export const COPY_FEEDBACK_TIMEOUT = 1500
export const DEBOUNCE_DELAY = 300

// ── Table layout ───────────────────────────────────────────────────────────
export const MIN_COLUMN_WIDTH = 50
export const MIN_LEADING_COLUMN_WIDTH = 44

// ── Max content width ──────────────────────────────────────────────────────
export const MAX_CONTENT_WIDTH = '1400px'
