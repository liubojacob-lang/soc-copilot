"""IOC Hits service for business logic."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from repositories.ioc_hit_repository import IOCHitRepository
from schemas.ioc_hit import (
    IOCHitCreate,
    IOCHitResponse,
    IOCHitListRequest,
    IOCHitListResponse,
    IOCType,
    IOCSource,
)

logger = get_logger(__name__)


class IOCHitsService:
    """Service for IOC hit management."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize IOC hits service.

        Args:
            session: Database session
        """
        self.session = session
        self.repository = IOCHitRepository()

    async def create(self, data: IOCHitCreate) -> IOCHitResponse:
        """Create a new IOC hit.

        Args:
            data: IOC hit creation data

        Returns:
            Created IOC hit
        """
        hit = await self.repository.create(self.session, data)
        logger.info(f"Created IOC hit: {hit.id} for IOC: {data.ioc_value}")
        return self._to_response(hit)

    async def get_by_id(self, hit_id: str) -> Optional[IOCHitResponse]:
        """Get IOC hit by ID.

        Args:
            hit_id: IOC hit ID

        Returns:
            IOC hit response or None
        """
        hit = await self.repository.get_by_id(self.session, hit_id)
        if not hit:
            return None
        return self._to_response(hit)

    async def list_by_ioc(
        self, ioc_value: str, limit: int = 100
    ) -> tuple[List[IOCHitResponse], int]:
        """List IOC hits by IOC value.

        Args:
            ioc_value: IOC value to search
            limit: Maximum results

        Returns:
            Tuple of (hits, total count)
        """
        hits = await self.repository.list_by_ioc(self.session, ioc_value, limit)
        total = await self.repository.count_by_ioc(self.session, ioc_value)
        return [self._to_response(h) for h in hits], total

    async def list_by_asset(
        self, asset_id: str, limit: int = 100
    ) -> tuple[List[IOCHitResponse], int]:
        """List IOC hits by asset ID.

        Args:
            asset_id: Asset ID
            limit: Maximum results

        Returns:
            Tuple of (hits, total)
        """
        hits = await self.repository.list_by_asset(self.session, asset_id, limit)
        return [self._to_response(h) for h in hits], len(hits)

    async def list_by_history(
        self, history_id: str, limit: int = 100
    ) -> List[IOCHitResponse]:
        """List IOC hits by history ID.

        Args:
            history_id: History record ID
            limit: Maximum results

        Returns:
            List of IOC hits
        """
        hits = await self.repository.list_by_history(self.session, history_id, limit)
        return [self._to_response(h) for h in hits]

    async def get_hits_by_iocs(
        self, ioc_values: List[str], limit: int = 20
    ) -> List[IOCHitResponse]:
        """Get recent IOC hits for given IOC values.

        Args:
            ioc_values: List of IOC values
            limit: Maximum results

        Returns:
            List of IOC hits
        """
        hits = await self.repository.get_recent_by_iocs(self.session, ioc_values, limit)
        return [self._to_response(h) for h in hits]

    async def create_from_analysis(
        self,
        history_id: str,
        ioc_type: str,
        ioc_value: str,
        source: str,
        asset_id: Optional[str] = None,
        confidence: int = 60,
        context_snippet: Optional[str] = None,
    ) -> Optional[IOCHitResponse]:
        """Create IOC hit from analysis result.

        Args:
            history_id: History record ID
            ioc_type: IOC type
            ioc_value: IOC value
            source: Source (local/llm)
            asset_id: Associated asset ID
            confidence: Confidence score
            context_snippet: Context snippet

        Returns:
            Created IOC hit or None if creation failed
        """
        try:
            data = IOCHitCreate(
                history_id=history_id,
                asset_id=asset_id,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                confidence=confidence,
                source=source,
                context_snippet=context_snippet,
            )
            return await self.create(data)
        except Exception as e:
            logger.warning(f"Failed to create IOC hit for {ioc_value}: {str(e)}")
            return None

    def _to_response(self, hit) -> IOCHitResponse:
        """Convert database model to response schema.

        Args:
            hit: IOC hit database model

        Returns:
            IOC hit response
        """
        return IOCHitResponse(
            id=hit.id,
            created_at=hit.created_at,
            history_id=hit.history_id,
            asset_id=hit.asset_id,
            ioc_type=hit.ioc_type,
            ioc_value=hit.ioc_value,
            confidence=hit.confidence,
            source=hit.source,
            context_snippet=hit.context_snippet,
            notes=hit.notes,
        )
