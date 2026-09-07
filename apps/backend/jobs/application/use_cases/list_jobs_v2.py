"""ListJobsV2 use case — new jobs list for the row-based UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobs.domain.repositories.job_repository import IJobRepository


@dataclass
class ListJobsV2Request:
    page: int = 1
    page_size: int = 25
    cursor: str | None = None
    query: str | None = None
    sort: str = "created_at"
    order: str = "desc"
    job_ids: list[str] | None = None
    exclude_job_ids: list[str] | None = None
    status_lookup: dict[str, str] | None = None
    company_id: str | None = None
    location: str | None = None
    remote: bool | None = None
    visa: bool | None = None
    overall_score_min: int | None = None
    overall_score_max: int | None = None
    fit_score_min: int | None = None
    fit_score_max: int | None = None
    success_score_min: int | None = None
    success_score_max: int | None = None
    pinned: bool | None = None
    dismissed: bool | None = None
    tags: list[str] | None = None
    recommendation: list[str] | None = None
    created_date: str | None = None


@dataclass
class ListJobsV2Response:
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    next_cursor: str | None = None
    has_more: bool = False


class ListJobsV2UseCase:
    def __init__(self, job_repository: IJobRepository):
        self._job_repository = job_repository

    def execute(self, request: ListJobsV2Request) -> ListJobsV2Response:
        items, total, next_cursor, has_more = self._job_repository.search_jobs_cursor(
            cursor=request.cursor,
            page_size=request.page_size,
            page=request.page,
            query=request.query,
            sort=request.sort,
            order=request.order,
            job_ids=request.job_ids,
            exclude_job_ids=request.exclude_job_ids,
            status_lookup=request.status_lookup,
            company_id=request.company_id,
            location=request.location,
            remote=request.remote,
            visa=request.visa,
            overall_score_min=request.overall_score_min,
            overall_score_max=request.overall_score_max,
            fit_score_min=request.fit_score_min,
            fit_score_max=request.fit_score_max,
            success_score_min=request.success_score_min,
            success_score_max=request.success_score_max,
            pinned=request.pinned,
            dismissed=request.dismissed,
            tags=request.tags,
            recommendation=request.recommendation,
            created_date=request.created_date,
        )
        return ListJobsV2Response(
            items=items,
            total=total,
            page=request.page if request.cursor is None else 1,
            page_size=request.page_size,
            next_cursor=next_cursor,
            has_more=has_more,
        )
