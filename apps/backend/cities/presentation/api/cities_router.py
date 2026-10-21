"""Cities API router.

GET /cities/list — paginated list of canonical cities with job counts.
POST /cities/merge — merge source cities into a target.
POST /cities/{id}/aliases — add an alias.
DELETE /cities/{id}/aliases — remove an alias.
PATCH /cities/{id}/canonical — promote an alias to the canonical name.

Default sort is by job count (descending). Sortable by jobs, country, city,
created_at. Owned by the Cities bounded context (per-context router, rule 10).
"""

from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_city_repo, get_city_service
from cities.application.services.city_service import CityService
from cities.infrastructure.repositories.sa_city_repository import SQLAlchemyCityRepository
from cities.presentation.api.schemas.cities import (
    CityAliasAddSchema,
    CityCanonicalChangeSchema,
    CityListResponseSchema,
    CityMergeSchema,
    build_city_list_response,
)

router = APIRouter()

DEFAULT_PAGE_SIZE = 10
SORTABLE_FIELDS = {"jobs", "country", "city", "created_at"}


def _cursor_decode(cursor: str) -> int:
    if not cursor:
        return 0
    try:
        return int(base64.b64decode(cursor.encode()).decode())
    except Exception:
        return 0


def _cursor_encode(offset: int) -> str:
    return base64.b64encode(str(offset).encode()).decode()


def _matches(row: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    q = query.lower()
    haystacks = [row.get("city"), row.get("country"), row.get("original_text")]
    return any(h and q in str(h).lower() for h in haystacks)


@router.get("/list", response_model=CityListResponseSchema)
def list_cities(
    query: str = Query("", description="Substring search over city, country, original text"),
    sort: str = Query("jobs", description="Sort field: jobs | country | city | created_at"),
    order: str = Query("desc", description="asc or desc"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=200),
    cursor: str = Query("", description="Opaque pagination cursor"),
    repo: SQLAlchemyCityRepository = Depends(get_city_repo),
) -> CityListResponseSchema:
    """List canonical cities with their job counts, sorted by jobs by default."""
    if sort not in SORTABLE_FIELDS:
        sort = "jobs"
    if order not in {"asc", "desc"}:
        order = "desc"

    rows = [r for r in repo.list_with_job_counts(sort, order) if _matches(r, query)]

    total = len(rows)
    offset = _cursor_decode(cursor)
    page = rows[offset:offset + page_size]
    next_offset = offset + len(page)
    has_more = next_offset < total

    return build_city_list_response(
        page,
        _cursor_encode(next_offset) if has_more else None,
        has_more,
        total,
    )


@router.post("/merge")
def merge_cities(
    body: CityMergeSchema,
    service: CityService = Depends(get_city_service),
) -> dict[str, Any]:
    """Merge one or more source cities into a target city."""
    if not body.source_ids:
        raise HTTPException(status_code=400, detail="source_ids must not be empty")
    if body.target_id in body.source_ids:
        raise HTTPException(status_code=400, detail="target must not be a source")

    result = service.merge(body.target_id, body.source_ids)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{city_id}/aliases")
def add_city_alias(
    city_id: str,
    body: CityAliasAddSchema,
    service: CityService = Depends(get_city_service),
) -> dict[str, Any]:
    """Add an alias to a city."""
    result = service.add_alias(city_id, body.alias_name)
    if result is None:
        raise HTTPException(status_code=404, detail="City not found")
    return result


@router.delete("/{city_id}/aliases")
def remove_city_alias(
    city_id: str,
    alias_name: str = Query(..., description="Alias to remove"),
    service: CityService = Depends(get_city_service),
) -> dict[str, Any]:
    """Remove an alias from a city."""
    result = service.remove_alias(city_id, alias_name)
    if result is None:
        raise HTTPException(status_code=404, detail="City not found")
    return result


@router.patch("/{city_id}/canonical")
def promote_city_canonical(
    city_id: str,
    body: CityCanonicalChangeSchema,
    service: CityService = Depends(get_city_service),
) -> dict[str, Any]:
    """Promote an alias to be the canonical city name."""
    result = service.promote_alias_to_canonical(city_id, body.alias_name)
    if result is None:
        raise HTTPException(status_code=404, detail="City not found")
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


__all__ = ["router"]