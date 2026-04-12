"""Playbook Version Service for v0.7.3.

This service handles:
- Version snapshot creation on definition updates
- Publishing draft definitions
- Version history retrieval
- Restoring from historical versions
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_definition import (
    PlaybookDefinitionModel,
    PlaybookDefinitionStatus,
    PlaybookDefinitionVersionModel,
)
from schemas.playbook_dag import (
    PlaybookDefinitionVersionOut,
    PlaybookVersionListResponse,
)

logger = logging.getLogger(__name__)


class PlaybookVersionService:
    """Service for managing playbook definition versions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_version_snapshot(
        self,
        definition_id: str,
        change_note: str | None = None,
        created_by_user_id: str | None = None,
    ) -> PlaybookDefinitionVersionModel:
        """
        Create a version snapshot of a playbook definition.

        Args:
            definition_id: ID of the definition to snapshot
            change_note: Optional note describing the change
            created_by_user_id: ID of the user creating the version

        Returns:
            Created version model
        """
        # Get the definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition {definition_id} not found")

        # Get current max version number
        version_stmt = (
            select(PlaybookDefinitionVersionModel)
            .where(
                PlaybookDefinitionVersionModel.playbook_definition_id == definition_id
            )
            .order_by(PlaybookDefinitionVersionModel.version_no.desc())
        )

        version_result = await self.session.execute(version_stmt)
        last_version = version_result.first()

        # Calculate new version number
        new_version_no = 1
        if last_version:
            new_version_no = last_version[0].version_no + 1

        # Create version snapshot
        version = PlaybookDefinitionVersionModel(
            id=str(uuid.uuid4()),
            playbook_definition_id=definition_id,
            version_no=new_version_no,
            dag_json=definition.definition_json.copy(),
            name=definition.name,
            description=definition.description,
            created_by_user_id=created_by_user_id,
            created_at=datetime.now(UTC),
            change_note=change_note,
        )

        self.session.add(version)

        # Update definition's current version
        definition.current_version_no = new_version_no

        await self.session.flush()

        logger.info(
            f"Created version snapshot v{new_version_no} for definition {definition_id}"
        )

        return version

    async def publish_definition(
        self,
        definition_id: str,
        change_note: str | None = None,
        created_by_user_id: str | None = None,
    ) -> PlaybookDefinitionModel:
        """
        Publish a draft playbook definition.

        This creates a version snapshot and sets the status to published.
        Published definitions cannot be modified (must create new version).

        Args:
            definition_id: ID of the definition to publish
            change_note: Optional note for the published version
            created_by_user_id: ID of the user publishing

        Returns:
            Updated definition model
        """
        # Get the definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition {definition_id} not found")

        if definition.status == PlaybookDefinitionStatus.PUBLISHED:
            raise ValueError(f"Definition {definition_id} is already published")

        if definition.status == PlaybookDefinitionStatus.ARCHIVED:
            raise ValueError(f"Cannot publish archived definition {definition_id}")

        # Create version snapshot
        await self.create_version_snapshot(
            definition_id=definition_id,
            change_note=change_note or "Published",
            created_by_user_id=created_by_user_id,
        )

        # Update definition status
        definition.status = PlaybookDefinitionStatus.PUBLISHED
        definition.published_at = datetime.now(UTC)

        await self.session.flush()

        logger.info(f"Published playbook definition {definition_id}")

        return definition

    async def get_version_history(
        self, definition_id: str
    ) -> PlaybookVersionListResponse:
        """
        Get version history for a playbook definition.

        Args:
            definition_id: ID of the definition

        Returns:
            Version history response
        """
        # Get the definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition {definition_id} not found")

        # Get all versions
        version_stmt = (
            select(PlaybookDefinitionVersionModel)
            .where(
                PlaybookDefinitionVersionModel.playbook_definition_id == definition_id
            )
            .order_by(PlaybookDefinitionVersionModel.version_no.desc())
        )

        version_result = await self.session.execute(version_stmt)
        versions = version_result.scalars().all()

        # Convert to output schema
        version_outputs = [
            PlaybookDefinitionVersionOut.model_validate(v) for v in versions
        ]

        return PlaybookVersionListResponse(
            definition_id=definition_id,
            versions=version_outputs,
            total=len(version_outputs),
            current_version_no=definition.current_version_no,
        )

    async def restore_from_version(
        self,
        definition_id: str,
        version_no: int,
        change_note: str | None = None,
        created_by_user_id: str | None = None,
    ) -> PlaybookDefinitionModel:
        """
        Restore a playbook definition from a historical version.

        This creates a new draft with the content from the specified version.
        The original version is preserved.

        Args:
            definition_id: ID of the definition to restore
            version_no: Version number to restore from
            change_note: Optional note for the restoration
            created_by_user_id: ID of the user restoring

        Returns:
            Updated definition model
        """
        # Get the definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition {definition_id} not found")

        # Get the version to restore
        version_stmt = select(PlaybookDefinitionVersionModel).where(
            PlaybookDefinitionVersionModel.playbook_definition_id == definition_id,
            PlaybookDefinitionVersionModel.version_no == version_no,
        )
        version_result = await self.session.execute(version_stmt)
        version = version_result.scalar_one_or_none()

        if not version:
            raise ValueError(
                f"Version {version_no} not found for definition {definition_id}"
            )

        # If definition is published, we need to create a new version as draft
        if definition.status == PlaybookDefinitionStatus.PUBLISHED:
            # Reset to draft
            definition.status = PlaybookDefinitionStatus.DRAFT
            definition.published_at = None
            logger.info(f"Reset definition {definition_id} to draft for restoration")

        # Restore the DAG from version
        definition.definition_json = version.dag_json.copy()
        definition.name = version.name or definition.name
        definition.description = version.description or definition.description
        definition.updated_at = datetime.now(UTC)

        # Increment version number
        definition.current_version_no += 1

        await self.session.flush()

        logger.info(
            f"Restored definition {definition_id} from version {version_no}, "
            f"now at version {definition.current_version_no}"
        )

        return definition

    async def validate_can_modify(self, definition_id: str) -> bool:
        """
        Check if a definition can be modified.

        Args:
            definition_id: ID of the definition

        Returns:
            True if can modify, False otherwise
        """
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            return False

        return definition.can_modify

    async def archive_definition(self, definition_id: str) -> PlaybookDefinitionModel:
        """
        Archive a playbook definition.

        Args:
            definition_id: ID of the definition to archive

        Returns:
            Updated definition model
        """
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition {definition_id} not found")

        definition.status = PlaybookDefinitionStatus.ARCHIVED
        definition.is_active = False

        await self.session.flush()

        logger.info(f"Archived playbook definition {definition_id}")

        return definition
