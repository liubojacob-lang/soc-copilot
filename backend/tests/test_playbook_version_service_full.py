"""Unit tests for PlaybookVersionService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.playbook_definition import (
    PlaybookDefinitionModel,
    PlaybookDefinitionStatus,
    PlaybookDefinitionVersionModel,
)
from services.playbook.playbook_version_service import PlaybookVersionService


def _make_definition_model(
    def_id="def-100",
    name="Test Playbook",
    status=PlaybookDefinitionStatus.DRAFT,
    current_version_no=1,
):
    model = PlaybookDefinitionModel(
        id=def_id,
        name=name,
        description="Description of playbook",
        version="1.0.0",
        status=status,
        current_version_no=current_version_no,
        definition_json={"nodes": [{"id": "n1", "type": "sleep"}], "edges": []},
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="user-admin",
    )
    return model


@pytest.mark.asyncio
async def test_create_version_snapshot_and_not_found():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    service = PlaybookVersionService(session)

    # 1. Not found
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res_none)

    with pytest.raises(ValueError) as exc:
        await service.create_version_snapshot("nonexistent-def")
    assert "not found" in str(exc.value)

    # 2. Success snapshot (no previous version -> version_no=1)
    definition = _make_definition_model()
    mock_res_def = MagicMock()
    mock_res_def.scalar_one_or_none.return_value = definition

    mock_res_prev = MagicMock()
    mock_res_prev.first.return_value = None  # no previous version

    session.execute = AsyncMock(side_effect=[mock_res_def, mock_res_prev])

    version = await service.create_version_snapshot(
        definition_id="def-100",
        change_note="Initial version snapshot",
        created_by_user_id="user-1",
    )
    assert version.version_no == 1
    assert version.playbook_definition_id == "def-100"
    assert definition.current_version_no == 1
    session.add.assert_called_once()
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_publish_definition_flow():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    service = PlaybookVersionService(session)

    # 1. Publish draft definition
    definition = _make_definition_model(status=PlaybookDefinitionStatus.DRAFT)
    mock_res_def = MagicMock()
    mock_res_def.scalar_one_or_none.return_value = definition
    mock_res_prev = MagicMock()
    mock_res_prev.first.return_value = None

    session.execute = AsyncMock(side_effect=[mock_res_def, mock_res_def, mock_res_prev])

    published = await service.publish_definition("def-100", change_note="Release v1.0")
    assert published.status == PlaybookDefinitionStatus.PUBLISHED
    assert published.published_at is not None

    # 2. Already published
    mock_res_already = MagicMock()
    mock_res_already.scalar_one_or_none.return_value = published
    session.execute = AsyncMock(return_value=mock_res_already)

    with pytest.raises(ValueError) as exc:
        await service.publish_definition("def-100")
    assert "already published" in str(exc.value)

    # 3. Archived cannot be published
    archived_def = _make_definition_model(status=PlaybookDefinitionStatus.ARCHIVED)
    mock_res_archived = MagicMock()
    mock_res_archived.scalar_one_or_none.return_value = archived_def
    session.execute = AsyncMock(return_value=mock_res_archived)

    with pytest.raises(ValueError) as exc:
        await service.publish_definition("def-100")
    assert "Cannot publish archived" in str(exc.value)


@pytest.mark.asyncio
async def test_get_version_history():
    session = AsyncMock()
    service = PlaybookVersionService(session)

    definition = _make_definition_model()
    mock_res_def = MagicMock()
    mock_res_def.scalar_one_or_none.return_value = definition

    v1 = PlaybookDefinitionVersionModel(
        id=str(uuid.uuid4()),
        playbook_definition_id="def-100",
        version_no=1,
        name="Playbook v1",
        description="desc",
        dag_json={"nodes": [], "edges": []},
        created_at=datetime.now(UTC),
        created_by_user_id="user-1",
        change_note="v1 note",
    )
    v2 = PlaybookDefinitionVersionModel(
        id=str(uuid.uuid4()),
        playbook_definition_id="def-100",
        version_no=2,
        name="Playbook v2",
        description="desc",
        dag_json={"nodes": [], "edges": []},
        created_at=datetime.now(UTC),
        created_by_user_id="user-1",
        change_note="v2 note",
    )

    mock_res_versions = MagicMock()
    mock_res_versions.scalars.return_value.all.return_value = [v2, v1]

    session.execute = AsyncMock(side_effect=[mock_res_def, mock_res_versions])

    history = await service.get_version_history("def-100")
    assert history.definition_id == "def-100"
    assert history.total == 2
    assert len(history.versions) == 2
    assert history.versions[0].version_no == 2


@pytest.mark.asyncio
async def test_restore_from_version():
    session = AsyncMock()
    session.flush = AsyncMock()
    service = PlaybookVersionService(session)

    definition = _make_definition_model(
        status=PlaybookDefinitionStatus.PUBLISHED, current_version_no=3
    )
    mock_res_def = MagicMock()
    mock_res_def.scalar_one_or_none.return_value = definition

    hist_version = PlaybookDefinitionVersionModel(
        id="v-1",
        playbook_definition_id="def-100",
        version_no=1,
        name="Old Name",
        description="Old Description",
        dag_json={"nodes": [{"id": "old_node"}], "edges": []},
        created_at=datetime.now(UTC),
    )
    mock_res_ver = MagicMock()
    mock_res_ver.scalar_one_or_none.return_value = hist_version

    session.execute = AsyncMock(side_effect=[mock_res_def, mock_res_ver])

    restored = await service.restore_from_version("def-100", version_no=1)
    assert restored.status == PlaybookDefinitionStatus.DRAFT
    assert restored.current_version_no == 4
    assert restored.name == "Old Name"
    assert restored.definition_json["nodes"][0]["id"] == "old_node"
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_validate_can_modify_and_archive():
    session = AsyncMock()
    session.flush = AsyncMock()
    service = PlaybookVersionService(session)

    definition = _make_definition_model(status=PlaybookDefinitionStatus.DRAFT)
    mock_res_def = MagicMock()
    mock_res_def.scalar_one_or_none.return_value = definition
    session.execute = AsyncMock(return_value=mock_res_def)

    # 1. validate_can_modify
    can_mod = await service.validate_can_modify("def-100")
    assert can_mod is True

    # 2. archive_definition
    archived = await service.archive_definition("def-100")
    assert archived.status == PlaybookDefinitionStatus.ARCHIVED
    assert archived.is_active is False
    session.flush.assert_awaited()
