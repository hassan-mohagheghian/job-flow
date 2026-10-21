"""Application repository interface."""

from abc import ABC, abstractmethod
from typing import Any


class IApplicationRepository(ABC):
    """Data access for the Application aggregate."""

    @abstractmethod
    def get_by_id(self, application_id: str) -> dict[str, Any] | None:
        """Get an application by id, or None."""
        ...

    @abstractmethod
    def get_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        """Get the application for a job, or None."""
        ...

    @abstractmethod
    def list_ids_by_job(self, job_id: str) -> list[str]:
        """List application ids belonging to a job (used by the delete cascade)."""
        ...

    @abstractmethod
    def statuses_by_job_ids(self, job_ids: list[str]) -> dict[str, str]:
        """Map job ids to their application status (``{job_id: status}``).

        Used by the jobs list to surface the job-tracking status. Jobs without
        an application are omitted from the result.
        """
        ...

    @abstractmethod
    def job_ids_with_application(self) -> list[str]:
        """List every job id that has at least one application.

        Used to resolve the ``not_applied`` tracking filter.
        """
        ...

    @abstractmethod
    def status_distribution(self) -> dict[str, Any]:
        """Count the user's applications grouped by status.

        Returns ``{"items": [{"status": ..., "count": ...}], "total": ...}``;
        zero-count statuses are omitted, known statuses follow the canonical
        lifecycle order, and ``total`` covers every status.
        """
        ...

    @abstractmethod
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create an application. Returns the stored dict."""
        ...

    @abstractmethod
    def update(self, application_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update application core fields (status, applied_at)."""
        ...

    @abstractmethod
    def delete_by_job(self, job_id: str) -> int:
        """Delete every application (and children) belonging to a job.

        Used by the job hard-delete cascade. Returns the number of applications
        deleted.
        """
        ...
