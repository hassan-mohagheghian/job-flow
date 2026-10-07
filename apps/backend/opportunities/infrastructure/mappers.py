"""Mappers between Opportunity ORM models and plain dicts.

JSON columns are stored as text; mappers parse them into dicts/lists on read
and dump them on write.
"""

from __future__ import annotations

import json
from typing import Any

_JSON_TEXT_FIELDS = (
    "extracted_urls",
    "extracted",
    "evaluation",
    "missing_information",
    "application_path",
    "snapshot",
)


def _parse_json(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _dump_json(value: Any, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def opportunity_model_to_dict(model: Any) -> dict[str, Any]:
    return {
        "id": model.id,
        "user_id": model.user_id,
        "source": model.source,
        "source_message_id": model.source_message_id,
        "sender": model.sender,
        "sender_email": model.sender_email,
        "received_at": model.received_at,
        "subject": model.subject,
        "raw_content": model.raw_content,
        "content_hash": model.content_hash,
        "extracted_urls": _parse_json(model.extracted_urls, []),
        "extracted": _parse_json(model.extracted, {}),
        "company_id": model.company_id,
        "company_name": model.company_name,
        "job_id": model.job_id,
        "job_title": model.job_title,
        "status": model.status,
        "evaluation_status": model.evaluation_status,
        "fit_score": model.fit_score,
        "success_score": model.success_score,
        "overall_score": model.overall_score,
        "recommendation": model.recommendation,
        "evaluation": _parse_json(model.evaluation, {}),
        "missing_information": _parse_json(model.missing_information, []),
        "application_path": _parse_json(model.application_path, {}),
        "next_action": model.next_action,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def evaluation_model_to_dict(model: Any) -> dict[str, Any]:
    return {
        "id": model.id,
        "opportunity_id": model.opportunity_id,
        "status": model.status,
        "evaluation_status": model.evaluation_status,
        "fit_score": model.fit_score,
        "success_score": model.success_score,
        "overall_score": model.overall_score,
        "recommendation": model.recommendation,
        "snapshot": _parse_json(model.snapshot, {}),
        "created_at": model.created_at,
    }


def dump_json_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Dump JSON-text fields of an opportunity payload for persistence."""
    dumped = dict(data)
    for field_name in ("extracted_urls", "extracted", "evaluation", "missing_information", "application_path"):
        if field_name in dumped:
            dumped[field_name] = _dump_json(
                dumped[field_name], "[]" if field_name in ("extracted_urls", "missing_information") else "{}"
            )
    return dumped


__all__ = [
    "opportunity_model_to_dict",
    "evaluation_model_to_dict",
    "dump_json_fields",
]
