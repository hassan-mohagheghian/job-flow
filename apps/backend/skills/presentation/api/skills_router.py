"""Tech stack CRUD, skill relationships, merge, hide/restore."""

from __future__ import annotations

import base64
from typing import Any, Callable

from fastapi import APIRouter, Depends, Query

from dependencies import get_skill_repo, get_skill_category_service, get_skill_normalization_service, get_job_repo, get_skill_resource_service, get_skill_note_repo, get_skill_link_repo
from skills.application.use_cases.skill_category_service import SkillCategoryService
from skills.application.use_cases.skill_normalization_service import SkillNormalizationService
from skills.application.services.skill_resource_service import SkillResourceService
from skills.infrastructure import SQLAlchemySkillRepository
from skills.presentation.api.schemas.skills import (
    SkillCreate,
    SkillUpdate,
    SkillPinRequest,
    SkillRename,
    SkillHide,
    SkillAliasAdd,
    SkillAliasRemove,
    SkillMerge,
    SkillBreakdown,
    SkillCanonicalChange,
    SkillBulkHide,
    SkillBulkCategorize,
    SkillCategoryUpdate,
    SkillCategoryCreate,
    SkillListItemSchema,
    SkillListResponseSchema,
    SkillJobRefSchema,
    SkillJobsResponseSchema,
    CreateSkillNoteRequest,
    SkillNoteSchema,
    CreateSkillLinkRequest,
    SkillLinkSchema,
)
from shared.application.exceptions import NotFoundError, BadRequestError, ConflictError

router = APIRouter()

DEFAULT_PAGE_SIZE = 25

SORTABLE_SKILL_FIELDS = ("created_at", "name", "level", "confidence", "market_relevance", "mention_count")


def _cursor_decode(cursor: str) -> int:
    """Decode an opaque base64 offset cursor; invalid cursors restart at 0."""
    if not cursor:
        return 0
    try:
        return int(base64.b64decode(cursor.encode()).decode())
    except Exception:
        return 0


def _cursor_encode(offset: int) -> str:
    return base64.b64encode(str(offset).encode()).decode()


def _skill_matches(
    row: dict[str, Any],
    query: str,
    categories: list[str],
    pinned: bool = False,
) -> bool:
    if pinned and not bool(row.get("pinned")):
        return False
    if categories:
        skill_cats = row.get("categories") or []
        primary = row.get("category") or ""
        if not any(c in skill_cats or c == primary for c in categories):
            return False
    if query:
        q = query.lower()
        haystacks = [row.get("name"), row.get("roles"), row.get("path")]
        haystacks += row.get("aliases") or []
        if not any(h and q in str(h).lower() for h in haystacks):
            return False
    return True


def _skill_sort_key(row: dict[str, Any], sort: str) -> Any:
    if sort in SORTABLE_SKILL_FIELDS:
        return row.get(sort)
    return row.get("created_at")


@router.get("/list")
def list_skills_v2(
    query: str = Query("", description="Substring search over name, roles, path, aliases"),
    categories: list[str] = Query(
        default=[],
        description="Exact category filter; OR semantics — repeat the param for multiple categories",
    ),
    category: str = Query("", description="Legacy single category filter (use `categories` instead)"),
    pinned: bool = Query(False, description="Only include pinned skills"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="asc or desc"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=200),
    cursor: str = Query("", description="Opaque pagination cursor"),
    repo: SQLAlchemySkillRepository = Depends(get_skill_repo),
) -> SkillListResponseSchema:
    """List visible skills with server-side search, category/pinned filter, sort and cursor pagination."""
    if categories:
        pass
    elif category:
        categories = [category]
    categories = [c for c in categories if c]
    rows = [r for r in repo.list_visible() if _skill_matches(r, query, categories, pinned)]

    if rows:
        mention_counts = repo.get_mention_counts([r["id"] for r in rows])
        for r in rows:
            r["mention_count"] = mention_counts.get(r["id"], 0)

    key: Callable[[dict[str, Any]], Any] = lambda r: _skill_sort_key(r, sort)
    with_value = [r for r in rows if key(r) is not None]
    without_value = [r for r in rows if key(r) is None]
    with_value.sort(key=key, reverse=(order == "desc"))
    rows = with_value + without_value

    total = len(rows)
    offset = _cursor_decode(cursor)
    page = rows[offset:offset + page_size]
    next_offset = offset + len(page)
    has_more = next_offset < total

    return SkillListResponseSchema(
        items=[
            SkillListItemSchema(
                id=r["id"],
                name=r.get("name") or "",
                level=r.get("level") or 1,
                roles=r.get("roles") or "",
                path=r.get("path") or "",
                category=r.get("category") or "",
                categories=r.get("categories") or [],
                confidence=r.get("confidence"),
                market_relevance=r.get("market_relevance"),
                evidence=r.get("evidence"),
                tags=r.get("tags") or [],
                aliases=r.get("aliases") or [],
                source_type=r.get("source_type") or "user_input",
                mention_count=r.get("mention_count") or 0,
                pinned=bool(r.get("pinned")),
                created_at=r.get("created_at"),
            )
            for r in page
        ],
        next_cursor=_cursor_encode(next_offset) if has_more else None,
        has_more=has_more,
        total_items=total,
    )


@router.get("")
def list_skills(
    category: str = Query(""),
    repo: SQLAlchemySkillRepository = Depends(get_skill_repo),
):
    """Get visible skills with aliases and tags."""
    return repo.list_visible(category)


@router.get("/hidden")
def list_hidden_skills(repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """List all hidden skills."""
    return repo.list_hidden()


@router.get("/categories")
def get_categories(repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Get the full category catalog with per-category counts."""
    return repo.get_categories()


@router.post("/categories")
def create_category(
    data: SkillCategoryCreate,
    service: SkillCategoryService = Depends(get_skill_category_service),
):
    """Create a new category in the catalog (idempotent)."""
    name = data.name.strip()
    if not name:
        raise BadRequestError("Category name is required")
    result = service.create_category(name)
    return result


@router.delete("/categories/{name}")
def delete_category(
    name: str,
    service: SkillCategoryService = Depends(get_skill_category_service),
):
    """Delete an unused category from the catalog."""
    result = service.delete_category(name)
    if result["status"] == "not_found":
        raise NotFoundError(f'Category "{name}" not found')
    if result["status"] == "in_use":
        raise ConflictError(
            f'Category "{name}" is assigned to {result["count"]} skill(s) and cannot be deleted'
        )
    return {"status": "deleted", "name": name}


@router.get("/stats")
def get_stats(repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Get overall skills statistics."""
    return repo.get_stats()


@router.get("/breakdowns")
def list_breakdowns(
    service: SkillNormalizationService = Depends(get_skill_normalization_service),
):
    """Return the full origin→children decomposition map for skill extraction."""
    return {"breakdowns": service.get_breakdown_map()}


@router.get("/{id}/breakdowns")
def get_skill_breakdowns(
    id: int,
    repo: SQLAlchemySkillRepository = Depends(get_skill_repo),
):
    """Return a skill's children (and origin) after a breakdown."""
    return repo.list_breakdowns(id)


@router.get("/{id}")
def get_skill(
    id: int,
    repo: SQLAlchemySkillRepository = Depends(get_skill_repo),
    note_repo=Depends(get_skill_note_repo),
    link_repo=Depends(get_skill_link_repo),
):
    """Get a single skill with aliases, tags, notes, and links."""
    skill = repo.get_by_id(id)
    if not skill:
        raise NotFoundError(f"Skill {id} not found")
    skill["notes"] = note_repo.list_for_skill(id)
    skill["links"] = link_repo.list_for_skill(id)
    return skill


@router.get("/{id}/jobs", response_model=SkillJobsResponseSchema)
def get_skill_jobs(
    id: int,
    repo: SQLAlchemySkillRepository = Depends(get_skill_repo),
    job_repo=Depends(get_job_repo),
):
    """List the jobs that mention a skill (source_type="job")."""
    skill = repo.get_by_id(id)
    if not skill:
        raise NotFoundError(f"Skill {id} not found")
    job_ids = repo.get_job_mention_ids(id)
    jobs, _, _, _ = job_repo.search_jobs_cursor(
        job_ids=job_ids,
        page_size=200,
        sort="created_at",
        order="desc",
    )
    return SkillJobsResponseSchema(
        jobs=[
            SkillJobRefSchema(
                id=j.get("id") or "",
                title=j.get("title") or j.get("role") or "",
                company=j.get("company"),
                location=j.get("location"),
                fit_score=j.get("fit_score"),
                success_score=j.get("success_score"),
                overall_score=j.get("overall_score"),
                pinned=bool(j.get("pinned")),
                status=j.get("status") or "",
                created_at=j.get("created_at"),
            )
            for j in jobs
        ],
        total=len(jobs),
    )


@router.post("")
def create_skill(data: SkillCreate, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Create a new skill."""
    existing = repo.get_by_name(data.name)
    if existing:
        return {"id": existing["id"], "name": data.name, "message": "Skill already exists"}
    return repo.create(data.model_dump())


@router.put("/{id}")
def update_skill(
    id: int,
    data: SkillUpdate,
    service: SkillCategoryService = Depends(get_skill_category_service),
):
    """Update a skill."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise BadRequestError("No valid fields to update")
    result = service.update_skill(id, updates)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return result


@router.patch("/{id}/rename")
def rename_skill(id: int, data: SkillRename, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Rename a skill and update all references."""
    new_name = data.name.strip()
    result = repo.rename(id, new_name)
    if not result:
        existing = repo.get_by_id(id)
        if not existing:
            raise NotFoundError(f"Skill {id} not found")
        raise ConflictError(f'Skill "{new_name}" already exists')
    return result


@router.delete("/{id}")
def delete_skill(id: int, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Delete a skill and all its aliases."""
    skill = repo.get_by_id(id)
    if not skill:
        raise NotFoundError(f"Skill {id} not found")
    repo.delete(id)
    return {"status": "deleted", "name": skill["name"], "aliases_deleted": skill.get("aliases", [])}


@router.patch("/{id}/hide")
def hide_skill(id: int, data: SkillHide, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Toggle hidden flag on a skill."""
    result = repo.set_hidden(id, data.hidden)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return result


@router.patch("/{id}/restore")
def restore_skill(id: int, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Restore a hidden skill."""
    result = repo.set_hidden(id, 0)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return result


@router.put("/{id}/pinned")
def set_skill_pinned(id: int, data: SkillPinRequest, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Pin or unpin a skill."""
    result = repo.set_pinned(id, data.pinned)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return {"id": id, "pinned": data.pinned}


@router.post("/{id}/aliases")
def add_skill_alias(id: int, data: SkillAliasAdd, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Add an alias to a skill."""
    result = repo.add_alias(id, data.alias_name)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return result


@router.delete("/{id}/aliases")
def remove_skill_alias(id: int, alias_name: str = Query(...), repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Remove an alias from a skill."""
    result = repo.remove_alias(id, alias_name)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return result


@router.post("/merge")
def merge_skills(data: SkillMerge, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Merge source skills into target skill."""
    if not data.source_ids:
        raise BadRequestError("source_ids must not be empty")
    if data.target_id in data.source_ids:
        raise BadRequestError("target skill cannot be one of the sources")
    result = repo.merge(data.target_id, data.source_ids)
    if "error" in result:
        raise NotFoundError(result["error"])
    return result


@router.post("/{id}/breakdown")
def break_down_skill(
    id: int,
    data: SkillBreakdown,
    service: SkillNormalizationService = Depends(get_skill_normalization_service),
):
    """Break a composite skill into atomic child skills.

    Children are resolved by name/alias/canonical slug and created only when
    missing. The origin's job mentions are duplicated onto every child and the
    origin is soft-hidden. The origin→children map feeds skill extraction.
    """
    result = service.break_down(id, data.child_names)
    if "error" in result:
        if "not found" in result["error"]:
            raise NotFoundError(result["error"])
        raise BadRequestError(result["error"])
    return result


@router.patch("/{id}/canonical")
def promote_alias_to_canonical(
    id: int,
    data: SkillCanonicalChange,
    repo: SQLAlchemySkillRepository = Depends(get_skill_repo),
    service: SkillNormalizationService = Depends(get_skill_normalization_service),
):
    """Promote an alias to be the canonical name of a skill; the old canonical
    name becomes an alias of the same skill."""
    result = service.promote_alias_to_canonical(id, data.alias_name)
    if not result:
        skill = repo.get_by_id(id)
        if not skill:
            raise NotFoundError(f"Skill {id} not found")
        aliases = skill.get("aliases", [])
        if data.alias_name not in aliases:
            raise BadRequestError(f'"{data.alias_name}" is not an alias of "{skill["name"]}"')
        raise ConflictError(f'"{data.alias_name}" is already the canonical name of another skill')
    return result


@router.get("/skill-relationships/{skill_name}")
def get_skill_relationships(skill_name: str, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Get all relationships for a skill."""
    return repo.get_relationships(skill_name)


@router.post("/skill-relationships")
def create_skill_relationship(data: dict, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Create a skill relationship."""
    success = repo.create_relationship(data)
    if not success:
        raise ConflictError("Relationship already exists")
    return {"status": "created"}


@router.delete("/skill-relationships/{id}")
def delete_skill_relationship(id: int, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Delete a skill relationship."""
    repo.delete_relationship(id)
    return {"status": "deleted"}


@router.post("/bulk-hide")
def bulk_hide(data: SkillBulkHide, repo: SQLAlchemySkillRepository = Depends(get_skill_repo)):
    """Hide multiple skills at once."""
    if not data.ids:
        raise BadRequestError("ids array required")
    count = repo.bulk_hide(data.ids)
    return {"status": "hidden", "count": count}


@router.post("/bulk-categorize")
def bulk_categorize(
    data: SkillBulkCategorize,
    service: SkillCategoryService = Depends(get_skill_category_service),
):
    """Re-categorize multiple skills at once (category auto-created if new)."""
    if not data.ids:
        raise BadRequestError("ids array required")
    category = data.category.strip()
    if not category:
        raise BadRequestError("category is required")
    count = service.bulk_categorize(data.ids, category)
    return {"status": "categorized", "category": category, "count": count}


@router.put("/{id}/category")
def update_category(
    id: int,
    data: SkillCategoryUpdate,
    service: SkillCategoryService = Depends(get_skill_category_service),
):
    """Set a skill's category (auto-creates the category if new)."""
    category = data.category.strip()
    if not category:
        raise BadRequestError("category is required")
    result = service.categorize(id, category)
    if not result:
        raise NotFoundError(f"Skill {id} not found")
    return result


@router.post("/{id}/notes", status_code=201, response_model=SkillNoteSchema)
def add_skill_note(
    id: int,
    body: CreateSkillNoteRequest,
    service: SkillResourceService = Depends(get_skill_resource_service),
):
    """Add a free-text note to a skill."""
    return service.add_note(id, body.content)


@router.delete("/notes/{note_id}", status_code=204)
def delete_skill_note(
    note_id: int,
    service: SkillResourceService = Depends(get_skill_resource_service),
):
    """Delete a skill note."""
    service.delete_note(note_id)


@router.post("/{id}/links", status_code=201, response_model=SkillLinkSchema)
def add_skill_link(
    id: int,
    body: CreateSkillLinkRequest,
    service: SkillResourceService = Depends(get_skill_resource_service),
):
    """Add a titled resource link to a skill."""
    return service.add_link(id, body.title, body.url)


@router.delete("/links/{link_id}", status_code=204)
def delete_skill_link(
    link_id: int,
    service: SkillResourceService = Depends(get_skill_resource_service),
):
    """Delete a skill link."""
    service.delete_link(link_id)
