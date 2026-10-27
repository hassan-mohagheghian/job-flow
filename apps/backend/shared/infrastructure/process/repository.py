"""
SQLAlchemy repository implementations — persistence layer.

DDD: Repositories are the only place that touches the database directly.
Domain models flow in, SQLAlchemy ORM handles the rest.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from .interfaces import IPendingRepository, IJobRepository
from .models import ItemStatus, WorkflowLogEntry

from jobs.infrastructure.models.job_model import JobModel
from companies.infrastructure.models.company_model import CompanyModel
from jobs.infrastructure.models.misc_models import SummaryModel


# ── Pending Jobs Repository (backed by JobModel) ─────────────────

class PendingJobRepository(IPendingRepository):
    """Repository for job processing backed by JobModel."""

    def __init__(self, session: Session):
        self._session = session

    def get(self, pid: str) -> Optional[dict]:
        row = self._session.query(JobModel).filter(JobModel.id == pid).first()
        if not row:
            return None
        return self._to_dict(row)

    def update_status(self, pid: str, status: str | ItemStatus, **fields) -> None:
        m = self._session.query(JobModel).filter(JobModel.id == pid).first()
        if not m:
            return
        m.status = status.value if isinstance(status, ItemStatus) else status
        m.updated_at = datetime.now().isoformat()
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self._session.commit()

    def update_fields(self, pid: str, table: str = "pending_jobs", **fields) -> None:
        m = self._session.query(JobModel).filter(JobModel.id == pid).first()
        if not m:
            return
        m.updated_at = datetime.now().isoformat()
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self._session.commit()

    def update_step(self, pid: str, step: str, val: int, **fields) -> None:
        m = self._session.query(JobModel).filter(JobModel.id == pid).first()
        if not m:
            return
        if hasattr(m, step):
            setattr(m, step, val)
        m.updated_at = datetime.now().isoformat()
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self._session.commit()

    def append_log(self, pid: str, entry: WorkflowLogEntry) -> None:
        m = self._session.query(JobModel).filter(JobModel.id == pid).first()
        if not m:
            return
        logs = json.loads(m.workflow_log or '[]')
        logs.append(entry.to_dict())
        m.workflow_log = json.dumps(logs)
        self._session.commit()

    def get_logs(self, pid: str) -> List[WorkflowLogEntry]:
        m = self._session.query(JobModel).filter(JobModel.id == pid).first()
        if not m:
            return []
        logs = json.loads(m.workflow_log or '[]')
        return [WorkflowLogEntry.from_dict(e) for e in logs]

    def claim_next(self) -> Optional[dict]:
        m = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == 'queued'
        ).order_by(JobModel.queue_order.asc(), JobModel.id.asc()).first()
        if not m:
            return None
        m.status = 'processing'
        m.updated_at = datetime.now().isoformat()
        self._session.commit()
        self._session.refresh(m)
        return self._to_dict(m)

    def count_by_status(self) -> Dict[str, int]:
        from shared.infrastructure.process.models import JobStatus
        counts = {}
        for status in JobStatus:
            cnt = self._session.query(JobModel).filter(
                JobModel.deleted == 0,
                JobModel.status == status.value
            ).count()
            counts[status.value] = cnt
        return counts

    def reset_orphans(self) -> int:
        count = self._session.query(JobModel).filter(
            JobModel.deleted == 0,
            JobModel.status == 'processing'
        ).count()
        if count > 0:
            self._session.query(JobModel).filter(
                JobModel.deleted == 0,
                JobModel.status == 'processing'
            ).update({
                'status': 'queued',
                'error': None,
                'updated_at': datetime.now().isoformat(),
            })
            self._session.commit()
        return count

    @staticmethod
    def _to_dict(m: JobModel) -> dict:
        return {
            'id': m.id,
            'url': m.url or '',
            'source': m.source or 'web',
            'status': m.status,
            'notes': m.notes or '[]',
            'links': m.links or '[]',
            'workflow_log': m.workflow_log or '[]',
            'error': m.error,
            'queue_order': m.queue_order,
            'session_id': m.session_id,
            'current_node': m.current_node,
            'retry_count': m.retry_count,
            'company': m.company or '',
            'job_id': m.id,
            'failure_details': m.failure_reason,
            'created_at': m.created_at.isoformat() if isinstance(m.created_at, datetime) else m.created_at,
            'updated_at': m.updated_at.isoformat() if isinstance(m.updated_at, datetime) else m.updated_at,
        }


# ── Pending Companies Repository (backed by CompanyModel) ─────────

class PendingCompanyRepository(IPendingRepository):
    """Repository for company processing backed by CompanyModel."""

    def __init__(self, session: Session):
        self._session = session

    def get(self, pid: str) -> Optional[dict]:
        row = self._session.query(CompanyModel).filter(CompanyModel.id == pid).first()
        if not row:
            return None
        return self._to_dict(row)

    def update_status(self, pid: str, status: str | ItemStatus, **fields) -> None:
        m = self._session.query(CompanyModel).filter(CompanyModel.id == pid).first()
        if not m:
            return
        m.status = status.value if isinstance(status, ItemStatus) else status
        m.updated_at = datetime.now().isoformat()
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self._session.commit()

    def update_fields(self, pid: str, table: str = "pending_companies", **fields) -> None:
        m = self._session.query(CompanyModel).filter(CompanyModel.id == pid).first()
        if not m:
            return
        m.updated_at = datetime.now().isoformat()
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self._session.commit()

    def update_step(self, pid: str, step: str, val: int, **fields) -> None:
        m = self._session.query(CompanyModel).filter(CompanyModel.id == pid).first()
        if not m:
            return
        if hasattr(m, step):
            setattr(m, step, val)
        m.updated_at = datetime.now().isoformat()
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self._session.commit()

    def append_log(self, pid: str, entry: WorkflowLogEntry) -> None:
        m = self._session.query(CompanyModel).filter(CompanyModel.id == pid).first()
        if not m:
            return
        logs = json.loads(m.workflow_log or '[]')
        logs.append(entry.to_dict())
        m.workflow_log = json.dumps(logs)
        self._session.commit()

    def get_logs(self, pid: str) -> List[WorkflowLogEntry]:
        m = self._session.query(CompanyModel).filter(CompanyModel.id == pid).first()
        if not m:
            return []
        logs = json.loads(m.workflow_log or '[]')
        return [WorkflowLogEntry.from_dict(e) for e in logs]

    ACTIVE_STATUSES = {'processing'}

    def claim_next(self) -> Optional[dict]:
        m = self._session.query(CompanyModel).filter(
            CompanyModel.status == 'queued'
        ).order_by(CompanyModel.id.asc()).first()
        if not m:
            return None
        m.status = 'processing'
        m.updated_at = datetime.now().isoformat()
        self._session.commit()
        self._session.refresh(m)
        return self._to_dict(m)

    def count_by_status(self) -> Dict[str, int]:
        from shared.infrastructure.process.models import JobStatus
        counts = {}
        for status in JobStatus:
            cnt = self._session.query(CompanyModel).filter(
                CompanyModel.status == status.value
            ).count()
            counts[status.value] = cnt
        return counts

    def reset_orphans(self) -> int:
        count = self._session.query(CompanyModel).filter(
            CompanyModel.status.in_(self.ACTIVE_STATUSES)
        ).count()
        if count > 0:
            self._session.query(CompanyModel).filter(
                CompanyModel.status.in_(self.ACTIVE_STATUSES)
            ).update({
                'status': 'created',
                'error': None,
                'updated_at': datetime.now().isoformat(),
            })
            self._session.commit()
        return count

    @staticmethod
    def _to_dict(m: CompanyModel) -> dict:
        return {
            'id': m.id,
            'input_text': m.input_text or '[]',
            'notes': m.input_text or '[]',
            'links': m.links or '[]',
            'source': m.source or 'web',
            'input_type': m.input_type or 'url',
            'status': m.status,
            'workflow_log': m.workflow_log or '[]',
            'error': m.error,
            'session_id': m.session_id,
            'current_node': m.current_node,
            'retry_count': m.retry_count,
            'company_id': m.id,
            'company_name': m.name or '',
            'failure_details': m.failure_reason,
            'created_at': m.created_at.isoformat() if isinstance(m.created_at, datetime) else m.created_at,
            'updated_at': m.updated_at.isoformat() if isinstance(m.updated_at, datetime) else m.updated_at,
        }


# ── Job Results Repository ────────────────────────────────────────

class JobRepository(IJobRepository):
    """Repository for jobs, summaries, and resumes tables via SQLAlchemy."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_url(self, url: str) -> Optional[dict]:
        m = self._session.query(JobModel).filter(
            JobModel.url == url, JobModel.deleted == 0
        ).first()
        if not m:
            return None
        return {
            'id': m.id, 'company': m.company, 'url': m.url,
        }

    def insert(self, job_data: dict) -> str:
        now = datetime.now().isoformat()
        job_id = job_data['id']
        existing = self._session.query(JobModel).filter(JobModel.id == job_id).first()
        if existing:
            for k, v in job_data.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
        else:
            m = JobModel(
                id=job_id,
                company=job_data.get('company'),
                role=job_data.get('role'),
                location=job_data.get('location'),
                salary=job_data.get('salary'),
                stack=job_data.get('stack'),
                visa=job_data.get('visa'),
                applicants=job_data.get('applicants'),
                posted=job_data.get('posted'),
                industry=job_data.get('industry'),
                domain=job_data.get('domain'),
                notes=job_data.get('notes'),
                action=job_data.get('action'),
                url=job_data.get('url'),
                workflow_log=job_data.get('workflow_log', '[]'),
                created_at=job_data.get('created_at', now),
                posted_at=job_data.get('posted_at'),
                deleted=job_data.get('deleted', 0),
                work_types=job_data.get('work_types', []),
                employment_types=job_data.get('employment_types', ['Full-time']),
                raw_description=job_data.get('raw_description'),
                structured_description=job_data.get('structured_description'),
                raw_file_path=job_data.get('raw_file_path'),
                structured_file_path=job_data.get('structured_file_path'),
                rescoring=job_data.get('rescoring', 0),
                adv_at=job_data.get('adv_at'),
                see_at=job_data.get('see_at'),
                apply_reason=job_data.get('apply_reason'),
                company_url=job_data.get('company_url'),
                linkedin_url=job_data.get('linkedin_url'),
                apply_time=job_data.get('apply_time'),
                response_time=job_data.get('response_time'),
                response_status=job_data.get('response_status'),
                fit_score=job_data.get('fit_score'),
                success_score=job_data.get('success_score'),
                overall_score=job_data.get('overall_score'),
                company_id=job_data.get('company_id'),
            )
            self._session.add(m)
        self._session.commit()
        return job_id

    def insert_summary(self, d: dict) -> None:
        existing = self._session.query(SummaryModel).filter(SummaryModel.job_id == d['job_id']).first()
        if existing:
            existing.company = d.get('company')
            existing.match = d.get('match')
            existing.score = d.get('score')
            existing.summary = d.get('summary')
            existing.stack = d.get('stack')
            existing.resume_fit = d.get('resumeFit')
            existing.note = d.get('note')
            existing.url = d.get('url')
        else:
            m = SummaryModel(
                job_id=d['job_id'], company=d.get('company'), match=d.get('match'),
                score=d.get('score'), summary=d.get('summary'), stack=d.get('stack'),
                resume_fit=d.get('resumeFit'), note=d.get('note'), url=d.get('url'),
            )
            self._session.add(m)
        self._session.commit()

    def save_workflow_log(self, job_id: str, log_json: str) -> None:
        m = self._session.query(JobModel).filter(JobModel.id == job_id).first()
        if m:
            m.workflow_log = log_json
            self._session.commit()
