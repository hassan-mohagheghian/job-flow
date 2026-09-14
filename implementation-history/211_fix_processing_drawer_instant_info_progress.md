# Prompt 211 - Fix Processing Drawer Instant Info Progress Bar

## Objective
The Processing Drawer progress bar does not show real-time step information during job processing. Step SSE events that arrive before the workflow is loaded from the API are silently dropped, and the entry card's `current_step` text never updates during execution. Fix both issues so the progress bar shows instant live info.

## Current State
- `ProcessingDrawer.tsx:360-377`: On `workflow.step.*` events, if `workflowsRef.current[execution_id]` is null (workflow not yet loaded), calls `ensureWorkflow()` and returns — the step event is lost, never buffered or replayed.
- `ProcessingDrawer.tsx:232-235`: Entry card shows `entry.current_step` from the queue snapshot. The snapshot's `current_step` is populated from `execution.workflow_progress.get("current_step")` in `processing_queue_service.py:47-48`. This DB field is only set at start (null) and end of execution — never during processing. So the entry card always shows `entry.status` ("running") instead of the actual step name.
- `ProcessingDrawer.tsx:264-267`: `workflowsRef` stores loaded workflows; `loadedRef` / `inFlightRef` prevent duplicate fetches. `ensureWorkflow:325-332` deletes from `loadedRef` then calls `loadWorkflow`.
- SSE pipeline is confirmed working end-to-end (Redis pub/sub → backend SSE → frontend EventSource). Events arrive with full step data.

## Changes

### 1. `apps/frontend/src/shared/components/ProcessingDrawer.tsx`

**Add a pending events buffer:**
- Add `const pendingEventsRef = useRef<Map<string, SSEEventEnvelope[]>>(new Map())` alongside existing refs.
- When a `workflow.step.*` event arrives and `workflowsRef.current[execution_id]` is null, instead of just calling `ensureWorkflow()` and returning, **buffer** the event: push `data` into `pendingEventsRef.current.get(execution_id)`.
- Create a new `applyPendingEvents` helper that drains the buffer for an execution_id and replays all buffered step events through `mergeWorkflowStep`.

**Apply buffered events after workflow loads:**
- In the `setWorkflow` callback (or after `loadWorkflow` completes in the SSE handler's `ensureWorkflow` path), call `applyPendingEvents(executionId)` to replay buffered events.
- Modify `loadWorkflow` to call `applyPendingEvents(executionId)` after `setWorkflow`.

**Update entry card `current_step` from SSE events:**
- On `workflow.step.started` events where `data.payload.step` has a `title`, update the corresponding entry in `snapshot` to reflect the current step name. Add a `setSnapshot` updater that patches `current_step` for the matching execution_id in the processing array.
- On `execution.completed` / `execution.failed` / `queue.entry.removed`, clear the `current_step` back to null (the snapshot will be refreshed by `loadSnapshot()` anyway).

### 2. `apps/frontend/src/shared/components/ProcessingDrawer.test.tsx`
- Add test: "buffers step events received before workflow loads and replays them"
- Add test: "updates entry current_step from workflow.step.started event"

## Testing Requirements
- `cd apps/frontend && npx vitest run --reporter=verbose` (ProcessingDrawer tests)
- `./scripts/docker-test.sh frontend`

## Constraints
- Do not change the SSE wire contract or backend event publishing.
- Do not add cross-context FKs or model changes.
- Preserve existing behavior for events that arrive after workflow is loaded (no regression).
