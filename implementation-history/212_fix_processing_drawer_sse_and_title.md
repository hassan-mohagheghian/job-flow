# Prompt 212 - Fix Processing Drawer SSE Reliability, Title Fallback, and Refresh Safety Net

## Objective
The Processing Drawer progress bar freezes at the early stage and never updates in real-time. After processing completes, the user must manually refresh to see the final status. Additionally, entry card titles show UUIDs instead of meaningful job titles. Fix all three root causes.

## Root Causes
1. **SSE listener crash isolation**: `processingEvents.ts:58` uses `listeners.forEach()`. If any listener throws (e.g. `useProcessingEvents` hook's `queryClient` call), JavaScript's `Set.forEach` stops iteration and subsequent listeners (ProcessingDrawer's) are never called.
2. **`loadedRef` blocks retries on failure**: `ProcessingDrawer.tsx:338-339` marks execution as loaded even when `processingApi.get()` fails (catch block). This prevents all future retries for that execution, leaving the workflow permanently null.
3. **No refresh safety net**: When the drawer opens after SSE events have already fired (or if the SSE connection briefly drops), there's no mechanism to recover. The initial `loadWorkflow` returns stale DB state (runner only persists at start/end).
4. **Title shows UUID**: `processing_queue_service.py:137-139` falls back to `execution.target_id` (UUID) when `job.get("title")` and `job.get("role")` are both falsy for newly imported jobs.

## Changes

### 1. `apps/backend/processing/application/services/processing_queue_service.py`
- Add `_truncate_url()` helper: parses URL, returns `netloc + path` truncated to 60 chars.
- Update `_title()`: insert `_truncate_url(job.get("url"))` before the UUID fallback for both jobs and companies.
- Clean up import ordering (stdlib `urlparse` grouped with stdlib imports).

### 2. `apps/frontend/src/shared/api/processingEvents.ts`
- Replace `listeners.forEach((listener) => listener(type, data))` with a `for...of` loop where each `listener(type, data)` call is wrapped in its own `try/catch`. This prevents one failing listener from blocking others.
- Add optional `setSSELogging(enabled)` export for debug logging of listener errors.

### 3. `apps/frontend/src/shared/components/ProcessingDrawer.tsx`
- **Remove `loadedRef.current.add(executionId)` from catch block**: On API failure, do NOT mark as loaded. This allows `ensureWorkflow` and periodic refresh to retry.
- **Add periodic refresh `useEffect`**: When the drawer is open and there are active (processing/queued) entries, run `setInterval(5_000)` that calls `loadSnapshot()` + `loadWorkflow()` for active entries. Cleanup on unmount or when no active entries remain.

## Testing
- Backend: `./scripts/docker-test.sh backend` — all existing tests pass.
- Frontend: `npx vitest run src/shared/components/ProcessingDrawer.test.tsx` — 3/3 pass.
- Frontend: `npx vitest run src/shared/hooks/useProcessingEvents.test.tsx src/features/jobs-v2/components/ProcessingDrawer.test.tsx` — 13/13 pass.
- TypeScript: no new errors introduced (all pre-existing).
