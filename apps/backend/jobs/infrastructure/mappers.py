"""Domain-to-database mapping for the Jobs context.

Converts between domain dictionaries and SQLAlchemy ORM models in the
infrastructure layer, keeping the domain layer clean of persistence concerns.
"""

from typing import Any
from datetime import datetime

from jobs.infrastructure.models.job_model import JobModel


def _to_str(value: Any) -> Any:
    """Normalize datetime values to ISO strings (Text columns may hold datetimes on fresh inserts)."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def job_model_to_dict(model: JobModel) -> dict[str, Any]:
    """Convert a JobModel to a domain dictionary."""
    return {
        "id": model.id,
        "source_site_id": getattr(model, "source_site_id", None),
        "company": model.company,
        "role": model.role,
        "location": model.location,
        "salary": model.salary,
        "stack": model.stack,
        "visa": model.visa,
        "applicants": model.applicants,
        "posted": model.posted,
        "industry": model.industry,
        "domain": model.domain,
        "notes": model.notes,
        "links": model.links,
        "action": model.action,
        "url": model.url,
        "workflow_log": model.workflow_log,
        "deleted": model.deleted,
        "work_types": model.work_types,
        "employment_types": model.employment_types,
        "raw_description": model.raw_description,
        "structured_description": model.structured_description,
        "adv_at": model.adv_at,
        "see_at": model.see_at,
        "apply_reason": model.apply_reason,
        "fit_score": model.fit_score,
        "success_score": model.success_score,
        "overall_score": model.overall_score,
        "company_id": model.company_id,
        "created_at": _to_str(model.created_at),
        "updated_at": _to_str(model.updated_at),
        "title": model.title,
        "description": model.description,
        "apply_time": model.apply_time,
        "response_time": model.response_time,
        "response_status": model.response_status,
        "rescoring": model.rescoring,
        "pinned": model.pinned,
        "dismissed": model.dismissed,
        "tags": model.tags,
        "status": model.status,
        "queue_order": model.queue_order,
        "current_node": model.current_node,
        "progress_pct": model.progress_pct,
        "error": model.error,
        "retry_count": model.retry_count,
        "failure_reason": model.failure_reason,
        "failure_step": model.failure_step,
        "failure_timestamp": model.failure_timestamp,
        "session_id": model.session_id,
        "easy_apply": model.easy_apply,
    }


def dict_to_job_model(data: dict[str, Any]) -> JobModel:
    """Convert a domain dictionary to a JobModel."""
    return JobModel(**{k: v for k, v in data.items() if hasattr(JobModel, k)})


# Columns the Jobs list needs. Used with ``load_only`` so list queries never
# fetch the multi-KB description / workflow columns.
JOB_LIST_FIELDS = (
    "id",
    "title",
    "role",
    "company",
    "location",
    "work_types",
    "visa",
    "pinned",
    "dismissed",
    "tags",
    "easy_apply",
    "status",
    "overall_score",
    "fit_score",
    "success_score",
    "updated_at",
    "created_at",
)


def job_model_to_list_dict(model: JobModel) -> dict[str, Any]:
    """Convert a partially-loaded JobModel into the Jobs list projection.

    Only reads the fields in ``JOB_LIST_FIELDS``; pair with
    ``load_only(*JOB_LIST_FIELDS)`` to avoid loading text payloads.
    """
    return {
        "id": model.id,
        "title": model.title,
        "role": model.role,
        "company": model.company,
        "location": model.location,
        "work_types": model.work_types,
        "visa": model.visa,
        "pinned": model.pinned,
        "dismissed": model.dismissed,
        "tags": model.tags,
        "easy_apply": model.easy_apply,
        "status": model.status,
        "overall_score": model.overall_score,
        "fit_score": model.fit_score,
        "success_score": model.success_score,
        "updated_at": _to_str(model.updated_at),
        "created_at": _to_str(model.created_at),
    }
