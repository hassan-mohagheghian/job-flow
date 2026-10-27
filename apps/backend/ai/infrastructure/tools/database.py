"""Database tool — provides ORM-based query execution for agents.

SRP: Only handles database query execution.
DIP: Agents use this tool instead of directly calling the database.

Uses predefined ORM queries instead of raw SQL for security and maintainability.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .base import BaseTool, ToolResult


class DatabaseTool(BaseTool):
    """Executes predefined read-only ORM queries against the project database.

    Agents use this to access data without importing DB modules directly.
    Only predefined queries are allowed — no raw SQL execution.
    """

    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._queries: dict[str, Callable[[Session, dict], list[dict[str, Any]]]] = {
            "list_jobs": self._list_jobs,
            "get_job": self._get_job,
            "get_job_stats": self._get_job_stats,
            "list_companies": self._list_companies,
            "get_company": self._get_company,
            "get_company_intelligence": self._get_company_intelligence,
            "list_skills": self._list_skills,
            "get_skill": self._get_skill,
            "get_skill_stats": self._get_skill_stats,
            "get_skill_relationships": self._get_skill_relationships,
            "list_pending_jobs": self._list_pending_jobs,
            "list_pending_companies": self._list_pending_companies,
            "get_rules": self._get_rules,
            "search_jobs": self._search_jobs,
        }

    @property
    def name(self) -> str:
        return "database"

    @property
    def description(self) -> str:
        return "Execute predefined read-only queries against the project database"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f"Query name. Available: {', '.join(sorted(self._queries.keys()))}",
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters (varies by query)",
                },
            },
            "required": ["query"],
        }

    def run(self, **kwargs) -> ToolResult:
        query_name = kwargs.get("query")
        if not query_name:
            return ToolResult(
                success=False,
                error=f"query parameter is required. Available: {', '.join(sorted(self._queries.keys()))}",
            )

        if query_name not in self._queries:
            return ToolResult(
                success=False,
                error=f"Unknown query '{query_name}'. Available: {', '.join(sorted(self._queries.keys()))}",
            )

        params = kwargs.get("params", {})

        try:
            if self._session is None:
                from shared.infrastructure.database.session import get_session_sync
                self._session = get_session_sync()

            result = self._queries[query_name](self._session, params)
            return ToolResult(
                success=True,
                data=result,
                metadata={"row_count": len(result), "query": query_name},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Query failed: {e}")

    def _get_session(self) -> Session:
        if self._session is None:
            from shared.infrastructure.database.session import get_session_sync
            self._session = get_session_sync()
        return self._session

    def _list_jobs(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from jobs.infrastructure.models.job_model import JobModel

        query = select(JobModel).where(JobModel.deleted == 0)

        if "company" in params:
            query = query.where(JobModel.company.ilike(f"%{params['company']}%"))
        if "min_score" in params:
            query = query.where(JobModel.overall_score >= params["min_score"])
        if "max_score" in params:
            query = query.where(JobModel.overall_score <= params["max_score"])
        if "location" in params:
            query = query.where(JobModel.location.ilike(f"%{params['location']}%"))
        if "limit" in params:
            query = query.limit(params["limit"])
        else:
            query = query.limit(20)

        query = query.order_by(JobModel.created_at.desc())
        rows = session.execute(query).scalars().all()
        return [self._job_to_dict(row) for row in rows]

    def _get_job(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from jobs.infrastructure.models.job_model import JobModel

        job_id = params.get("job_id")
        if not job_id:
            return [{"error": "job_id parameter is required"}]

        row = session.execute(
            select(JobModel).where(JobModel.id == job_id)
        ).scalars().first()
        if not row:
            return []
        return [self._job_to_dict(row)]

    def _get_job_stats(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from jobs.infrastructure.models.job_model import JobModel

        total = session.execute(
            select(func.count()).select_from(JobModel).where(JobModel.deleted == 0)
        ).scalar()
        avg_score = session.execute(
            select(func.avg(JobModel.overall_score)).where(JobModel.deleted == 0)
        ).scalar()
        companies = session.execute(
            select(func.count(func.distinct(JobModel.company))).where(JobModel.deleted == 0)
        ).scalar()

        return [{
            "total_jobs": total or 0,
            "average_score": round(float(avg_score or 0), 2),
            "unique_companies": companies or 0,
        }]

    def _list_companies(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from companies.infrastructure.models.company_model import CompanyModel

        query = select(CompanyModel)
        if "name" in params:
            query = query.where(CompanyModel.name.ilike(f"%{params['name']}%"))
        if "limit" in params:
            query = query.limit(params["limit"])
        else:
            query = query.limit(20)

        rows = session.execute(query).scalars().all()
        return [{
            "id": row.id,
            "name": row.name,
            "website": row.website,
            "industry": row.industry,
            "country": row.country,
            "city": row.city,
            "company_size": row.company_size,
            "processing_status": row.processing_status,
        } for row in rows]

    def _get_company(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from companies.infrastructure.models.company_model import CompanyModel

        company_id = params.get("company_id")
        if not company_id:
            return [{"error": "company_id parameter is required"}]

        row = session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        ).scalars().first()
        if not row:
            return []
        return [{
            "id": row.id,
            "name": row.name,
            "website": row.website,
            "domain": row.domain,
            "industry": row.industry,
            "country": row.country,
            "city": row.city,
            "description": row.description,
            "tech_stack": row.tech_stack,
            "company_size": row.company_size,
            "funding_stage": row.funding_stage,
        }]

    def _get_company_intelligence(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from companies.infrastructure.models.company_model import CompanyModel, CompanyIntelligenceModel

        company_id = params.get("company_id")
        if not company_id:
            return [{"error": "company_id parameter is required"}]

        row = session.execute(
            select(CompanyIntelligenceModel).where(CompanyIntelligenceModel.company_id == company_id)
        ).scalars().first()
        if not row:
            return []
        return [{
            "company_id": row.company_id,
            "overview": row.overview,
            "culture_analysis": row.culture_analysis,
            "visa_analysis": row.visa_analysis,
            "technology_analysis": row.technology_analysis,
            "scores": row.scores,
        }]

    def _list_skills(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from skills.infrastructure.models.skill_model import SkillModel

        query = select(SkillModel).where(SkillModel.hidden == 0)
        if "category" in params:
            query = query.where(SkillModel.category == params["category"])
        if "limit" in params:
            query = query.limit(params["limit"])
        else:
            query = query.limit(50)

        rows = session.execute(query).scalars().all()
        return [{
            "id": row.id,
            "name": row.name,
            "level": row.level,
            "category": row.category,
            "confidence": row.confidence,
            "market_relevance": row.market_relevance,
        } for row in rows]

    def _get_skill(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from skills.infrastructure.models.skill_model import SkillModel

        skill_name = params.get("name")
        skill_id = params.get("skill_id")
        if not skill_name and not skill_id:
            return [{"error": "name or skill_id parameter is required"}]

        if skill_id:
            row = session.execute(
                select(SkillModel).where(SkillModel.id == skill_id)
            ).scalars().first()
        else:
            row = session.execute(
                select(SkillModel).where(SkillModel.name == skill_name)
            ).scalars().first()

        if not row:
            return []
        return [{
            "id": row.id,
            "name": row.name,
            "level": row.level,
            "category": row.category,
            "confidence": row.confidence,
            "market_relevance": row.market_relevance,
            "source": row.source,
        }]

    def _get_skill_stats(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from skills.infrastructure.models.skill_model import SkillModel

        total = session.execute(
            select(func.count()).select_from(SkillModel).where(SkillModel.hidden == 0)
        ).scalar()
        categories = session.execute(
            select(SkillModel.category, func.count())
            .where(SkillModel.hidden == 0)
            .group_by(SkillModel.category)
        ).all()

        return [{
            "total_skills": total or 0,
            "by_category": {cat: count for cat, count in categories},
        }]

    def _get_skill_relationships(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from skills.infrastructure.models.skill_model import SkillRelationshipModel

        skill_name = params.get("name")
        if not skill_name:
            return [{"error": "name parameter is required"}]

        rows = session.execute(
            select(SkillRelationshipModel).where(
                SkillRelationshipModel.skill_name == skill_name
            )
        ).scalars().all()
        return [{
            "skill_name": row.skill_name,
            "related_name": row.related_name,
            "relation_type": row.relation_type,
            "confidence": row.confidence,
        } for row in rows]

    def _list_pending_jobs(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from jobs.infrastructure.models.job_model import JobModel

        query = select(JobModel).where(JobModel.deleted == 0)
        if "status" in params:
            query = query.where(JobModel.status == params["status"])
        if "limit" in params:
            query = query.limit(params.get("limit", 20))

        rows = session.execute(query).scalars().all()
        return [{
            "id": row.id,
            "url": row.url,
            "company": row.company,
            "status": row.status,
        } for row in rows]

    def _list_pending_companies(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from companies.infrastructure.models.company_model import CompanyModel

        query = select(CompanyModel)
        if "status" in params:
            query = query.where(CompanyModel.status == params["status"])
        if "limit" in params:
            query = query.limit(params.get("limit", 20))

        rows = session.execute(query).scalars().all()
        return [{
            "id": row.id,
            "input_text": row.notes or "",
            "company_name": row.name,
            "status": row.status,
        } for row in rows]

    def _get_rules(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from rules.infrastructure.models.rule_model import RuleModel

        query = select(RuleModel).where(RuleModel.enabled == 1)
        if "category" in params:
            query = query.where(RuleModel.category == params["category"])
        if "scope" in params:
            query = query.where(RuleModel.scope == params["scope"])

        rows = session.execute(query).scalars().all()
        return [{
            "id": row.id,
            "category": row.category,
            "rule_type": row.rule_type,
            "scope": row.scope,
            "key": row.key,
            "value": row.value,
            "priority": row.priority,
        } for row in rows]

    def _search_jobs(self, session: Session, params: dict) -> list[dict[str, Any]]:
        from jobs.infrastructure.models.job_model import JobModel

        search_term = params.get("term", "")
        if not search_term:
            return [{"error": "term parameter is required"}]

        query = select(JobModel).where(
            JobModel.deleted == 0,
            (JobModel.title.ilike(f"%{search_term}%")) |
            (JobModel.description.ilike(f"%{search_term}%")) |
            (JobModel.stack.ilike(f"%{search_term}%"))
        )
        if "limit" in params:
            query = query.limit(params["limit"])
        else:
            query = query.limit(20)

        query = query.order_by(JobModel.created_at.desc())
        rows = session.execute(query).scalars().all()
        return [self._job_to_dict(row) for row in rows]

    def _job_to_dict(self, job: Any) -> dict[str, Any]:
        return {
            "id": job.id,
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "fit_score": job.fit_score,
            "success_score": job.success_score,
            "overall_score": job.overall_score,
            "stack": job.stack,
            "url": job.url,
            "created_at": str(job.created_at) if job.created_at else None,
        }
