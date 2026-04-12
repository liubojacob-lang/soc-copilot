"""Repository for history CRUD operations."""

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.history import HistoryModel
from schemas.history import (
    HistoryCreate,
    HistoryResponse,
)


class HistoryRepository:
    """Repository for history operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session."""
        self.session = session

    async def create(self, data: HistoryCreate) -> HistoryModel:
        """Create a new history record."""
        history = HistoryModel(
            module=data.module,
            input_text=data.input_text,
            output_json=data.output_json,
            output_markdown=data.output_markdown,
            extracted_iocs=data.extracted_iocs or {},
            tags=data.tags,
            request_id=data.request_id,
            model_used=data.model_used,
            degraded=data.degraded or False,
            error_reason=data.error_reason,
        )
        self.session.add(history)
        await self.session.flush()

        # Enforce max 200 records - delete oldest if exceeded
        count_result = await self.session.execute(
            select(func.count()).select_from(HistoryModel)
        )
        count = count_result.scalar()

        if count > 200:
            # Find and delete oldest records
            oldest_records = await self.session.execute(
                select(HistoryModel)
                .order_by(HistoryModel.created_at.asc())
                .limit(count - 200)
            )
            for record in oldest_records.scalars():
                await self.session.delete(record)

        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def get_by_id(self, history_id: str) -> HistoryModel | None:
        """Get history record by ID."""
        result = await self.session.execute(
            select(HistoryModel).where(HistoryModel.id == history_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        module: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[HistoryModel]:
        """List history records with optional filters."""
        stmt = select(HistoryModel).order_by(HistoryModel.created_at.desc())

        if module:
            stmt = stmt.where(HistoryModel.module == module)

        if query:
            # Search in input_text, output_json (stringified), and extracted_iocs
            search_pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    HistoryModel.input_text.ilike(search_pattern),
                    HistoryModel.output_markdown.ilike(search_pattern),
                )
            )

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_id(self, history_id: str) -> bool:
        """Delete history record by ID."""
        result = await self.session.execute(
            delete(HistoryModel).where(HistoryModel.id == history_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def delete_all(self) -> int:
        """Delete all history records."""
        result = await self.session.execute(delete(HistoryModel))
        await self.session.commit()
        return result.rowcount

    @staticmethod
    def to_response(model: HistoryModel) -> HistoryResponse:
        """Convert model to response schema."""
        return HistoryResponse(
            id=model.id,
            module=model.module,
            created_at=model.created_at,
            input_text=model.input_text,
            output_json=model.output_json,
            output_markdown=model.output_markdown,
            extracted_iocs=model.extracted_iocs,
            tags=model.tags,
            request_id=model.request_id,
            model_used=model.model_used,
            degraded=model.degraded,
            error_reason=model.error_reason,
        )
