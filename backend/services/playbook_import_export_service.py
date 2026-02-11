"""Playbook Import/Export Service for v0.7.3.

This service handles:
- Exporting playbook definitions to JSON or YAML
- Importing playbook definitions from JSON or YAML
- Format validation and conversion
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from models.playbook_definition import PlaybookDefinitionModel, PlaybookDefinitionStatus
from schemas.playbook_dag import (
    PlaybookExportData,
    PlaybookImportResponse,
    DAGSchema,
    NodeSchema,
    EdgeSchema
)

logger = logging.getLogger(__name__)


class PlaybookImportExportService:
    """Service for importing and exporting playbook definitions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_definition(
        self,
        definition_id: str,
        format: Literal["json", "yaml"] = "json"
    ) -> tuple[str, str]:
        """
        Export a playbook definition to JSON or YAML.

        Args:
            definition_id: ID of the definition to export
            format: Export format ('json' or 'yaml')

        Returns:
            Tuple of (content, mime_type)
        """
        # Get the definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition {definition_id} not found")

        # Build export data
        export_data = PlaybookExportData(
            name=definition.name,
            description=definition.description,
            version=definition.version,
            status=definition.status,
            current_version_no=definition.current_version_no,
            dag=DAGSchema(**definition.definition_json),
            created_at=definition.created_at,
            updated_at=definition.updated_at,
            created_by_user_id=definition.created_by
        )

        # Serialize
        if format == "yaml":
            if not YAML_AVAILABLE:
                raise ValueError("YAML format not available. Install pyyaml: pip install pyyaml")

            content = yaml.dump(
                export_data.model_dump(mode='json', exclude_none=True),
                default_flow_style=False,
                sort_keys=False
            )
            mime_type = "text/yaml"
        else:  # json
            content = json.dumps(
                export_data.model_dump(mode='json', exclude_none=True),
                indent=2
            )
            mime_type = "application/json"

        logger.info(f"Exported playbook definition {definition_id} as {format}")

        return content, mime_type

    async def import_definition(
        self,
        content: str,
        format: Literal["json", "yaml"] = "json",
        name_override: Optional[str] = None,
        publish: bool = False,
        created_by_user_id: Optional[str] = None
    ) -> PlaybookImportResponse:
        """
        Import a playbook definition from JSON or YAML.

        Args:
            content: Import content (JSON or YAML string)
            format: Import format ('json' or 'yaml')
            name_override: Optional override for playbook name
            publish: Whether to auto-publish after import (default: draft)
            created_by_user_id: ID of the user importing

        Returns:
            Import response with definition details
        """
        # Parse content
        if format == "yaml":
            if not YAML_AVAILABLE:
                raise ValueError("YAML format not available. Install pyyaml: pip install pyyaml")

            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML: {str(e)}")
        else:  # json
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {str(e)}")

        # Validate structure
        validated = self._validate_import_data(data)

        # Apply name override if provided
        if name_override:
            validated.name = name_override

        # Create new definition
        definition = PlaybookDefinitionModel(
            id=str(uuid.uuid4()),
            name=validated.name,
            description=validated.description,
            version=validated.version,
            definition_json=validated.dag.model_dump(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by=created_by_user_id,
            is_active=True,
            status=PlaybookDefinitionStatus.PUBLISHED if publish else PlaybookDefinitionStatus.DRAFT,
            published_at=datetime.now(timezone.utc) if publish else None,
            current_version_no=1
        )

        self.session.add(definition)
        await self.session.flush()

        logger.info(
            f"Imported playbook definition '{definition.name}' ({definition.id}) "
            f"as {definition.status}"
        )

        return PlaybookImportResponse(
            definition_id=definition.id,
            name=definition.name,
            version=definition.version,
            status=definition.status,
            message=f"Successfully imported '{definition.name}'"
        )

    def _validate_import_data(self, data: dict) -> PlaybookExportData:
        """
        Validate imported data structure.

        Args:
            data: Parsed import data

        Returns:
            Validated PlaybookExportData
        """
        # Check required fields
        if "name" not in data:
            raise ValueError("Missing required field: name")

        if "dag" not in data:
            raise ValueError("Missing required field: dag")

        # Validate DAG structure
        dag_data = data["dag"]
        if not isinstance(dag_data, dict):
            raise ValueError("dag must be an object")

        if "nodes" not in dag_data:
            raise ValueError("dag must contain 'nodes' field")

        # Auto-migrate old schema if needed
        dag_data = self._auto_migrate_dag_schema(dag_data)

        # Set defaults
        data.setdefault("version", "1.0.0")
        data.setdefault("description", None)

        try:
            return PlaybookExportData(**data)
        except Exception as e:
            raise ValueError(f"Invalid playbook structure: {str(e)}")

    def _auto_migrate_dag_schema(self, dag_data: dict) -> dict:
        """
        Auto-migrate old DAG schema to v0.7.3 format.

        Adds missing fields:
        - outputs_mapping to nodes
        - inputs_template to nodes

        Args:
            dag_data: Original DAG data

        Returns:
            Migrated DAG data
        """
        migrated = dag_data.copy()

        for node in migrated.get("nodes", []):
            # Add outputs_mapping if missing
            if "outputs_mapping" not in node:
                node["outputs_mapping"] = {}

            # Add inputs_template if missing
            if "inputs_template" not in node:
                # Migrate old 'inputs' to 'inputs_template' if needed
                if "inputs" in node and isinstance(node["inputs"], dict):
                    node["inputs_template"] = node["inputs"].copy()
                else:
                    node["inputs_template"] = {}

        return migrated

    async def validate_import_format(self, content: str, format: Literal["json", "yaml"]) -> bool:
        """
        Validate if content is valid JSON or YAML.

        Args:
            content: Content to validate
            format: Expected format

        Returns:
            True if valid, False otherwise
        """
        try:
            if format == "yaml":
                if not YAML_AVAILABLE:
                    return False
                yaml.safe_load(content)
            else:  # json
                json.loads(content)
            return True
        except:
            return False


# Singleton factory function
def get_import_export_service(session: AsyncSession) -> PlaybookImportExportService:
    """Get import/export service instance."""
    return PlaybookImportExportService(session)
