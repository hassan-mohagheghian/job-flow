# Prompt 217 - Fix SSE Proxy Buffering for Live Processing Updates

## Objective
Make the processing-events SSE stream arrive live in browsers reaching the backend through the Next.js standalone rewrite proxy (`/events/*`), so the Jobs list and Queue drawer update without manual Refresh.

## Current State
- Browsers send `Accept-Encoding: gzip`; the Next standalone proxy compresses the proxied SSE response and buffers it, so neither `: connected` nor events arrive until the buffer flushes (verified: plain curl streams instantly, gzip curl receives nothing).
- Backend sets only `Cache-Control: no-cache` + `X-Accel-Buffering: no` on both SSE `StreamingResponse`s (`shared/presentation/api/processing_events_router.py:64`, `processing/presentation/api/executions_router.py:136`).
- `docs/api/sse/processing-events.md:458` wrongly claims the standalone proxy streams without compression.
- Backend/background run as prebuilt images without bind mounts (`docker-compose.yml`), so the fix needs an image rebuild + container recreate.

## Changes
1. Add `no-transform` to `Cache-Control` on both SSE `StreamingResponse`s (`no-cache, no-transform`), keeping `X-Accel-Buffering: no`. `no-transform` instructs compliant proxies not to compress/transform the stream.
2. Extend `apps/backend/tests/shared/presentation/api/test_processing_events_router.py`: assert the global stream response carries `no-transform` (guards the proxy contract).
3. Correct `docs/api/sse/processing-events.md` proxy paragraph (gzip buffering + `no-transform` fix).
4. Rebuild the backend image (`docker compose build backend`) and recreate the backend container; verify live with a gzip `curl` through `:5173/events/processing` + a synthetic Redis event.

## Testing Requirements
- New header assertion test passes: `./scripts/docker-test.sh backend` (targeted SSE file first).
- Live verification (not committable, do manually): gzip curl receives `: connected` immediately and the synthetic event within seconds.
- Frontend suite untouched (no frontend change); full `./scripts/docker-test.sh frontend` optional.

## Constraints
- Respect AGENTS.md rules 3 (no raw SQL — n/a), 11, 14 (no migration), 16 (no transport change — the event flow is untouched, only HTTP headers), 18 (Docker tests only).
