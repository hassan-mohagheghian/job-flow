# TaskIQ Processing Queue

## Purpose

This document describes the background processing infrastructure based on TaskIQ.

TaskIQ is responsible only for background task execution.

It does not contain business logic or workflow orchestration.

The system separates:

- API execution requests
- Domain processing execution
- Background task execution
- Workflow orchestration

## Architecture Overview

The processing architecture contains three independent layers:

1. Application Layer
2. Infrastructure Layer
3. Workflow Layer

## Application Layer

The application layer manages business execution requests.

Main component:

- ProcessingExecution

Responsibilities:

- Create execution records
- Track execution lifecycle
- Store execution metadata
- Create processing requests
- Trigger workflow execution

The domain layer must not depend on TaskIQ.

ProcessingExecution only knows that execution should be dispatched.

The queue implementation is an infrastructure concern.

## Infrastructure Layer

The infrastructure layer manages background execution.

Main components:

- TaskIQ
- Redis Broker
- TaskIQ Worker

Responsibilities:

- Dispatch background tasks
- Execute worker processes
- Handle retries
- Manage task lifecycle
- Communicate through Redis

TaskIQ is replaceable infrastructure.

Business logic must not directly depend on TaskIQ.

## Workflow Layer

The workflow layer manages processing orchestration.

Main component:

- LangGraph

Responsibilities:

- Define workflow graph
- Manage workflow state
- Execute workflow nodes
- Handle branching
- Save checkpoints
- Resume failed workflows
- Generate progress events

LangGraph owns workflow state.

TaskIQ only starts workflow execution.

## Final Architecture

API

↓

ProcessingExecution

↓

TaskIQ Task

↓

TaskIQ Worker

↓

LangGraph Workflow

↓

Database

↓

SSE Events

# Redis Broker

Redis is used as the TaskIQ message broker.

Redis responsibilities:

- Store pending tasks
- Deliver tasks to workers
- Manage task communication

Redis does not store business workflow state.

Business state belongs to:

- PostgreSQL
- ProcessingExecution records
- LangGraph checkpoints

# Worker Lifecycle

A TaskIQ worker lifecycle:

1. Worker starts

2. Connects to Redis broker

3. Waits for tasks

4. Receives processing execution task

5. Loads ProcessingExecution

6. Starts LangGraph workflow

7. Updates execution progress

8. Publishes processing events

9. Completes task

Worker flow:

Worker Started

↓

Connect Redis

↓

Receive Task

↓

Execute Workflow

↓

Update Execution

↓

Complete

# Task Definition

TaskIQ tasks should be thin infrastructure wrappers.

Example:

process_job_execution_task(execution_id)

The task responsibilities:

- Receive execution identifier
- Load execution context
- Start LangGraph workflow
- Handle infrastructure failures
- Report execution result

The task must not contain:

- Job analysis logic
- AI prompt logic
- Scoring logic
- Workflow decisions

# Retry Strategy

Retries are managed by TaskIQ.

## Retryable Failures

Examples:

- Network failures
- Temporary provider failures
- External API timeout
- Service unavailable errors

## Non Retryable Failures

Examples:

- Invalid input
- Missing required data
- Business validation errors

Retry flow:

Task Failure

↓

Check Error Type

↓

Retryable

↓

Retry Task

Non retryable:

Task Failure

↓

Mark Execution Failed

# Error Handling

## Infrastructure Failures

TaskIQ Failure

↓

Retry

↓

Maximum retries reached

↓

ProcessingExecution Failed

## Workflow Failures

LangGraph Node Failure

↓

Checkpoint Saved

↓

Execution Marked Failed

# Scheduling

TaskIQ can execute:

- Immediate tasks
- Delayed tasks
- Scheduled maintenance tasks

Examples:

Immediate execution:

process_job_execution_task(execution_id)

Scheduled execution:

periodic_db_backup

## Dev DB Backup Scheduler

During development (`./start -b` or `./start background`) a TaskIQ scheduler
runs `periodic_db_backup`, which:

- Dumps the main PostgreSQL database with `pg_dump` (run inside the
  `job-search-postgres-1` container via `docker exec`).
- Runs every `DB_BACKUP_INTERVAL_MINUTES` minutes (default 10).
- Keeps only the `DB_BACKUP_KEEP_COUNT` most recent dumps (default 3) and
  deletes older ones.

Configuration lives in `.env`:

- `DB_BACKUP_INTERVAL_MINUTES` (default 10)
- `DB_BACKUP_KEEP_COUNT` (default 3)
- `DB_BACKUP_DIR` (default `<repo>/backups`)
- `DB_BACKUP_CONTAINER` (default `job-search-postgres-1`)

Backups are written to `DB_BACKUP_DIR` as `jobsearch_YYYYMMDD_HHMMSS.dump` and
are gitignored. The task is registered in `shared.infrastructure.taskiq.tasks`
(the worker's `TASK_MODULES`), so the worker can execute it — the "task not
found" warning does not occur.

## Scheduler in Docker Stacks

The scheduled tasks (`reconcile_stuck_executions`, `periodic_db_backup`) need
a running TaskIQ scheduler process alongside the worker — the worker alone
does not fire scheduled tasks. Both Docker stacks run it via a dedicated
`scheduler` service/container that reuses the background image and runs:

    taskiq scheduler apps.backend.entrypoints.scheduler:create_scheduler \
        shared.infrastructure.taskiq.tasks

- Dev: `scheduler` service in `docker-compose.yml` (waits for Redis healthy).
- Production: `docker_container.scheduler` in `terraform/main.tf`.

This is essential for crash recovery: when a worker process dies mid-execution
(e.g. a Redis reader timeout), the sweep fails the RUNNING execution with the
timeout message after `WORKER_JOB_TIMEOUT` so Retry becomes available again.
Regression tests pin this wiring:
`apps/backend/tests/shared/infrastructure/taskiq/test_scheduler_stack_wiring.py`.

# Deployment Model

Production services:

- FastAPI API service
- TaskIQ Worker service
- TaskIQ Scheduler service
- Redis broker
- PostgreSQL database

Deployment flow:

FastAPI

↓

Redis Broker

↓

TaskIQ Workers

↓

LangGraph Execution

↓

PostgreSQL

# Development Environment

Required services:

- Redis
- PostgreSQL
- FastAPI
- TaskIQ Worker
- TaskIQ Scheduler (fires scheduled tasks, e.g. reconcile sweep)

Local environment:

Redis

↓

FastAPI

↓

TaskIQ Worker

↓

TaskIQ Scheduler (periodic maintenance)

↓

Database

# Monitoring

Monitoring should include:

## Worker Metrics

- Active workers
- Running tasks
- Completed tasks
- Failed tasks
- Retry count

## Execution Metrics

- ProcessingExecution status
- Workflow progress
- Execution duration
- Failed workflow nodes

# Migration From ARQ

The previous system used ARQ as background execution infrastructure.

Previous architecture:

API

↓

ARQ Queue

↓

ARQ Worker

↓

Processing

New architecture:

API

↓

ProcessingExecution

↓

TaskIQ Queue

↓

TaskIQ Worker

↓

LangGraph Workflow

# Deprecated Components

The following components are deprecated:

- ARQ Worker
- ARQ Queue Configuration
- ARQ Task Definitions

# Related Documents

- docs/adr/019-taskiq-migration.md
- docs/domain/processing/processing-execution.md
- docs/workflows/job-processing.md
- docs/ai/workflows.md
- docs/api/processing/process-job.md
- docs/api/sse/processing-events.md
