"""Regression (prompt 222): both Docker stacks must run the TaskIQ scheduler.

Without the scheduler service, the periodic ``reconcile_stuck_executions``
sweep never fires and executions whose worker died mid-run stay RUNNING
forever (observed: Redis reader timeout killed a worker, job showed
"processing" indefinitely).
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]

SCHEDULER_CLI = "taskiq scheduler"
SCHEDULER_MODULE = "apps.backend.entrypoints.scheduler:create_scheduler"
SCHEDULER_TASKS = "shared.infrastructure.taskiq.tasks"


def test_dev_compose_defines_scheduler_service():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    services = compose.get("services") or {}
    assert "scheduler" in services, "docker-compose.yml must define a scheduler service"

    scheduler = services["scheduler"]
    command = " ".join(
        scheduler.get("command")
        if isinstance(scheduler.get("command"), list)
        else [scheduler.get("command", "")]
    )
    assert SCHEDULER_CLI in command
    assert SCHEDULER_MODULE in command
    assert SCHEDULER_TASKS in command
    assert scheduler.get("depends_on"), "scheduler must wait for its dependencies"


def test_dev_compose_scheduler_depends_on_redis_health():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    depends_on = compose["services"]["scheduler"]["depends_on"]
    assert depends_on.get("redis", {}).get("condition") == "service_healthy"


def test_terraform_prod_defines_scheduler_container():
    main_tf = (REPO_ROOT / "terraform" / "main.tf").read_text()
    assert SCHEDULER_MODULE in main_tf, (
        "terraform/main.tf must define a scheduler container running the "
        "taskiq scheduler entrypoint"
    )
    assert SCHEDULER_CLI in main_tf
    assert SCHEDULER_TASKS in main_tf


def test_scheduler_entrypoint_scopes_reconcile_task():
    """The scheduler's task module registers the reconcile sweep."""
    from shared.infrastructure.taskiq import tasks as taskiq_tasks

    assert taskiq_tasks.RECONCILE_INTERVAL_SECONDS > 0
    # The registered task must survive refactors/renames.
    source = Path(taskiq_tasks.__file__).read_text()
    assert "@broker.task" in source
    assert "async def reconcile_stuck_executions" in source
