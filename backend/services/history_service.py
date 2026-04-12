"""History service for managing analysis history."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.history_repository import HistoryRepository
from schemas.history import (
    HistoryCreate,
    HistoryListResponse,
    HistoryResponse,
)


class HistoryService:
    """Service for history operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize history service."""
        self.repository = HistoryRepository(session)

    async def create_history(
        self,
        module: str,
        input_text: str,
        output_json: dict[str, Any],
        output_markdown: str | None = None,
        extracted_iocs: dict[str, list[str]] | None = None,
        tags: dict[str, Any] | None = None,
        request_id: str | None = None,
        model_used: str | None = None,
        degraded: bool = False,
        error_reason: str | None = None,
    ) -> HistoryResponse:
        """Create a new history record.

        Args:
            module: Module name (analyzer, report, timeline)
            input_text: Original input text
            output_json: Model output JSON
            output_markdown: Rendered markdown
            extracted_iocs: Extracted IOCs
            tags: Optional tags
            request_id: Request ID
            model_used: Model used
            degraded: Whether degraded mode was used
            error_reason: Error reason if degraded

        Returns:
            Created history response
        """
        data = HistoryCreate(
            module=module,
            input_text=input_text,
            output_json=output_json,
            output_markdown=output_markdown,
            extracted_iocs=extracted_iocs or {},
            tags=tags,
            request_id=request_id,
            model_used=model_used,
            degraded=degraded,
            error_reason=error_reason,
        )

        model = await self.repository.create(data)
        return self.repository.to_response(model)

    async def get_history(self, history_id: str) -> HistoryResponse | None:
        """Get history record by ID.

        Args:
            history_id: History record ID

        Returns:
            History response or None
        """
        model = await self.repository.get_by_id(history_id)
        if model is None:
            return None
        return self.repository.to_response(model)

    async def list_history(
        self,
        module: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> HistoryListResponse:
        """List history records.

        Args:
            module: Filter by module
            query: Search query
            limit: Max records to return

        Returns:
            History list response
        """
        models = await self.repository.list(module=module, query=query, limit=limit)
        items = [self.repository.to_response(m) for m in models]
        return HistoryListResponse(items=items, total=len(items))

    async def delete_history(self, history_id: str) -> bool:
        """Delete history record by ID.

        Args:
            history_id: History record ID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_by_id(history_id)

    async def delete_all_history(self) -> int:
        """Delete all history records.

        Returns:
            Number of records deleted
        """
        return await self.repository.delete_all()
