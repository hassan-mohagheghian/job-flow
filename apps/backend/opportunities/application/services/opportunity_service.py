"""OpportunityService — manual inbound-opportunity pipeline.

Flow:

    create_manual (store message, dedupe)
        ↓
    process / reprocess: extract → resolve → evaluate
        ↓
    set_status / set_links (funnel tracking, manual corrections)
        ↓
    delete (hard delete with evaluation history)

Phase one is synchronous (no TaskIQ/SSE): ``process`` runs the two structured
LLM calls (``opportunity.extract``, ``opportunity.evaluate``) inline and
returns the updated opportunity. All AI calls go through LLMService (rule #1).

The context never creates jobs, companies, or skills — resolution only links
existing rows. Domain events are emitted through the OpportunityEventPublisher
port (in-memory collector by default — EDD is incremental, no pub/sub yet).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, UTC
from typing import Any

from ai.infrastructure.service import get_llm_service
from pydantic import ValidationError as PydanticValidationError

from companies.application.services.company_matching_service import (
    extract_domain,
    normalize_company_name,
)
from jobs.domain.services.job_url_rules import find_duplicate_job
from opportunities.application.services.opportunity_evaluate_prompt import (
    OPPORTUNITY_EVALUATE_PROMPT_VERSION,
    OPPORTUNITY_EVALUATE_SCHEMA_VERSION,
    build_opportunity_evaluate_output_schema,
    build_opportunity_evaluate_prompt,
)
from opportunities.application.services.opportunity_evaluate_validation import (
    OpportunityEvaluateOutput,
)
from opportunities.application.services.opportunity_extract_prompt import (
    OPPORTUNITY_EXTRACT_PROMPT_VERSION,
    OPPORTUNITY_EXTRACT_SCHEMA_VERSION,
    build_opportunity_extract_output_schema,
    build_opportunity_extract_prompt,
)
from opportunities.application.services.opportunity_extract_validation import (
    OpportunityExtractOutput,
)
from opportunities.domain.entities.opportunity import (
    EvaluationStatus,
    FieldState,
    OpportunitySource,
    OpportunityStatus,
)
from opportunities.domain.event_publisher import (
    InMemoryEventCollector,
    OpportunityEventPublisher,
)
from opportunities.domain.events import (
    OpportunityCreated,
    OpportunityEvaluated,
    OpportunityExtracted,
    OpportunityLinked,
    OpportunityStatusChanged,
)
from processing.application.services.job_analysis_inputs import (
    build_candidate_profile_text,
    build_scoring_rules_text,
)
from processing.application.services.job_analysis_scoring import (
    calculate_overall_score,
    recommendation_for_overall,
)
from shared.application.exceptions import (
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from shared.infrastructure.process.logging_config import get_logger

log = get_logger("opportunity.pipeline")

_URL_RE = re.compile(r"https?://[^\s)>\]]+")
_TRAILING_PUNCT = ".,;:!?'\""


class OpportunityPipelineError(Exception):
    """Raised when the AI extraction/evaluation step fails."""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _content_hash(raw_content: str) -> str:
    normalized = re.sub(r"\s+", " ", (raw_content or "").strip()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _find_urls(text: str) -> list[str]:
    seen: list[str] = []
    for match in _URL_RE.findall(text or ""):
        url = match.rstrip(_TRAILING_PUNCT)
        if url and url not in seen:
            seen.append(url)
    return seen


def _coerce_payload(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _display_title(row: dict[str, Any]) -> str:
    extracted = row.get("extracted") or {}
    role = extracted.get("role_title")
    if role:
        return str(role)
    if row.get("job_title"):
        return str(row["job_title"])
    if row.get("subject"):
        return str(row["subject"])
    return "Unknown role"


class OpportunityService:
    """Business operations for the Opportunity aggregate."""

    def __init__(
        self,
        opportunity_repo: Any,
        evaluation_repo: Any,
        job_repo: Any = None,
        company_repo: Any = None,
        skill_repo: Any = None,
        profile_repo: Any = None,
        rule_repo: Any = None,
        llm: Any | None = None,
        event_publisher: OpportunityEventPublisher | None = None,
    ):
        self._opportunities = opportunity_repo
        self._evaluations = evaluation_repo
        self._jobs = job_repo
        self._companies = company_repo
        self._skills = skill_repo
        self._profiles = profile_repo
        self._rules = rule_repo
        self._llm = llm
        self.event_publisher = event_publisher or InMemoryEventCollector()

    # ── Create ────────────────────────────────────────────────────

    def create_manual(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Store a manually pasted inbound message.

        Idempotent: an identical message (or the same external message id)
        returns the existing opportunity with ``duplicate=True`` instead of a
        new row. Returns (opportunity, duplicate).
        """
        source = str(data.get("source") or OpportunitySource.MANUAL).strip().lower()
        if source not in OpportunitySource.ALL:
            raise ValidationError(
                f"Invalid source '{source}'; allowed: {', '.join(OpportunitySource.ALL)}"
            )
        raw_content = str(data.get("raw_content") or "").strip()
        if not raw_content:
            raise ValidationError("raw_content must not be empty")

        source_message_id = (str(data.get("source_message_id") or "").strip() or None)
        if source_message_id:
            existing = self._opportunities.get_by_source_message(source, source_message_id)
            if existing:
                return self._present(existing), True

        content_hash = _content_hash(raw_content)
        existing = self._opportunities.get_by_content_hash(content_hash)
        if existing:
            return self._present(existing), True

        now = _now_iso()
        stored = self._opportunities.create(
            {
                "source": source,
                "source_message_id": source_message_id,
                "sender": (str(data.get("sender") or "").strip() or None),
                "sender_email": (str(data.get("sender_email") or "").strip() or None),
                "received_at": data.get("received_at"),
                "subject": (str(data.get("subject") or "").strip() or None),
                "raw_content": raw_content,
                "content_hash": content_hash,
                "extracted_urls": [],
                "extracted": {},
                "company_id": None,
                "company_name": None,
                "job_id": None,
                "job_title": None,
                "status": OpportunityStatus.NEW,
                "evaluation_status": EvaluationStatus.PENDING,
                "fit_score": None,
                "success_score": None,
                "overall_score": None,
                "recommendation": None,
                "evaluation": {},
                "missing_information": [],
                "application_path": {},
                "next_action": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        self._emit(OpportunityCreated(aggregate_id=stored["id"], opportunity_id=stored["id"], source=source))
        return self._present(stored), False

    # ── Read ──────────────────────────────────────────────────────

    def get_detail(self, opportunity_id: str) -> dict[str, Any]:
        row = self._get_or_raise(opportunity_id)
        evaluations = self._evaluations.list_for_opportunity(opportunity_id)
        return self._present(row, evaluations)

    def list(
        self,
        status: str | None = None,
        source: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        if status is not None and status not in OpportunityStatus.ALL:
            raise ValidationError(f"Invalid status '{status}'")
        if source is not None and source not in OpportunitySource.ALL:
            raise ValidationError(f"Invalid source '{source}'")
        items, total = self._opportunities.list(
            status=status, source=source, query=query, limit=limit, offset=offset
        )
        return [self._present(item) for item in items], total

    # ── Pipeline ──────────────────────────────────────────────────

    def process(self, opportunity_id: str) -> dict[str, Any]:
        """Run extract → resolve → evaluate synchronously."""
        row = self._get_or_raise(opportunity_id)
        row = self._extract(row)
        row = self._resolve(row)
        row = self._evaluate(row)
        return self.get_detail(opportunity_id)

    def reprocess(self, opportunity_id: str) -> dict[str, Any]:
        """Re-run the full pipeline (appends a new evaluation snapshot)."""
        return self.process(opportunity_id)

    # ── Manual corrections ────────────────────────────────────────

    def set_links(
        self,
        opportunity_id: str,
        job_id: str | None = None,
        company_id: str | None = None,
    ) -> dict[str, Any]:
        row = self._get_or_raise(opportunity_id)
        update: dict[str, Any] = {}
        if job_id is not None:
            if job_id == "":
                update["job_id"] = None
                update["job_title"] = None
            else:
                job = self._jobs.get_by_id(job_id) if self._jobs else None
                if not job:
                    raise NotFoundError(f"Job {job_id} not found")
                update["job_id"] = job_id
                update["job_title"] = job.get("title") or job.get("role")
        if company_id is not None:
            if company_id == "":
                update["company_id"] = None
                update["company_name"] = None
            else:
                company = self._companies.get_by_id(company_id) if self._companies else None
                if not company:
                    raise NotFoundError(f"Company {company_id} not found")
                update["company_id"] = company_id
                update["company_name"] = company.get("name")
        update["updated_at"] = _now_iso()
        stored = self._opportunities.update(opportunity_id, update) or row
        self._emit(
            OpportunityLinked(
                aggregate_id=opportunity_id,
                opportunity_id=opportunity_id,
                job_id=stored.get("job_id"),
                company_id=stored.get("company_id"),
            )
        )
        return self._present(stored)

    def set_status(self, opportunity_id: str, status: str) -> dict[str, Any]:
        row = self._get_or_raise(opportunity_id)
        if status not in OpportunityStatus.ALL:
            raise ValidationError(
                f"Invalid status '{status}'; allowed: {', '.join(OpportunityStatus.ALL)}"
            )
        allowed = OpportunityStatus.TRANSITIONS.get(row.get("status") or "", ())
        if status not in allowed:
            raise ValidationError(
                f"Cannot move opportunity from '{row.get('status')}' to '{status}'"
            )
        stored = self._opportunities.update(
            opportunity_id, {"status": status, "updated_at": _now_iso()}
        ) or row
        self._emit(
            OpportunityStatusChanged(
                aggregate_id=opportunity_id, opportunity_id=opportunity_id, status=status
            )
        )
        return self._present(stored)

    def delete(self, opportunity_id: str) -> bool:
        self._get_or_raise(opportunity_id)
        return bool(self._opportunities.delete(opportunity_id))

    # ── Extract ───────────────────────────────────────────────────

    def _extract(self, row: dict[str, Any]) -> dict[str, Any]:
        llm = self._llm or get_llm_service()
        prompt = build_opportunity_extract_prompt(
            source=row.get("source") or "",
            sender=row.get("sender"),
            subject=row.get("subject"),
            raw_content=row.get("raw_content") or "",
        )
        try:
            response = llm.generate_structured(
                prompt, schema=build_opportunity_extract_output_schema()
            )
            payload = _coerce_payload(response.content)
            extracted = OpportunityExtractOutput.model_validate(payload).model_dump()
        except PydanticValidationError as exc:
            raise OpportunityPipelineError(f"opportunity.extract schema-invalid: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — mapped to 502 at the router
            raise OpportunityPipelineError(f"opportunity.extract failed: {exc}") from exc

        llm_urls = [u for u in (extracted.get("job_urls") or []) if u]
        urls = _find_urls(row.get("raw_content") or "")
        for url in llm_urls:
            if url not in urls:
                urls.append(url)
        extracted["job_urls"] = urls

        company = extracted.get("company") or {}
        stored = self._opportunities.update(
            row["id"],
            {
                "extracted": extracted,
                "extracted_urls": urls,
                "status": OpportunityStatus.EXTRACTED,
                "updated_at": _now_iso(),
            },
        ) or row
        self._emit(
            OpportunityExtracted(
                aggregate_id=row["id"],
                opportunity_id=row["id"],
                has_role=bool(extracted.get("role_title")),
                has_company=bool(company.get("name")),
                url_count=len(urls),
            )
        )
        return stored

    # ── Resolve ───────────────────────────────────────────────────

    def _resolve(self, row: dict[str, Any]) -> dict[str, Any]:
        extracted = row.get("extracted") or {}
        update: dict[str, Any] = {}

        job_id, job_title = self._resolve_job(extracted.get("job_urls") or [])
        if job_id:
            update["job_id"] = job_id
            update["job_title"] = job_title

        company_id, company_name = self._resolve_company(extracted.get("company") or {})
        if company_id:
            update["company_id"] = company_id
            update["company_name"] = company_name
        elif (extracted.get("company") or {}).get("name"):
            update["company_name"] = str((extracted["company"] or {}).get("name")).strip() or None

        update["status"] = OpportunityStatus.ENRICHING
        update["updated_at"] = _now_iso()
        stored = self._opportunities.update(row["id"], update) or row
        if update.get("job_id") or update.get("company_id"):
            self._emit(
                OpportunityLinked(
                    aggregate_id=row["id"],
                    opportunity_id=row["id"],
                    job_id=stored.get("job_id"),
                    company_id=stored.get("company_id"),
                )
            )
        return stored

    def _resolve_job(self, urls: list[str]) -> tuple[str | None, str | None]:
        if not self._jobs:
            return None, None
        for url in urls:
            try:
                existing = find_duplicate_job(self._jobs, url)
            except Exception:  # noqa: BLE001 — resolution is best-effort
                existing = None
            if existing:
                return existing.get("id"), existing.get("title") or existing.get("role")
            getter = getattr(self._jobs, "get_by_url", None)
            if callable(getter):
                try:
                    exact = getter(url)
                except Exception:  # noqa: BLE001 — resolution is best-effort
                    exact = None
                if exact:
                    return exact.get("id"), exact.get("title") or exact.get("role")
        return None, None

    def _resolve_company(self, company: dict[str, Any]) -> tuple[str | None, str | None]:
        """Link an existing company on exact name/domain evidence only.

        Never creates a company — weak evidence stays unlinked with the
        extracted name kept as a display hint.
        """
        if not self._companies:
            return None, None
        name = str(company.get("name") or "").strip()
        website = str(company.get("website") or "").strip() or None
        if not name and not website:
            return None, None
        try:
            candidates = self._companies.list_for_matching()
        except Exception:  # noqa: BLE001 — resolution is best-effort
            return None, None
        norm = normalize_company_name(name) if name else ""
        domain = extract_domain(website) if website else None
        for candidate in candidates:
            if norm and normalize_company_name(candidate.get("name") or "") == norm:
                return candidate.get("id"), candidate.get("name")
            if domain:
                candidate_domain = candidate.get("domain") or extract_domain(candidate.get("website"))
                if candidate_domain == domain:
                    return candidate.get("id"), candidate.get("name")
        return None, None

    # ── Evaluate ──────────────────────────────────────────────────

    def _has_enough_to_score(self, extracted: dict[str, Any], profile: Any) -> bool:
        if not profile:
            return False
        return bool(
            extracted.get("role_title")
            or extracted.get("job_urls")
            or extracted.get("job_description_present")
        )

    def _evaluate(self, row: dict[str, Any]) -> dict[str, Any]:
        extracted = row.get("extracted") or {}
        profile = self._profiles.get_current_profile() if self._profiles else None

        if not self._has_enough_to_score(extracted, profile):
            return self._store_pending(row, extracted, profile)

        rules = self._rules.get_enabled_by_scopes(["SHARED", "JOB"]) if self._rules else []
        prompt = build_opportunity_evaluate_prompt(
            extracted_summary=json.dumps(extracted, indent=2, ensure_ascii=False),
            candidate_profile_text=build_candidate_profile_text(profile or {}),
            scoring_rules=build_scoring_rules_text(rules),
            linked_job_summary=self._job_summary(row.get("job_id")),
            linked_company_summary=self._company_summary(row.get("company_id")),
        )
        llm = self._llm or get_llm_service()
        try:
            response = llm.generate_structured(
                prompt, schema=build_opportunity_evaluate_output_schema()
            )
            payload = _coerce_payload(response.content)
            evaluated = OpportunityEvaluateOutput.model_validate(payload).model_dump()
        except PydanticValidationError as exc:
            raise OpportunityPipelineError(f"opportunity.evaluate schema-invalid: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — mapped to 502 at the router
            raise OpportunityPipelineError(f"opportunity.evaluate failed: {exc}") from exc

        fit, success = evaluated.get("fit"), evaluated.get("success")
        overall = calculate_overall_score(fit, success)
        if overall is None:
            return self._store_pending(row, extracted, profile, evaluated)

        recommendation = recommendation_for_overall(overall)
        path = self._application_path(row, extracted)
        status = (
            OpportunityStatus.READY_TO_APPLY
            if evaluated.get("enough_to_apply") and path["kind"] in ("job_url", "reply_sender")
            else OpportunityStatus.EVALUATED
        )
        evaluation = self._evaluation_dict(
            extracted, evaluated, fit, success, overall, recommendation, profile
        )
        missing = self._missing_information(extracted, evaluated)
        next_action = evaluated.get("recommended_next_action") or self._derived_next_action(
            path, extracted
        )
        stored = self._opportunities.update(
            row["id"],
            {
                "fit_score": fit,
                "success_score": success,
                "overall_score": overall,
                "recommendation": recommendation,
                "evaluation": evaluation,
                "evaluation_status": EvaluationStatus.COMPLETE,
                "missing_information": missing,
                "application_path": path,
                "next_action": next_action,
                "status": status,
                "updated_at": _now_iso(),
            },
        ) or row
        self._evaluations.create(
            {
                "opportunity_id": row["id"],
                "status": status,
                "evaluation_status": EvaluationStatus.COMPLETE,
                "fit_score": fit,
                "success_score": success,
                "overall_score": overall,
                "recommendation": recommendation,
                "snapshot": evaluation,
            }
        )
        self._emit(
            OpportunityEvaluated(
                aggregate_id=row["id"],
                opportunity_id=row["id"],
                status=status,
                overall_score=overall,
                recommendation=recommendation,
            )
        )
        return stored

    def _store_pending(
        self,
        row: dict[str, Any],
        extracted: dict[str, Any],
        profile: Any,
        evaluated: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        missing = self._missing_information(extracted, evaluated or {})
        if not profile:
            missing = ["Candidate profile is missing — import a resume or LinkedIn profile", *missing]
        path = self._application_path(row, extracted)
        stored = self._opportunities.update(
            row["id"],
            {
                "fit_score": None,
                "success_score": None,
                "overall_score": None,
                "recommendation": None,
                "evaluation": evaluated or {},
                "evaluation_status": EvaluationStatus.PENDING,
                "missing_information": missing,
                "application_path": path,
                "next_action": self._derived_next_action(path, extracted),
                "status": OpportunityStatus.NEEDS_INFO,
                "updated_at": _now_iso(),
            },
        ) or row
        self._emit(
            OpportunityEvaluated(
                aggregate_id=row["id"],
                opportunity_id=row["id"],
                status=OpportunityStatus.NEEDS_INFO,
                overall_score=None,
                recommendation=None,
            )
        )
        return stored

    # ── Evaluation helpers ────────────────────────────────────────

    def _evaluation_dict(
        self,
        extracted: dict[str, Any],
        evaluated: dict[str, Any],
        fit: int | None,
        success: int | None,
        overall: int | None,
        recommendation: str,
        profile: Any,
    ) -> dict[str, Any]:
        overlap = self._skill_overlap(extracted, profile or {})
        return {
            **evaluated,
            "fit": fit,
            "success": success,
            "overall": overall,
            "recommendation": recommendation,
            "skill_overlap": overlap,
            "prompt_version": OPPORTUNITY_EVALUATE_PROMPT_VERSION,
            "schema_version": OPPORTUNITY_EVALUATE_SCHEMA_VERSION,
        }

    def _skill_overlap(self, extracted: dict[str, Any], profile: Any) -> dict[str, list[str]]:
        """Compare required-skill names against the candidate's own skills.

        Read-only: skill rows are never created here (no ``resolve_skill``).
        """
        have = set()
        for skill in profile.get("skills") or []:
            name = str(skill.get("name") or "").strip().lower()
            if name:
                have.add(name)
        matched: list[str] = []
        missing: list[str] = []
        for skill in extracted.get("skills") or []:
            name = str(skill.get("name") or "").strip().lower()
            if not name or name in matched or name in missing:
                continue
            (matched if name in have else missing).append(name)
        return {"matched": matched, "missing_from_profile": missing}

    def _missing_information(
        self, extracted: dict[str, Any], evaluated: dict[str, Any]
    ) -> list[str]:
        missing: list[str] = []
        if not extracted.get("role_title"):
            missing.append("Role or job title")
        if not extracted.get("job_urls") and not extracted.get("job_description_present"):
            missing.append("Job description or posting link")
        location = extracted.get("location") or {}
        if not location.get("value"):
            missing.append("Job location")
        sponsorship = extracted.get("sponsorship") or {}
        if (sponsorship.get("state") or FieldState.UNKNOWN) == FieldState.UNKNOWN and not (
            sponsorship.get("mentions")
        ):
            missing.append("Visa sponsorship / work authorization")
        for item in evaluated.get("missing_requirements") or []:
            if item and item not in missing:
                missing.append(item)
        for item in evaluated.get("unknown_information") or []:
            if item and item not in missing:
                missing.append(item)
        for item in extracted.get("uncertainties") or []:
            if item and item not in missing:
                missing.append(item)
        return missing

    def _application_path(self, row: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
        """Derive the application path deterministically — never invented."""
        urls = extracted.get("job_urls") or []
        if urls:
            return {
                "kind": "job_url",
                "label": "Apply through the job posting",
                "url": urls[0],
                "alternatives": urls[1:],
            }
        sender_email = row.get("sender_email") or (extracted.get("recruiter") or {}).get("email")
        if sender_email:
            return {
                "kind": "reply_sender",
                "label": "Reply to the sender",
                "email": sender_email,
            }
        if row.get("sender"):
            return {"kind": "reply_sender", "label": "Reply to the sender"}
        return {"kind": "research", "label": "Research the opportunity first"}

    def _derived_next_action(self, path: dict[str, Any], extracted: dict[str, Any]) -> str:
        if path["kind"] == "job_url":
            return "Review the posting and apply through the job link"
        if path["kind"] == "reply_sender":
            if not extracted.get("job_description_present") and not extracted.get("job_urls"):
                return "Ask the sender for the full job description"
            location = extracted.get("location") or {}
            if not location.get("value"):
                return "Ask the sender about the location and work arrangement"
            return "Reply to the sender with your interest and key questions"
        return "Research the opportunity first — identify the company and role"

    def _job_summary(self, job_id: str | None) -> str:
        if not job_id or not self._jobs:
            return ""
        try:
            job = self._jobs.get_by_id(job_id)
        except Exception:  # noqa: BLE001 — context is best-effort
            return ""
        if not job:
            return ""
        parts = [
            f"Title: {job.get('title') or job.get('role')}",
            f"Company: {job.get('company')}",
            f"Location: {job.get('location')}",
            f"Scores: overall={job.get('overall_score')} fit={job.get('fit_score')} success={job.get('success_score')}",
        ]
        return "\n".join(parts)

    def _company_summary(self, company_id: str | None) -> str:
        if not company_id or not self._companies:
            return ""
        try:
            company = self._companies.get_by_id(company_id)
        except Exception:  # noqa: BLE001 — context is best-effort
            return ""
        if not company:
            return ""
        parts = [
            f"Name: {company.get('name')}",
            f"Industry: {company.get('industry')}",
            f"Location: {company.get('city')}, {company.get('country')}",
        ]
        return "\n".join(parts)

    # ── Plumbing ──────────────────────────────────────────────────

    def _get_or_raise(self, opportunity_id: str) -> dict[str, Any]:
        row = self._opportunities.get_by_id(opportunity_id)
        if not row:
            raise NotFoundError(f"Opportunity {opportunity_id} not found")
        return row

    def _present(
        self, row: dict[str, Any], evaluations: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        presented = dict(row)
        presented["title"] = _display_title(row)
        if evaluations is not None:
            presented["evaluations"] = evaluations
        return presented

    def _emit(self, event: Any) -> None:
        try:
            self.event_publisher.publish(event)
        except Exception:  # noqa: BLE001 — best-effort publishing
            pass


__all__ = ["OpportunityService", "OpportunityPipelineError"]
