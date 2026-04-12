"""Repository for playbook output CRUD operations."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_output import PlaybookOutputModel
from schemas.playbook import (
    PlaybookOutputResponse,
)


class PlaybookRepository:
    """Repository for playbook output operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session."""
        self.session = session

    async def create(
        self,
        history_id: str | None,
        output_type: str,
        platform: str | None,
        output_json: dict[str, Any],
        request_id: str | None,
        degraded: bool,
        error_reason: str | None,
    ) -> PlaybookOutputModel:
        """Create a new playbook output record."""
        playbook_output = PlaybookOutputModel(
            history_id=history_id,
            output_type=output_type,
            platform=platform,
            output_json=output_json,
            request_id=request_id,
            degraded=degraded,
            error_reason=error_reason,
        )
        self.session.add(playbook_output)
        await self.session.flush()

        # Enforce max 100 playbook records per output_type
        count_result = await self.session.execute(
            select(func.count())
            .select_from(PlaybookOutputModel)
            .where(PlaybookOutputModel.output_type == output_type)
        )
        count = count_result.scalar()

        if count > 100:
            # Find and delete oldest records of same type
            oldest_records = await self.session.execute(
                select(PlaybookOutputModel)
                .where(PlaybookOutputModel.output_type == output_type)
                .order_by(PlaybookOutputModel.created_at.asc())
                .limit(count - 100)
            )
            for record in oldest_records.scalars():
                await self.session.delete(record)

        await self.session.commit()
        await self.session.refresh(playbook_output)
        return playbook_output

    async def get_by_id(self, output_id: str) -> PlaybookOutputModel | None:
        """Get playbook output by ID."""
        result = await self.session.execute(
            select(PlaybookOutputModel).where(PlaybookOutputModel.id == output_id)
        )
        return result.scalar_one_or_none()

    async def list_by_history(
        self,
        history_id: str,
        output_type: str | None = None,
        limit: int = 50,
    ) -> list[PlaybookOutputModel]:
        """List playbook outputs by history ID."""
        stmt = (
            select(PlaybookOutputModel)
            .where(PlaybookOutputModel.history_id == history_id)
            .order_by(PlaybookOutputModel.created_at.desc())
        )

        if output_type:
            stmt = stmt.where(PlaybookOutputModel.output_type == output_type)

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self,
        output_type: str | None = None,
        limit: int = 50,
    ) -> list[PlaybookOutputModel]:
        """List all playbook outputs with optional filter."""
        stmt = select(PlaybookOutputModel).order_by(
            PlaybookOutputModel.created_at.desc()
        )

        if output_type:
            stmt = stmt.where(PlaybookOutputModel.output_type == output_type)

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def to_response(model: PlaybookOutputModel) -> PlaybookOutputResponse:
        """Convert model to response schema."""
        return PlaybookOutputResponse(
            id=model.id,
            created_at=model.created_at,
            history_id=model.history_id,
            output_type=model.output_type,
            platform=model.platform,
            output_json=model.output_json,
            request_id=model.request_id,
            degraded=model.degraded,
            error_reason=model.error_reason,
        )
