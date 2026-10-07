"""Root API router. Matches the exact paths the frontend expects.

Routes are organized by bounded context. Each context owns its
presentation/api/ layer with routers and schemas.
"""

from fastapi import APIRouter, Depends

# Bounded context routers — imported from their owning context's presentation layer
from skills.presentation.api.skills_router import router as skills_router

from rules.presentation.api.rules_router import router as rules_router
from shared.presentation.api.dashboard_router import router as dashboard_router
from ai.presentation.api.llm_configurations_router import router as llm_configurations_router
from processing.presentation.api.process_router import router as process_router
from processing.presentation.api.executions_router import router as executions_router
from candidates.presentation.api.candidates_router import router as candidates_router
from applications.presentation.api.applications_router import router as applications_router
from opportunities.presentation.api.opportunities_router import router as opportunities_router
from roadmaps.presentation.api.roadmaps_router import router as roadmaps_router
from placeholders.presentation.api.placeholders_router import router as placeholders_router

# DI dependencies — wired through bounded context infrastructure
from dependencies import get_job_repo, get_skill_repo, get_summary_repo, get_skill_relationship_repo


api_router = APIRouter(prefix="/api")

# ── Auth (PUBLIC — no get_current_user required) ────────────────

from auth.presentation.api.auth_router import router as auth_router
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── V2 routers (registered before legacy to prevent path conflicts) ──

from jobs.presentation.api.jobs_v2_router import router as jobs_v2_router
api_router.include_router(jobs_v2_router, prefix="/jobs", tags=["jobs-v2"])

from companies.presentation.api.companies_v2_router import router as companies_v2_router
api_router.include_router(companies_v2_router, prefix="/companies", tags=["companies-v2"])

from cities.presentation.api.cities_router import router as cities_router
api_router.include_router(cities_router, prefix="/cities", tags=["cities"])

# ── Feature routers ──────────────────────────────────────────────

api_router.include_router(skills_router, prefix="/skills", tags=["skills"])

api_router.include_router(rules_router, prefix="/rules", tags=["rules"])
api_router.include_router(dashboard_router, prefix="", tags=["dashboard"])
api_router.include_router(llm_configurations_router, prefix="/llm-configurations", tags=["llm-configurations"])
api_router.include_router(process_router, prefix="/jobs", tags=["processing"])
api_router.include_router(executions_router, prefix="/processing", tags=["processing"])

# ── Candidate Profile ────────────────────────────────────────────

api_router.include_router(candidates_router, prefix="/candidates", tags=["candidates"])
api_router.include_router(applications_router, prefix="/applications", tags=["applications"])
api_router.include_router(opportunities_router, prefix="/opportunities", tags=["opportunities"])
api_router.include_router(roadmaps_router, prefix="/roadmaps", tags=["roadmaps"])
api_router.include_router(placeholders_router, prefix="/placeholders", tags=["placeholders"])

# ── Flask compat routes ─────────────────────────────────────────

@api_router.get("/summaries")
def summaries_compat(summary_repo=Depends(get_summary_repo)):
    return summary_repo.get_all()


@api_router.get("/tech-stack")
def tech_stack_compat(skill_repo=Depends(get_skill_repo)):
    return skill_repo.list_visible()


# ── Skill relationships compat routes ───────────────────────────

@api_router.get("/skill-relationships/{skill_name}")
def get_skill_relationships_compat(skill_name: str, skill_repo=Depends(get_skill_repo)):
    return skill_repo.get_relationships(skill_name)


@api_router.post("/skill-relationships")
def create_skill_relationship_compat(data: dict, skill_repo=Depends(get_skill_repo)):
    from shared.application.exceptions import ConflictError
    success = skill_repo.create_relationship(data)
    if not success:
        raise ConflictError("Relationship already exists")
    return {"status": "created"}


@api_router.delete("/skill-relationships/{id}")
def delete_skill_relationship_compat(id: int, skill_repo=Depends(get_skill_repo)):
    skill_repo.delete_relationship(id)
    return {"status": "deleted"}


# ── Job-Company link ─────────────────────────────────────────────

@api_router.post("/jobs/{job_id}/link-company")
def link_job_to_company(job_id: str, data: dict, job_repo=Depends(get_job_repo)):
    company_id = data.get("company_id")
    if company_id:
        job_repo.update_fields(job_id, company_id=company_id)
    return {"status": "linked"}



