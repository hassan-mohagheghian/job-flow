"""Opportunity repository interfaces.

The opportunity aggregate owns its evaluations. Repositories expose CRUD for
the root plus lookup helpers used for dedupe (content hash, source message)
and listing (newest first, status/source/search filters).
"""

from abc import ABC, abstractmethod
from typing import Any


class IOpportunityRepository(ABC):
    """Data access for the opportunity aggregate root."""

    @abstractmethod
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a new opportunity and return it."""
        ...

    @abstractmethod
    def get_by_id(self, opportunity_id: str) -> dict[str, Any] | None:
        """Get an opportunity by id, or None."""
        ...

    @abstractmethod
    def get_by_content_hash(self, content_hash: str) -> dict[str, Any] | None:
        """Get an opportunity by content hash (duplicate detection), or None."""
        ...

    @abstractmethod
    def get_by_source_message(self, source: str, source_message_id: str) -> dict[str, Any] | None:
        """Get an opportunity by external source message id, or None."""
        ...

    @abstractmethod
    def list(
        self,
        status: str | None = None,
        source: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List opportunities newest first with optional filters.

        Returns (items, total).
        """
        ...

    @abstractmethod
    def update(self, opportunity_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an opportunity and return it, or None when missing."""
        ...

    @abstractmethod
    def delete(self, opportunity_id: str) -> bool:
        """Hard-delete an opportunity and its evaluations. Returns True when removed."""
        ...


class IOpportunityEvaluationRepository(ABC):
    """Data access for immutable evaluation snapshots."""

    @abstractmethod
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Append an evaluation snapshot and return it."""
        ...

    @abstractmethod
    def list_for_opportunity(self, opportunity_id: str) -> list[dict[str, Any]]:
        """List evaluation snapshots for an opportunity, newest first."""
        ...
