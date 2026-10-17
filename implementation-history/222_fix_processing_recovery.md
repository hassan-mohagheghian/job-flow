# Prompt 222 - Processing Resilience: Reconcile Scheduler in Docker + opencode Exit-Code-1 Tolerance

## Objective
The latest job shows "processing" forever. Make job processing resilient in Docker stacks and stop the analyze step from fail-fast-discarding valid LLM output.

## Current State
- Crash sweep exists: `reconcile_stuck_executions` (`shared/infrastructure/taskiq/tasks.py:79`, 30s interval) fails stale RUNNING and re-enqueues stuck QUEUED executions; scheduled labels need a `taskiq scheduler` process (`apps/backend/entrypoints/scheduler.py`), which hostmode `apps/start.py` starts.
- Docker stacks (dev `docker-compose.yml` + prod `terraform/main.tf`) have no scheduler container → sweep never runs → the worker death (`redis.exceptions.TimeoutError` killed worker-0 at 10:08, log `worker-0 is dead. Scheduling reload.`) leaves execution `2deee945…` RUNNING forever, heartbeat frozen at 10:08:22 → UI shows processing indefinitely.
- Earlier runs of the same job failed fast: `LLM call failed: opencode failed (exit code 1): ```json…` — `OpencodeProvider.generate` (`ai/infrastructure/providers/opencode/adapter.py:73-81`) raises on nonzero exit even though complete text parts streamed; so `AnalyzeNode._obtain_valid_payload` (`processing/application/workflows/job_analysis/nodes/analyze_node.py:134`) never reaches its validation-retry loop. Fetch `HTTP 403` (indeed) per-source is by-design nonfatal (fetch_sources_node).

## Changes
1. `docker-compose.yml`: add `scheduler` service — same `Dockerfile.background` image, command `uv run taskiq scheduler apps.backend.entrypoints.scheduler:create_scheduler shared.infrastructure.taskiq.tasks`, env like `background`, depends_on redis healthy.
2. `terraform/main.tf`: add `docker_container.scheduler` mirroring the background resource with the scheduler command.
3. `generate` (adapter.py): on nonzero returncode but non-empty parsed text content, log and proceed (metadata carries the returncode) instead of raising; still raise when there is no content. Downstream validation/retries then handle malformed payloads.
4. `execution_runner.run` completion path: clear `error_message` when an execution completes — a workflow finishing after the reconcile sweep already recorded its timeout message would otherwise keep a "timed out" error on a COMPLETED execution (observed live after redelivery finished at 10:41:41).
5. Regression tests: (a) provider — exit code 1 with streamed content returns content; exit code 1 without content raises; generate_structured parses fenced JSON after nonzero exit; (b) stack wiring — both docker-compose.yml and terraform/main.tf define a scheduler service (compose as YAML, terraform file has the `taskiq scheduler` command); (c) runner — completion clears stale timeout error_message.
6. No migration. Existing stuck execution: the scheduler reconciled it live (fails after WORKER_JOB_TIMEOUT); the redelivered run then completed the full 14-step workflow (analyze included) and scores persisted.

## Testing Requirements
- Backend Docker pytest: provider tests + taskiq sweep tests (`apps/backend/tests/`, `shared/infrastructure/taskiq/`).
- After deploy: within ~30s sweep, stuck execution flips FAILED with timeout message.

## Constraints
- AGENTS.md: 1 (LLMService path), 11 (structlog), 18 (Docker tests only). Do not weaken reconciliation thresholds.
