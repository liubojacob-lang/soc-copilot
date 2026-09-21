"""Marketplace repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.marketplace import (
    MarketplacePlaybookModel,
    MarketplacePlaybookStatus,
    MarketplaceReviewModel,
)
from models.playbook_definition import PlaybookDefinitionModel
from schemas.marketplace import (
    MarketplacePlaybookCreate,
    MarketplaceReviewCreate,
)


class MarketplaceRepository:
    """Repository for marketplace operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_playbook(
        self,
        definition: PlaybookDefinitionModel,
        data: MarketplacePlaybookCreate,
        author_id: str,
        author_name: str,
    ) -> MarketplacePlaybookModel:
        playbook = MarketplacePlaybookModel(
            id=str(uuid.uuid4()),
            name=definition.name,
            description=definition.description,
            version=definition.version,
            category=data.category,
            difficulty=data.difficulty,
            tags=data.tags,
            author_id=author_id,
            author_name=author_name,
            source_definition_id=definition.id,
            dag_json=definition.definition_json,
            documentation=None,
            status=MarketplacePlaybookStatus.PENDING,
            required_plugins=data.required_plugins,
            compatible_versions=data.compatible_versions,
        )
        self.db.add(playbook)
        await self.db.commit()
        await self.db.refresh(playbook)
        return playbook

    async def get_playbook(self, playbook_id: str) -> MarketplacePlaybookModel | None:
        result = await self.db.execute(
            select(MarketplacePlaybookModel).where(
                MarketplacePlaybookModel.id == playbook_id
            )
        )
        return result.scalar_one_or_none()

    async def get_playbooks(
        self,
        query: str | None = None,
        category: str | None = None,
        difficulty: str | None = None,
        tags: list[str] | None = None,
        min_rating: float | None = None,
        verified_only: bool = False,
        status: str | None = None,
        sort_by: str = "rating",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MarketplacePlaybookModel], int]:
        filters = []

        if status:
            filters.append(MarketplacePlaybookModel.status == status)
        else:
            filters.append(
                MarketplacePlaybookModel.status == MarketplacePlaybookStatus.APPROVED
            )

        if query:
            q = f"%{query.lower()}%"
            filters.append(
                or_(
                    func.lower(MarketplacePlaybookModel.name).ilike(q),
                    func.lower(MarketplacePlaybookModel.description).ilike(q),
                )
            )

        if category:
            filters.append(MarketplacePlaybookModel.category == category)

        if difficulty:
            filters.append(MarketplacePlaybookModel.difficulty == difficulty)

        if min_rating:
            filters.append(MarketplacePlaybookModel.rating_average >= min_rating)

        if verified_only:
            filters.append(MarketplacePlaybookModel.verified == True)

        stmt = select(MarketplacePlaybookModel).where(and_(*filters))

        count_result = await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar() or 0

        if sort_by == "rating":
            stmt = stmt.order_by(
                desc(MarketplacePlaybookModel.rating_average),
                desc(MarketplacePlaybookModel.download_count),
            )
        elif sort_by == "downloads":
            stmt = stmt.order_by(desc(MarketplacePlaybookModel.download_count))
        elif sort_by == "newest":
            stmt = stmt.order_by(desc(MarketplacePlaybookModel.created_at))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        playbooks = list(result.scalars().all())

        return playbooks, total

    async def approve_playbook(
        self,
        playbook_id: str,
        reviewer_id: str,
        approved: bool,
        review_note: str | None,
        featured: bool = False,
        verified: bool = False,
    ) -> MarketplacePlaybookModel | None:
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            return None

        playbook.status = (
            MarketplacePlaybookStatus.APPROVED
            if approved
            else MarketplacePlaybookStatus.REJECTED
        )
        playbook.reviewed_by = reviewer_id
        playbook.reviewed_at = datetime.now(UTC)
        playbook.review_note = review_note

        if approved:
            playbook.featured = featured
            playbook.verified = verified

        await self.db.commit()
        await self.db.refresh(playbook)
        return playbook

    async def increment_download(self, playbook_id: str) -> None:
        playbook = await self.get_playbook(playbook_id)
        if playbook:
            playbook.download_count += 1
            await self.db.commit()

    async def create_review(
        self,
        playbook_id: str,
        user_id: str,
        username: str,
        data: MarketplaceReviewCreate,
    ) -> MarketplaceReviewModel | None:
        playbook = await self.get_playbook(playbook_id)
        if not playbook:
            return None

        existing = await self.db.execute(
            select(MarketplaceReviewModel).where(
                and_(
                    MarketplaceReviewModel.playbook_id == playbook_id,
                    MarketplaceReviewModel.user_id == user_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            return None

        review = MarketplaceReviewModel(
            id=str(uuid.uuid4()),
            playbook_id=playbook_id,
            user_id=user_id,
            username=username,
            rating=data.rating,
            comment=data.comment,
        )
        self.db.add(review)

        await self._update_playbook_stats(playbook_id)

        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def _update_playbook_stats(self, playbook_id: str) -> None:
        stats = await self.db.execute(
            select(
                func.count(MarketplaceReviewModel.id).label("count"),
                func.avg(MarketplaceReviewModel.rating).label("avg_rating"),
                func.count(MarketplaceReviewModel.comment).label("review_count"),
            ).where(MarketplaceReviewModel.playbook_id == playbook_id)
        )
        row = stats.one()

        playbook = await self.get_playbook(playbook_id)
        if playbook:
            playbook.rating_count = row.count or 0
            playbook.rating_average = float(row.avg_rating or 0.0)
            playbook.review_count = row.review_count or 0

    async def get_reviews(
        self, playbook_id: str, page: int = 1, page_size: int = 10
    ) -> list[MarketplaceReviewModel]:
        result = await self.db.execute(
            select(MarketplaceReviewModel)
            .where(MarketplaceReviewModel.playbook_id == playbook_id)
            .order_by(desc(MarketplaceReviewModel.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def get_categories(self) -> list[dict]:
        result = await self.db.execute(
            select(
                MarketplacePlaybookModel.category,
                func.count(MarketplacePlaybookModel.id).label("count"),
            )
            .where(
                MarketplacePlaybookModel.status == MarketplacePlaybookStatus.APPROVED
            )
            .group_by(MarketplacePlaybookModel.category)
        )
        return [
            {
                "id": row.category,
                "name": row.category.replace("_", " ").title(),
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_featured(self, limit: int = 5) -> list[MarketplacePlaybookModel]:
        result = await self.db.execute(
            select(MarketplacePlaybookModel)
            .where(
                and_(
                    MarketplacePlaybookModel.status
                    == MarketplacePlaybookStatus.APPROVED,
                    MarketplacePlaybookModel.featured == True,
                )
            )
            .order_by(desc(MarketplacePlaybookModel.rating_average))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_trending(self, limit: int = 5) -> list[MarketplacePlaybookModel]:
        result = await self.db.execute(
            select(MarketplacePlaybookModel)
            .where(
                MarketplacePlaybookModel.status == MarketplacePlaybookStatus.APPROVED
            )
            .order_by(desc(MarketplacePlaybookModel.download_count))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self) -> dict:
        result = await self.db.execute(
            select(
                func.count(MarketplacePlaybookModel.id).label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                MarketplacePlaybookModel.status
                                == MarketplacePlaybookStatus.PENDING,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("pending"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                MarketplacePlaybookModel.status
                                == MarketplacePlaybookStatus.APPROVED,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("approved"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                MarketplacePlaybookModel.status
                                == MarketplacePlaybookStatus.REJECTED,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("rejected"),
                func.coalesce(
                    func.sum(
                        case((MarketplacePlaybookModel.featured == True, 1), else_=0)
                    ),
                    0,
                ).label("featured"),
                func.coalesce(
                    func.sum(
                        case((MarketplacePlaybookModel.verified == True, 1), else_=0)
                    ),
                    0,
                ).label("verified"),
                func.coalesce(
                    func.sum(MarketplacePlaybookModel.download_count), 0
                ).label("downloads"),
            )
        )
        row = result.one()

        review_count = await self.db.execute(
            select(func.count(MarketplaceReviewModel.id))
        )
        total_reviews = review_count.scalar() or 0

        return {
            "total_playbooks": row.total or 0,
            "pending_review": row.pending or 0,
            "approved": row.approved or 0,
            "rejected": row.rejected or 0,
            "featured": row.featured or 0,
            "verified": row.verified or 0,
            "total_downloads": row.downloads or 0,
            "total_reviews": total_reviews,
        }
