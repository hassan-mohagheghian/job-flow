"""SQLAlchemy-based job repository implementation."""

from typing import Any
from datetime import datetime, UTC, timedelta

from sqlalchemy import func, or_, and_, case, cast, select, DateTime, asc as sa_asc, desc as sa_desc, true as sa_true, exc as sa_exc
from sqlalchemy.orm import Session, load_only

from jobs.domain.repositories.job_repository import IJobRepository
from jobs.domain.services.job_source_rules import display_name_for_domain, resolve_source
from jobs.infrastructure.models.job_model import JobModel, JobSourceModel
from jobs.infrastructure.models.job_analysis_model import JobAnalysisModel
from jobs.infrastructure.mappers import (
    JOB_LIST_FIELDS,
    job_model_to_dict,
    job_model_to_list_dict,
)

IntegrityError = sa_exc.IntegrityError

# Keyset-cursor sentinel encoding a NULL sort value. NULLs always sort last,
# so the cursor must distinguish a NULL boundary row from a non-NULL one.
NULL_CURSOR = "__null__"

# Multi-column tiebreak for score sorts so rows tied on the primary score are
# ordered deterministically, sharing the chosen asc/desc direction.
SCORE_SORT_COLUMNS = {
    "overall_score": [JobModel.overall_score, JobModel.success_score, JobModel.fit_score],
    "fit_score": [JobModel.fit_score, JobModel.overall_score, JobModel.success_score],
    "success_score": [JobModel.success_score, JobModel.overall_score, JobModel.fit_score],
}


def _created_date_range(key: str | None) -> tuple[datetime | None, datetime | None]:
    """Return (start, end) naive UTC datetimes for a created_at preset.

    ``created_at`` is a Text column that may hold either a Python-datetime
    ``str()`` form (`2026-08-17 11:01:16.034846`, space separator, the common
    fresh-insert case) or an ISO form with a `T` separator. Both are cast to a
    timestamp and compared against naive UTC datetimes, so the exact text
    layout never matters.
    """
    if not key:
        return None, None
    now = datetime.now(UTC).replace(tzinfo=None)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if key == "today":
        return start_of_day, None
    if key == "yesterday":
        return start_of_day - timedelta(days=1), start_of_day
    if key == "week":
        return now - timedelta(days=7), None
    if key == "month":
        return now - timedelta(days=30), None
    return None, None


class SQLAlchemyJobRepository(IJobRepository):
    """SQLAlchemy implementation of job repository."""

    def __init__(self, session: Session, user_id: str = ""):
        self._session = session
        self._user_id = user_id

    def _base_query(self):
        """Base query: user-scoped, non-deleted jobs."""
        q = self._session.query(JobModel).filter(JobModel.deleted == 0)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        return q

    def get_by_id(self, uuid: str) -> dict[str, Any] | None:
        q = self._session.query(JobModel).filter(JobModel.id == uuid)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        m = q.first()
        if not m:
            return None
        return job_model_to_dict(m)

    def get_by_ids(self, job_ids: list[str]) -> list[dict[str, Any]]:
        if not job_ids:
            return []
        q = self._session.query(JobModel).filter(JobModel.id.in_(job_ids), JobModel.deleted == 0)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        rows = q.all()
        return [{"id": m.id, "title": m.title, "location": m.location} for m in rows]

    def get_jobs_by_ids(self, job_ids: list[str]) -> list[dict[str, Any]]:
        if not job_ids:
            return []
        q = self._session.query(JobModel).filter(JobModel.id.in_(job_ids), JobModel.deleted == 0)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        rows = q.all()
        return [job_model_to_dict(m) for m in rows]

    def list_jobs(
        self,
        offset: int | None = None,
        limit: int | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query = self._base_query()

        if filters:
            if filters.get("filter_cities"):
                cities = [c.strip() for c in filters["filter_cities"].split(",") if c.strip()]
                if cities:
                    query = query.filter(JobModel.location.in_(cities))

            if filters.get("filter_companies"):
                companies = [c.strip() for c in filters["filter_companies"].split(",") if c.strip()]
                if companies:
                    query = query.filter(JobModel.company.in_(companies))

            if filters.get("filter_work_types"):
                wtypes = [w.strip() for w in filters["filter_work_types"].split(",") if w.strip()]
                if wtypes:
                    query = query.filter(
                        or_(*(JobModel.work_types.contains([wt]) for wt in wtypes))
                    )

            if filters.get("filter_employment_types"):
                etypes = [e.strip() for e in filters["filter_employment_types"].split(",") if e.strip()]
                if etypes:
                    query = query.filter(
                        or_(*(JobModel.employment_types.contains([et]) for et in etypes))
                    )

            if filters.get("filter_tech"):
                like_param = f'%{filters["filter_tech"]}%'
                query = query.filter(
                    or_(
                        JobModel.stack.contains(like_param),
                        JobModel.role.contains(like_param),
                        JobModel.company.contains(like_param),
                        JobModel.notes.contains(like_param),
                    )
                )

            if filters.get("filter_response_status"):
                statuses = [s.strip() for s in filters["filter_response_status"].split(",") if s.strip()]
                if statuses:
                    query = query.filter(JobModel.response_status.in_(statuses))

            if filters.get("filter_applied") == "true":
                query = query.filter(JobModel.apply_time.isnot(None))

            if filters.get("filter_status"):
                statuses = [s.strip() for s in filters["filter_status"].split(",") if s.strip()]
                if statuses:
                    query = query.filter(JobModel.status.in_(statuses))

        total = query.count()

        # Build ORDER BY
        allowed_sorts = {
            "created_at", "overall_score", "fit_score", "success_score",
            "company", "location",
            "posted_at", "applicants", "adv_at", "see_at", "apply_time", "response_time",
        }
        if sort_by not in allowed_sorts:
            sort_by = "created_at"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"

        sort_column = getattr(JobModel, sort_by, JobModel.created_at)
        if sort_dir == "desc":
            query = query.order_by(sort_column.desc().nulls_last())
        else:
            query = query.order_by(sort_column.asc().nulls_last())

        if offset is not None and limit is not None:
            query = query.offset(offset).limit(limit)

        rows = query.all()
        return [job_model_to_dict(r) for r in rows], total

    def get_stats(self) -> dict[str, int]:
        q = self._base_query()
        total = q.count()
        high_match = q.filter(JobModel.overall_score >= 80).count()
        remote = q.filter(JobModel.work_types.contains(["Remote"])).count()

        return {
            "total": total,
            "high_match": high_match,
            "apply_now": high_match,
            "remote": remote,
        }

    def count_created_by_day(self) -> list[dict[str, Any]]:
        """Return ``{date, count, apply_count}`` for non-deleted jobs, newest first.

        ``created_at`` is a Text ISO column, so the day key is the first 10
        characters (``substr``) grouped directly. ``apply_count`` counts the
        day's jobs the user has actually applied to — i.e. having an
        application at or past ``applied`` in the funnel (applied, interview,
        offer, accepted). The application join matches on job and user so
        counts stay user-scoped (at most one application per job, so the
        day ``count`` is unaffected).
        """
        from applications.infrastructure.models.application_model import ApplicationModel

        applied_statuses = ("applied", "interview", "offer", "accepted")
        day = func.substr(JobModel.created_at, 1, 10)
        apply_count = func.sum(
            case((ApplicationModel.status.in_(applied_statuses), 1), else_=0)
        ).label("apply_count")
        q = (
            self._base_query()
            .filter(JobModel.created_at.isnot(None))
            .outerjoin(
                ApplicationModel,
                (ApplicationModel.job_id == JobModel.id)
                & (ApplicationModel.user_id == JobModel.user_id),
            )
        )
        rows = (
            q.with_entities(day.label("date"), func.count(JobModel.id).label("count"), apply_count)
            .group_by(day)
            .order_by(day.desc())
            .all()
        )
        return [
            {"date": r.date, "count": r.count, "apply_count": int(r.apply_count or 0)}
            for r in rows
        ]

    def source_stats(self) -> dict[str, Any]:
        """Dashboard summary: totals + unknown bucket, in two lightweight queries.

        ``count_created_by_source`` is the single counting definition shared
        by stats/distribution/table (non-deleted, user-scoped jobs grouped by
        their joined source site).
        """
        by_source = self.count_created_by_source()
        unknown_jobs = int(self._base_query().filter(JobModel.source_site_id.is_(None)).count())
        total_jobs = int(self._base_query().count())
        return {
            "total_jobs": total_jobs,
            "total_sources": len(by_source),
            "active_sources": sum(1 for s in by_source if s["is_active"] and s["job_count"] > 0),
            "unknown_jobs": unknown_jobs,
        }

    def count_created_by_source(self) -> list[dict[str, Any]]:
        """Counts of non-deleted jobs grouped by ``job.job_sources``.

        Single GROUP BY query (join job_sources, count jobs); no N+1 and no
        per-source queries. Sources with zero live jobs are not returned.
        """
        rows = (
            self._base_query()
            .join(JobSourceModel, JobSourceModel.id == JobModel.source_site_id)
            .with_entities(
                JobSourceModel.id.label("id"),
                JobSourceModel.name.label("name"),
                JobSourceModel.canonical_url.label("canonical_url"),
                JobSourceModel.normalized_domain.label("domain"),
                JobSourceModel.is_active.label("is_active"),
                func.count(JobModel.id).label("job_count"),
                func.max(JobModel.created_at).label("last_activity"),
            )
            .group_by(JobSourceModel.id)
            .all()
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "canonical_url": r.canonical_url,
                "domain": r.domain,
                "is_active": bool(r.is_active),
                "job_count": int(r.job_count or 0),
                "last_activity": r.last_activity,
            }
            for r in rows
        ]

    def source_distribution(self, limit: int = 5) -> dict[str, Any]:
        """Top ``limit`` sources by count with the remainder folded into other."""
        items = sorted(self.count_created_by_source(), key=lambda s: -s["job_count"])
        return {
            "items": items[:limit],
            "other_count": sum(s["job_count"] for s in items[limit:]),
            "unknown_count": int(
                self._base_query().filter(JobModel.source_site_id.is_(None)).count()
            ),
        }

    def recommendation_distribution(self) -> dict[str, Any]:
        """Count of non-deleted jobs per analysis recommendation.

        Jobs are grouped by the `recommendation` column of their analysis
        row (left join, so jobs without analysis land in `none`). Only
        non-empty buckets are returned in `items`; `total` is always the
        full non-deleted job count for the user.
        """
        analysis_join = JobAnalysisModel.job_id == JobModel.id
        if self._user_id:
            analysis_join = analysis_join & (
                JobAnalysisModel.user_id == self._user_id
            )
        rows = (
            self._base_query()
            .outerjoin(JobAnalysisModel, analysis_join)
            .with_entities(
                JobAnalysisModel.recommendation,
                func.count(func.distinct(JobModel.id)).label("count"),
            )
            .group_by(JobAnalysisModel.recommendation)
            .all()
        )
        by_rec: dict[str, int] = {}
        for recommendation, count in rows:
            key = (recommendation or "").strip() or "none"
            # Defensive: unexpected values (e.g. legacy labels) fold into none.
            if key not in ("apply", "consider", "skip"):
                key = "none"
            by_rec[key] = by_rec.get(key, 0) + int(count)
        return {
            "items": [
                {"recommendation": key, "count": count}
                for key, count in sorted(
                    by_rec.items(), key=lambda kv: (-kv[1], kv[0])
                )
                if count
            ],
            "total": int(self._base_query().count()),
        }

    def application_status_distribution(self) -> dict[str, Any]:
        """Count of non-deleted jobs per tracking/application status.

        A left join to the user's application row means jobs with no
        application land in ``not_applied``; jobs with an application are
        grouped under its status. Only non-empty buckets are returned,
        ``not_applied`` first and then the canonical funnel order. ``total`` is
        every non-deleted job for the user, which the Dashboard chart uses as
        its percentage denominator.
        """
        from applications.domain.entities.application import ApplicationStatus
        from applications.infrastructure.models.application_model import (
            ApplicationModel,
        )

        application_join = ApplicationModel.job_id == JobModel.id
        if self._user_id:
            application_join = application_join & (
                ApplicationModel.user_id == JobModel.user_id
            )
        rows = (
            self._base_query()
            .outerjoin(ApplicationModel, application_join)
            .with_entities(
                ApplicationModel.status,
                func.count(func.distinct(JobModel.id)).label("count"),
            )
            .group_by(ApplicationModel.status)
            .all()
        )

        counts: dict[str, int] = {}
        for status, count in rows:
            key = str(status) if status else "not_applied"
            counts[key] = counts.get(key, 0) + int(count)

        items = []
        if counts.get("not_applied"):
            items.append({"status": "not_applied", "count": counts["not_applied"]})
        known = [s for s in ApplicationStatus.ALL if counts.get(s)]
        unknown = sorted(
            s for s in counts if s not in ApplicationStatus.ALL and s != "not_applied"
        )
        items.extend(
            {"status": status, "count": counts[status]}
            for status in (*known, *unknown)
            if counts[status] > 0
        )
        return {"items": items, "total": int(self._base_query().count())}

    def list_sources(
        self,
        page: int = 1,
        page_size: int = 10,
        query: str = "",
        sort: str = "job_count",
        order: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """Paginated source rows for the dashboard table.

        Includes sources with zero live jobs (unlike the aggregates). Search,
        sort and pagination happen in SQL; no per-source count queries.
        """
        base = (
            self._session.query(JobSourceModel)
            .outerjoin(
                JobModel,
                (JobModel.source_site_id == JobSourceModel.id)
                & (JobModel.deleted == 0)
                & self._user_scope_clause(),
            )
        )
        if self._user_id:
            base = base.filter(JobSourceModel.user_id == self._user_id)
        if query:
            like = f"{query.lower()}%"
            base = base.filter(
                or_(
                    func.lower(func.coalesce(JobSourceModel.name, "")).like(like),
                    func.lower(JobSourceModel.normalized_domain).like(like),
                )
            )

        total = (
            base.with_entities(func.count(func.distinct(JobSourceModel.id)))
            .order_by(None)
            .scalar()
            or 0
        )

        job_count_exp = func.count(
            case((JobModel.id.isnot(None), JobModel.id))
        ).label("job_count_exp")
        q = base.with_entities(
            JobSourceModel,
            job_count_exp,
            func.max(JobModel.created_at).label("last_activity"),
        ).group_by(JobSourceModel.id)

        sort_column = {
            "job_count": job_count_exp,
            "name": JobSourceModel.name,
            "last_activity": func.max(JobModel.created_at),
        }[sort]
        direction = sa_desc if order == "desc" else sa_asc
        total_pages = max(1, -(-total // page_size))
        page = max(1, min(page, total_pages))
        ordering = direction(sort_column)
        if order == "desc":
            ordering = ordering.nulls_last()
        rows = (
            q.order_by(ordering, JobSourceModel.normalized_domain.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            {
                "id": site.id,
                "name": site.name,
                "canonical_url": site.canonical_url,
                "domain": site.normalized_domain,
                "is_active": bool(site.is_active),
                "job_count": int(count or 0),
                "last_activity": last_activity,
            }
            for site, count, last_activity in rows
        ]
        return items, int(total)

    def _user_scope_clause(self):
        """User matching for join conditions (mirrors _base_query scoping)."""
        return JobModel.user_id == self._user_id if self._user_id else sa_true()

    def delete_by_id(self, uuid: str) -> bool:
        """Hard-delete a job by UUID.

        Child rows in the same schema (``job_analysis``, ``summaries``,
        ``job_companies``) are removed by the database through
        ``ON DELETE CASCADE`` FKs. Processing executions are handled by the
        caller via the processing execution repository.
        """
        q = self._session.query(JobModel).filter(JobModel.id == uuid)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        model = q.first()
        if not model:
            return False
        self._session.delete(model)
        self._session.commit()
        return True

    def mark_deleted(self, job_id: str) -> None:
        q = self._session.query(JobModel).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        q.update({"deleted": 1, "updated_at": datetime.now(UTC).isoformat()})
        self._session.commit()

    def mark_rescoring(self, job_id: str, rescoring: bool = True) -> None:
        q = self._session.query(JobModel).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        q.update({"rescoring": int(rescoring), "updated_at": datetime.now(UTC).isoformat()})
        self._session.commit()

    def get_all_active(self) -> list[dict[str, Any]]:
        rows = self._base_query().all()
        return [{"id": r.id, "url": r.url, "company": r.company} for r in rows]

    # ── Extended methods for services ───────────────────────────────

    # Editable job fields for the Edit Job feature (whitelist).
    EDITABLE_FIELDS = {
        "title",
        "role",
        "company",
        "location",
        "url",
        "work_types",
        "employment_types",
        "visa",
        "salary",
        "description",
        "notes",
        "links",
    }

    def update_by_id(self, uuid: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Partially update a job's core data by UUID.

        Only whitelisted fields are applied; keys not present in ``data`` are
        left unchanged. ``None`` values are ignored (treated as "not provided").
        Returns the updated job dict, or ``None`` if the job does not exist.
        """
        updates = {k: v for k, v in data.items() if k in self.EDITABLE_FIELDS and v is not None}
        q = self._session.query(JobModel).filter(JobModel.id == uuid)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        model = q.first()
        if not model:
            return None
        if updates:
            model.updated_at = datetime.now(UTC).replace(tzinfo=None)
            for k, v in updates.items():
                setattr(model, k, v)
            self._session.commit()
            self._session.refresh(model)
        return job_model_to_dict(model)

    def create_job(self, url: str, title: str | None = None, notes: str = "[]", links: str = "[]", source: str = "api") -> dict[str, Any]:
        model = JobModel(
            url=url,
            title=title,
            links=links,
            notes=notes,
            status="imported",
            source=source,
            user_id=self._user_id,
        )
        resolved = resolve_source(url)
        model.source_site_id = (
            self._get_or_create_source_site(resolved).id if resolved else None
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return job_model_to_dict(model)

    def _get_or_create_source_site(self, normalized_domain: str) -> JobSourceModel:
        """Reuse-or-create the user's source row for a canonical domain.

        Same-session get-or-create; on a concurrent insert collision the
        unique index decide the winner and we take the persisted row.
        """
        existing = (
            self._session.query(JobSourceModel)
            .filter(
                JobSourceModel.user_id == self._user_id,
                JobSourceModel.normalized_domain == normalized_domain,
            )
            .first()
        )
        if existing:
            return existing

        site = JobSourceModel(
            user_id=self._user_id,
            name=display_name_for_domain(normalized_domain),
            canonical_url=f"https://{normalized_domain}",
            normalized_domain=normalized_domain,
            is_active=1,
        )
        self._session.add(site)
        try:
            self._session.flush()
            return site
        except IntegrityError:
            self._session.rollback()
            return (
                self._session.query(JobSourceModel)
                .filter(
                    JobSourceModel.user_id == self._user_id,
                    JobSourceModel.normalized_domain == normalized_domain,
                )
                .first()
            )

    def get_by_url(self, url: str) -> dict[str, Any] | None:
        q = self._session.query(JobModel).filter(JobModel.url == url)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        m = q.first()
        return job_model_to_dict(m) if m else None

    def get_id_by_url(self, url: str) -> str | None:
        q = self._session.query(JobModel.id).filter(JobModel.url == url)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        m = q.first()
        return m[0] if m else None

    def get_by_url_fragment(self, fragment: str) -> dict[str, Any] | None:
        q = self._session.query(JobModel).filter(
            JobModel.deleted == 0, JobModel.url.contains(fragment)
        )
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        m = q.first()
        return job_model_to_dict(m) if m else None

    def upsert(self, data: dict[str, Any]) -> dict[str, Any]:
        job_id = data.get("id") or data.get("url")
        q = self._session.query(JobModel).filter(
            or_(JobModel.id == job_id, JobModel.url == job_id)
        )
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        existing = q.first() if job_id else None
        if existing:
            existing.updated_at = datetime.now(UTC).isoformat()
            for k, v in data.items():
                if hasattr(existing, k) and k != "id":
                    setattr(existing, k, v)
            self._session.commit()
            self._session.refresh(existing)
            return job_model_to_dict(existing)
        m = JobModel(**{k: v for k, v in data.items() if hasattr(JobModel, k)})
        if self._user_id and not m.user_id:
            m.user_id = self._user_id
        self._session.add(m)
        self._session.commit()
        self._session.refresh(m)
        return job_model_to_dict(m)

    def update_fields(self, item_id: str, **fields) -> bool:
        fields.setdefault("updated_at", datetime.now(UTC).isoformat())
        valid_fields = {k: v for k, v in fields.items() if hasattr(JobModel, k)}
        q = self._session.query(JobModel).filter(JobModel.id == item_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        q.update(valid_fields)
        self._session.commit()
        return True

    def set_company(self, job_id: str, company_id: str | None, company_name: str | None = None) -> bool:
        """Link a job to a company (or unlink it with ``company_id=None``).

        When linking, ``company_name`` is also written so the display name
        matches the company's canonical name.
        """
        fields: dict[str, Any] = {"company_id": company_id}
        if company_name is not None:
            fields["company"] = company_name
        return self.update_fields(job_id, **fields)

    def update_workflow_log(self, job_id: str, log_json: str) -> bool:
        q = self._session.query(JobModel).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        q.update({"workflow_log": log_json, "updated_at": datetime.now(UTC).isoformat()})
        self._session.commit()
        return True

    def set_deleted_by_url(self, url: str, exclude_id: str | None = None) -> int:
        q = self._session.query(JobModel).filter(JobModel.url == url)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        if exclude_id is not None:
            q = q.filter(JobModel.id != exclude_id)
        count = q.update({"deleted": 1, "updated_at": datetime.now(UTC).isoformat()})
        self._session.commit()
        return count

    def delete_all_active(self) -> int:
        count = self._base_query().delete(synchronize_session=False)
        self._session.commit()
        return count

    # ── Queue management methods (consolidated from pending repo) ──

    EXCLUDED_STATUSES = {"processed"}

    def list_pending(self) -> list[dict[str, Any]]:
        rows = self._base_query().filter(
            ~JobModel.status.in_(self.EXCLUDED_STATUSES)
        ).order_by(JobModel.created_at.desc()).all()
        return [job_model_to_dict(r) for r in rows]

    def count_pending(self) -> int:
        return self._base_query().filter(
            ~JobModel.status.in_(self.EXCLUDED_STATUSES)
        ).count()

    def get_max_queue_order(self) -> int:
        result = self._session.query(func.max(JobModel.queue_order)).scalar()
        return result or 0

    def mark_processing_as_waiting(self) -> int:
        count = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status.in_(self.ACTIVE_STATUSES)
        ).update({"status": "pending", "updated_at": datetime.now(UTC).isoformat()})
        self._session.commit()
        return count

    def reset_processing_orphans(self) -> int:
        count = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status.in_(self.ACTIVE_STATUSES)
        ).update({"status": "created", "updated_at": datetime.now(UTC).isoformat()})
        self._session.commit()
        return count

    def get_queued_items(self) -> list[dict[str, Any]]:
        rows = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == "queued"
        ).order_by(JobModel.queue_order.asc(), JobModel.id.asc()).all()
        return [job_model_to_dict(r) for r in rows]

    def reset_steps(self, item_id: str) -> bool:
        updates = {
            "error": None,
            "workflow_log": "[]",
            "current_node": None,
            "retry_count": 0,
            "failure_reason": None,
            "status": "created",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._session.query(JobModel).filter(JobModel.id == item_id).update(updates)
        self._session.commit()
        return True

    def get_all_for_stream(self) -> list[dict[str, Any]]:
        rows = self._session.query(JobModel).order_by(JobModel.created_at.desc()).all()
        return [job_model_to_dict(r) for r in rows]

    def create_pending_job(self, url: str, source: str, company: str, status: str = "created") -> dict[str, Any]:
        model = JobModel(url=url, source=source, company=company, status=status, user_id=self._user_id)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return job_model_to_dict(model)

    def soft_delete(self, item_id: str) -> bool:
        m = self._session.query(JobModel).filter(JobModel.id == item_id).first()
        if m:
            m.deleted = 1
            m.updated_at = datetime.now(UTC).isoformat()
            self._session.commit()
            return True
        return False

    def get_company_id(self, job_id: str) -> str | None:
        m = self._session.query(JobModel.company_id).filter(JobModel.id == job_id).first()
        return m[0] if m else None

    # ── Lifecycle methods ───────────────────────────────────────────

    ACTIVE_STATUSES = {'processing'}

    def get_pending_count(self) -> int:
        return self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == 'pending',
        ).count()

    def list_by_status(self, status: str) -> list[dict[str, Any]]:
        rows = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == status,
        ).order_by(JobModel.created_at.desc()).all()
        return [job_model_to_dict(r) for r in rows]

    def get_processing_count(self) -> int:
        return self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status.in_(self.ACTIVE_STATUSES),
        ).count()

    def get_queued_count(self) -> int:
        return self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == 'queued',
        ).count()

    def update_status(self, job_id: str, status: str, **extra: Any) -> bool:
        extra.setdefault("updated_at", datetime.now(UTC).isoformat())
        fields = {'status': status, **extra}
        self._session.query(JobModel).filter(JobModel.id == job_id).update(fields)
        self._session.commit()
        return True

    def pick_queued_item(self) -> dict[str, Any] | None:
        model = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == 'queued',
        ).order_by(
            JobModel.queue_order.asc(),
            JobModel.created_at.asc(),
        ).first()
        if model:
            model.status = 'processing'
            model.updated_at = datetime.now(UTC).isoformat()
            self._session.commit()
            self._session.refresh(model)
            return job_model_to_dict(model)
        return None

    def get_processing_items(self) -> list[dict[str, Any]]:
        rows = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status.in_(self.ACTIVE_STATUSES),
        ).all()
        return [job_model_to_dict(r) for r in rows]

    def get_dashboard_counts(self) -> dict[str, int]:
        base = self._base_query()
        total = base.count() or 0
        high = base.filter(JobModel.overall_score >= 80).count() or 0
        return {"jobs_total": total, "jobs_high_match": high}

    def get_location_data(self) -> list[dict[str, Any]]:
        rows = self._base_query().with_entities(JobModel.location).all()
        return [{"location": r[0]} for r in rows]

    def get_company_id_by_id(self, job_id: str) -> str | None:
        q = self._session.query(JobModel.company_id).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        m = q.first()
        return m[0] if m else None

    def get_jobs_by_company_id(self, company_id: str) -> list[dict[str, Any]]:
        q = self._base_query().filter(JobModel.company_id == company_id)
        rows = q.order_by(JobModel.created_at.desc()).all()
        return [job_model_to_dict(r) for r in rows]

    def reassign_company(self, from_company_id: str, to_company_id: str) -> bool:
        """Re-point all non-deleted jobs linked to ``from_company_id`` to ``to_company_id``."""
        q = self._base_query().filter(JobModel.company_id == from_company_id)
        q.update(
            {"company_id": to_company_id, "updated_at": datetime.now(UTC).isoformat()},
            synchronize_session=False,
        )
        self._session.commit()
        return True

    def search_jobs(
        self,
        page: int = 1,
        page_size: int = 10,
        query: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
        processing_status: str | None = None,
        company_id: str | None = None,
        remote: bool | None = None,
        visa: bool | None = None,
        overall_score_min: int | None = None,
        overall_score_max: int | None = None,
        fit_score_min: int | None = None,
        fit_score_max: int | None = None,
        success_score_min: int | None = None,
        success_score_max: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        q = self._session.query(JobModel).filter(JobModel.deleted == 0)

        if query:
            like = f"%{query}%"
            q = q.filter(
                or_(
                    JobModel.title.ilike(like),
                    JobModel.company.ilike(like),
                    JobModel.location.ilike(like),
                    JobModel.role.ilike(like),
                    JobModel.url.ilike(like),
                )
            )

        if processing_status:
            q = q.filter(JobModel.status == processing_status)

        if company_id is not None:
            q = q.filter(JobModel.company_id == company_id)

        if remote is not None:
            if remote:
                q = q.filter(JobModel.work_types.contains(["Remote"]))
            else:
                q = q.filter(~JobModel.work_types.contains(["Remote"]))

        if visa is not None:
            if visa:
                q = q.filter(JobModel.visa.isnot(None), JobModel.visa != "")
            else:
                q = q.filter(
                    or_(JobModel.visa.is_(None), JobModel.visa == "")
                )

        if overall_score_min is not None:
            q = q.filter(JobModel.overall_score >= overall_score_min)
        if overall_score_max is not None:
            q = q.filter(JobModel.overall_score <= overall_score_max)
        if fit_score_min is not None:
            q = q.filter(JobModel.fit_score >= fit_score_min)
        if fit_score_max is not None:
            q = q.filter(JobModel.fit_score <= fit_score_max)
        if success_score_min is not None:
            q = q.filter(JobModel.success_score >= success_score_min)
        if success_score_max is not None:
            q = q.filter(JobModel.success_score <= success_score_max)

        total = q.count()

        sort_map = {
            "created_at": JobModel.created_at,
            "updated_at": JobModel.updated_at,
            "title": JobModel.title,
            "company": JobModel.company,
            "status": JobModel.status,
            "overall_score": JobModel.overall_score,
            "fit_score": JobModel.fit_score,
            "success_score": JobModel.success_score,
        }
        sort_column = sort_map.get(sort, JobModel.created_at)
        sort_columns = SCORE_SORT_COLUMNS.get(sort, [sort_column])
        if order == "asc":
            q = q.order_by(*(c.asc().nulls_last() for c in sort_columns))
        else:
            q = q.order_by(*(c.desc().nulls_last() for c in sort_columns))

        offset = (page - 1) * page_size
        q = q.offset(offset).limit(page_size)

        rows = q.all()
        return [job_model_to_dict(r) for r in rows], total

    def search_jobs_cursor(
        self,
        cursor: str | None = None,
        page_size: int = 10,
        page: int = 1,
        query: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
        job_ids: list[str] | None = None,
        exclude_job_ids: list[str] | None = None,
        status_lookup: dict[str, str] | None = None,
        company_id: str | None = None,
        location: str | None = None,
        remote: bool | None = None,
        visa: bool | None = None,
        overall_score_min: int | None = None,
        overall_score_max: int | None = None,
        fit_score_min: int | None = None,
        fit_score_max: int | None = None,
        success_score_min: int | None = None,
        success_score_max: int | None = None,
        pinned: bool | None = None,
        dismissed: bool | None = None,
        tags: list[str] | None = None,
        recommendation: list[str] | None = None,
        created_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, str | None, bool]:
        q = self._base_query().options(
            load_only(*(getattr(JobModel, field) for field in JOB_LIST_FIELDS))
        )

        if query:
            like = f"%{query}%"
            q = q.filter(
                or_(
                    JobModel.title.ilike(like),
                    JobModel.company.ilike(like),
                    JobModel.location.ilike(like),
                    JobModel.role.ilike(like),
                    JobModel.url.ilike(like),
                )
            )

        if job_ids is not None:
            q = q.filter(JobModel.id.in_(job_ids))

        if exclude_job_ids:
            q = q.filter(~JobModel.id.in_(exclude_job_ids))

        if company_id is not None:
            q = q.filter(JobModel.company_id == company_id)

        if location:
            q = q.filter(JobModel.location.ilike(f"%{location}%"))

        if remote is not None:
            if remote:
                q = q.filter(JobModel.work_types.contains(["Remote"]))
            else:
                q = q.filter(~JobModel.work_types.contains(["Remote"]))

        if visa is not None:
            if visa:
                q = q.filter(JobModel.visa.isnot(None), JobModel.visa != "")
            else:
                q = q.filter(
                    or_(JobModel.visa.is_(None), JobModel.visa == "")
                )

        if overall_score_min is not None:
            q = q.filter(JobModel.overall_score >= overall_score_min)
        if overall_score_max is not None:
            q = q.filter(JobModel.overall_score <= overall_score_max)
        if fit_score_min is not None:
            q = q.filter(JobModel.fit_score >= fit_score_min)
        if fit_score_max is not None:
            q = q.filter(JobModel.fit_score <= fit_score_max)
        if success_score_min is not None:
            q = q.filter(JobModel.success_score >= success_score_min)
        if success_score_max is not None:
            q = q.filter(JobModel.success_score <= success_score_max)

        if pinned is not None:
            q = q.filter(JobModel.pinned == (1 if pinned else 0))

        if dismissed is not None:
            q = q.filter(JobModel.dismissed == (1 if dismissed else 0))

        if tags:
            for tag in tags:
                q = q.filter(JobModel.tags.contains([tag]))

        if recommendation:
            q = q.filter(JobModel.id.in_(
                select(JobAnalysisModel.job_id).where(
                    JobAnalysisModel.recommendation.in_(recommendation)
                )
            ))

        created = cast(JobModel.created_at, DateTime)
        created_start, created_end = _created_date_range(created_date)
        if created_start is not None:
            q = q.filter(created >= created_start)
        if created_end is not None:
            q = q.filter(created < created_end)

        total = q.count()

        sort_map = {
            "created_at": JobModel.created_at,
            "updated_at": JobModel.updated_at,
            "title": JobModel.title,
            "company": JobModel.company,
            "status": JobModel.status,
            "overall_score": JobModel.overall_score,
            "fit_score": JobModel.fit_score,
            "success_score": JobModel.success_score,
        }
        sort_column = sort_map.get(sort, JobModel.created_at)
        multi = sort in SCORE_SORT_COLUMNS
        sort_columns = SCORE_SORT_COLUMNS.get(sort, [sort_column])

        # Status sort orders by the same execution status each row displays
        # (the latest execution), grouping rows by status. Unprocessed rows
        # (no execution, absent from ``status_lookup``) always sort last, in
        # both directions — achieved with a direction-aware sentinel for the
        # COALESCE (unprocessed rank = max in asc, = -1 in desc).
        status_mode = sort == "status" and status_lookup is not None
        if status_mode:
            statuses = sorted(set(status_lookup.values()))
            rank_of = {status: i for i, status in enumerate(statuses)}
            grouped: dict[str, list[str]] = {}
            for job_id, status in status_lookup.items():
                grouped.setdefault(status, []).append(job_id)
            status_rank = case(
                *[
                    (JobModel.id.in_(ids), rank_of[status])
                    for status, ids in grouped.items()
                ]
            )
            sentinel = len(statuses) if order == "asc" else -1
            rank_expr = func.coalesce(status_rank, sentinel)
        else:
            rank_expr = None

        if cursor:
            if status_mode:
                try:
                    cur_rank, cur_id = cursor.split(":", 1)
                    cur_rank = int(cur_rank)
                except (ValueError, TypeError):
                    cur_rank = cur_id = None
                if cur_rank is not None:
                    if order == "desc":
                        q = q.filter(
                            or_(
                                rank_expr < cur_rank,
                                and_(rank_expr == cur_rank, JobModel.id < cur_id),
                            )
                        )
                    else:
                        q = q.filter(
                            or_(
                                rank_expr > cur_rank,
                                and_(rank_expr == cur_rank, JobModel.id > cur_id),
                            )
                        )
            else:
                if multi:
                    # Multi-column keyset: cursor format ``v1|v2|v3|id``, one
                    # value per tiebreak column plus the id, all NULLS LAST.
                    # Effective value uses a direction-aware sentinel for NULL
                    # (coalesced to -1 in desc, to a large value in asc) so NULL
                    # columns sort last; ties resolve lexicographically then by id.
                    parts = cursor.split("|")
                    cur_id = parts[3] if len(parts) == 4 else None
                    sentinel = -1 if order == "desc" else 10_000
                    cur_eff = []
                    for i, col in enumerate(sort_columns):
                        raw = parts[i] if len(parts) > i else None
                        if raw == NULL_CURSOR or raw is None:
                            cur_eff.append(sentinel)
                        else:
                            cur_eff.append(cast(raw, col.type))
                    if cur_id is not None:
                        eff = [func.coalesce(c, sentinel) for c in sort_columns]
                        cmp_op = lambda a, b: a < b if order == "desc" else a > b  # noqa: E731
                        tie_op = JobModel.id < cur_id if order == "desc" else JobModel.id > cur_id
                        conditions = [
                            cmp_op(eff[0], cur_eff[0]),
                            and_(
                                eff[0] == cur_eff[0],
                                cmp_op(eff[1], cur_eff[1]),
                            ),
                            and_(
                                eff[0] == cur_eff[0],
                                eff[1] == cur_eff[1],
                                cmp_op(eff[2], cur_eff[2]),
                            ),
                            and_(
                                eff[0] == cur_eff[0],
                                eff[1] == cur_eff[1],
                                eff[2] == cur_eff[2],
                                tie_op,
                            ),
                        ]
                        q = q.filter(or_(*conditions))
                else:
                    # NULLS LAST is the policy for every sort, so keyset
                    # pagination must be NULL-aware. Cursor format: ``value|id``
                    # (a legacy single-value cursor without ``|`` is tolerated).
                    # While the boundary row is non-NULL the next page is every
                    # row strictly below it plus all NULL rows (they sort last);
                    # once the boundary row is NULL, remaining pages walk the
                    # NULL tail by id alone.
                    cur_value, cur_id = cursor, None
                    if "|" in cursor:
                        cur_value, cur_id = cursor.rsplit("|", 1)
                    if cur_value == NULL_CURSOR and cur_id is not None:
                        if order == "desc":
                            q = q.filter(and_(sort_column.is_(None), JobModel.id < cur_id))
                        else:
                            q = q.filter(and_(sort_column.is_(None), JobModel.id > cur_id))
                    else:
                        cur = cast(cur_value, sort_column.type)
                        cmp = sort_column < cur if order == "desc" else sort_column > cur
                        if cur_id is not None:
                            tiebreak = JobModel.id < cur_id if order == "desc" else JobModel.id > cur_id
                            q = q.filter(
                                or_(cmp, and_(sort_column == cur, tiebreak), sort_column.is_(None))
                            )
                        else:
                            q = q.filter(or_(cmp, sort_column.is_(None)))

        if status_mode:
            if order == "asc":
                q = q.order_by(rank_expr.asc(), JobModel.id.asc())
            else:
                q = q.order_by(rank_expr.desc(), JobModel.id.desc())
        elif order == "asc":
            q = q.order_by(
                *(c.asc().nulls_last() for c in sort_columns),
                JobModel.id.asc(),
            )
        else:
            q = q.order_by(
                *(c.desc().nulls_last() for c in sort_columns),
                JobModel.id.desc(),
            )

        q = q.limit(page_size + 1)
        if cursor is None and page and page > 1:
            q = q.offset((page - 1) * page_size)

        rows = q.all()
        has_more = len(rows) > page_size
        items = [job_model_to_list_dict(r) for r in rows[:page_size]]
        if len(rows) >= page_size:
            boundary = rows[page_size - 1]
            if status_mode:
                boundary_status = status_lookup.get(boundary.id)
                boundary_rank = (
                    sentinel
                    if boundary_status is None
                    else rank_of.get(boundary_status, sentinel)
                )
                next_cursor = f"{boundary_rank}:{boundary.id}"
            else:
                if multi:
                    vals = [getattr(boundary, col.key) for col in sort_columns]
                    encoded = [
                        NULL_CURSOR if v is None else str(v) for v in vals
                    ]
                    next_cursor = "|".join(encoded + [boundary.id])
                else:
                    boundary_value = getattr(boundary, sort, boundary.updated_at)
                    value = NULL_CURSOR if boundary_value is None else str(boundary_value)
                    next_cursor = f"{value}|{boundary.id}"
        else:
            next_cursor = None

        return items, total, next_cursor, has_more

    def set_pinned(self, job_id: str, pinned: bool) -> bool:
        """Set or clear the pinned flag on a job. Returns True if the job exists."""
        q = self._session.query(JobModel).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        model = q.first()
        if not model:
            return False
        model.pinned = 1 if pinned else 0
        model.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.commit()
        return True

    def set_dismissed(self, job_id: str, dismissed: bool) -> bool:
        """Set or clear the dismissed flag on a job. Returns True if the job exists."""
        q = self._session.query(JobModel).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        model = q.first()
        if not model:
            return False
        model.dismissed = 1 if dismissed else 0
        model.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.commit()
        return True

    def set_tags(self, job_id: str, tags: list[str]) -> bool:
        """Set the tags on a job. Returns True if the job exists."""
        q = self._session.query(JobModel).filter(JobModel.id == job_id)
        if self._user_id:
            q = q.filter(JobModel.user_id == self._user_id)
        model = q.first()
        if not model:
            return False
        model.tags = tags
        model.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.commit()
        return True

    def score_rank(self, job_id: str) -> int | None:
        """Competition rank of a single job — delegated to ``ranks_by_ids`` so
        it uses the exact same ``RANK()`` window as the list: a rank computed
        over the full non-deleted job list sorted by overall, then success, then
        fit (each descending, NULLS LAST). Jobs with identical scores share a
        rank. Returns None when the job does not exist."""
        return self.ranks_by_ids([job_id]).get(job_id)

    def ranks_by_ids(self, job_ids: list[str]) -> dict[str, int]:
        """Competition ranks (``RANK()``) for a set of jobs. Ranks are computed
        over the user's non-deleted job list (sorted by overall, then success,
        then fit, each descending, NULLS LAST) in a subquery, so each job's rank
        is absolute (independent of the requested subset / current list sort).
        Jobs with identical scores share a rank; the next distinct rank skips
        ahead."""
        if not job_ids:
            return {}
        rank_expr = func.rank().over(
            order_by=[
                func.coalesce(JobModel.overall_score, -1).desc(),
                func.coalesce(JobModel.success_score, -1).desc(),
                func.coalesce(JobModel.fit_score, -1).desc(),
            ]
        )
        user_filter = [JobModel.deleted == 0]
        if self._user_id:
            user_filter.append(JobModel.user_id == self._user_id)
        ranked = (
            select(JobModel.id, rank_expr.label("rn"))
            .where(JobModel.id.in_(
                select(JobModel.id).where(*user_filter)
            ))
            .subquery()
        )
        rows = (
            self._session.query(ranked.c.id, ranked.c.rn)
            .filter(ranked.c.id.in_(job_ids))
            .all()
        )
        return {row.id: row.rn for row in rows}
