"""Router for Dify workflow integration.

This module provides API endpoints for integrating with Dify workflow engine,
including importing, executing, and synchronizing workflows.
"""

import logging
import httpx
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from services.dify_service import (
    DifyClient,
    DifyWorkflow,
    DifyWorkflowExecutionRequest,
    DifyWorkflowExecutionResponse,
    get_dify_client,
)
from services.playbook_dag_compiler import DAGCompiler

logger = get_logger(__name__)

router = APIRouter(prefix="/api/dify", tags=["dify"])


@router.get("/workflows")
async def list_dify_workflows(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """List all available workflows from Dify.

    Requires: analyst or admin role
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(
            status_code=403, detail="Only admins and analysts can list workflows"
        )

    try:
        client = get_dify_client()
        workflows = await client.list_workflows()

        return {
            "success": True,
            "workflows": workflows,
            "total": len(workflows),
        }

    except Exception as e:
        logger.error(f"Failed to list Dify workflows: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list workflows from Dify: {str(e)}"
        )


@router.get("/workflows/{app_id}")
async def get_dify_workflow(
    app_id: str,
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific workflow from Dify.

    Args:
        app_id: Dify application ID

    Requires: analyst or admin role
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(
            status_code=403, detail="Only admins and analysts can view workflows"
        )

    try:
        client = get_dify_client()
        workflow = await client.get_workflow(app_id)

        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {app_id}")

        return {
            "success": True,
            "workflow": workflow.model_dump(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Dify workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow from Dify: {str(e)}"
        )


@router.post("/workflows/{app_id}/execute")
async def execute_dify_workflow(
    app_id: str,
    request: DifyWorkflowExecutionRequest,
    current_user: UserModel = Depends(get_current_user),
) -> DifyWorkflowExecutionResponse:
    """Execute a Dify workflow.

    Args:
        app_id: Dify application ID
        request: Execution request with inputs

    Requires: analyst or admin role
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(
            status_code=403, detail="Only admins and analysts can execute workflows"
        )

    try:
        client = get_dify_client()
        result = await client.execute_workflow(
            app_id=app_id,
            inputs=request.inputs,
            user=current_user.username,
            mode=request.user,  # Use user field to pass mode
        )

        logger.info(
            f"Executed Dify workflow {app_id} as {current_user.username}, status: {result.status}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to execute Dify workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to execute workflow: {str(e)}"
        )


@router.post("/workflows/{app_id}/import")
async def import_dify_workflow(
    app_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Import a Dify workflow into SOC Copilot as a playbook definition.

    Args:
        app_id: Dify application ID to import
        db: Database session

    Requires: admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can import workflows")

    try:
        client = get_dify_client()
        dify_workflow = await client.get_workflow(app_id)

        if not dify_workflow:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {app_id}")

        # Convert Dify workflow to SOC Copilot DAG format
        from services.dify_adapter import DifyDAGAdapter

        adapter = DifyDAGAdapter()
        dag_definition = adapter.dify_to_dag(dify_workflow)

        # Create playbook definition
        from repositories.playbook_definition_repository import (
            PlaybookDefinitionRepository,
        )

        defn_repo = PlaybookDefinitionRepository(db)
        definition = await defn_repo.create(
            name=f"[Dify] {dify_workflow.name}",
            version="1.0.0",
            description=f"Imported from Dify: {dify_workflow.description}",
            dag_json=dag_definition,
            created_by_user_id=current_user.id,
            is_active=True,
        )

        # Store Dify app_id for future sync
        definition.dify_app_id = app_id
        await db.commit()

        logger.info(
            f"Imported Dify workflow {app_id} as playbook definition {definition.id}"
        )

        return {
            "success": True,
            "definition_id": definition.id,
            "definition_name": definition.name,
            "dify_app_id": app_id,
            "message": "Workflow imported successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import Dify workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to import workflow: {str(e)}"
        )


@router.post("/workflows/sync/{definition_id}")
async def sync_dify_workflow(
    definition_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Synchronize a playbook definition with its Dify workflow source.

    Args:
        definition_id: Playbook definition ID to sync
        db: Database session

    Requires: analyst or admin role
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(
            status_code=403, detail="Only admins and analysts can sync workflows"
        )

    try:
        from repositories.playbook_definition_repository import (
            PlaybookDefinitionRepository,
        )
        from services.dify_adapter import DifyDAGAdapter

        defn_repo = PlaybookDefinitionRepository(db)
        definition = await defn_repo.get_by_id(definition_id)

        if not definition:
            raise HTTPException(status_code=404, detail="Definition not found")

        dify_app_id = getattr(definition, "dify_app_id", None)
        if not dify_app_id:
            raise HTTPException(
                status_code=400, detail="Definition is not linked to a Dify workflow"
            )

        # Fetch updated workflow from Dify
        client = get_dify_client()
        dify_workflow = await client.get_workflow(dify_app_id)

        if not dify_workflow:
            raise HTTPException(
                status_code=404, detail=f"Dify workflow not found: {dify_app_id}"
            )

        # Convert and update definition
        adapter = DifyDAGAdapter()
        dag_definition = adapter.dify_to_dag(dify_workflow)

        # Increment version number
        new_version = f"1.{int(definition.version.split('.')[-1]) + 1}.0"

        await defn_repo.update(
            definition_id=definition_id,
            version=new_version,
            dag_json=dag_definition,
        )

        logger.info(
            f"Synced definition {definition_id} with Dify workflow {dify_app_id}"
        )

        return {
            "success": True,
            "definition_id": definition_id,
            "dify_app_id": dify_app_id,
            "message": "Workflow synchronized successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync Dify workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to sync workflow: {str(e)}"
        )


@router.get("/config")
async def get_dify_config(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current Dify configuration status.

    Requires: admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view Dify config")

    from core.config import settings

    api_url = getattr(settings, "dify_api_url", "")
    api_key = getattr(settings, "dify_api_key", "")
    workspace_id = getattr(settings, "dify_workspace_id", "")

    # Return API key prefix for display (first 20 chars)
    api_key_display = ""
    if api_key:
        api_key_display = api_key[:20] + "..." if len(api_key) > 20 else api_key

    # Check connection
    is_connected = False
    error_message = None
    if api_url and api_key:
        try:
            client = get_dify_client()
            http_client = await client._get_client()
            # Try to connect to Dify - any response (not connection error) means it's reachable
            # Use the root path or a lightweight endpoint
            resp = await http_client.get("/", timeout=5.0)
            # If we got any response (not a connection error), the server is reachable
            is_connected = True
        except httpx.ConnectError as e:
            error_message = f"Cannot connect to Dify: {str(e)}"
        except httpx.TimeoutException as e:
            error_message = f"Connection timeout: {str(e)}"
        except Exception as e:
            # Any other error (404, 401, 500, etc.) means the server is reachable
            # but the specific endpoint might not exist or auth failed
            is_connected = True

    return {
        "success": True,
        "configured": bool(api_url),
        "connected": is_connected,
        "api_url": api_url,
        "api_key": api_key_display,
        "workspace_id": workspace_id if is_connected else None,
        "error": error_message,
    }


@router.get("/test-connection")
async def test_dify_connection(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Test Dify connection.

    Requires: admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can test connection")

    from core.config import settings

    api_url = getattr(settings, "dify_api_url", "")
    api_key = getattr(settings, "dify_api_key", "")

    if not api_url or not api_key:
        return {
            "success": False,
            "connected": False,
            "message": "Dify is not configured. Please set API URL and API Key first.",
        }

    try:
        client = get_dify_client()
        # Test connection by making a simple HTTP request
        http_client = await client._get_client()
        resp = await http_client.get("/", timeout=5.0)

        # If we got any response (not a connection error), the connection works
        return {
            "success": True,
            "connected": True,
            "message": f"Successfully connected to Dify! (Status: {resp.status_code})",
            "status_code": resp.status_code,
        }

    except httpx.ConnectError as e:
        return {
            "success": False,
            "connected": False,
            "message": f"Cannot connect to Dify server",
            "error": str(e),
        }
    except httpx.TimeoutException as e:
        return {
            "success": False,
            "connected": False,
            "message": f"Connection timeout",
            "error": str(e),
        }
    except Exception as e:
        # Any other error (404, 401, 500, etc.) means the server is reachable
        return {
            "success": True,
            "connected": True,
            "message": f"Dify server is reachable (API endpoint verification needed)",
            "note": str(e),
        }


@router.delete("/workflows/{definition_id}")
async def delete_imported_workflow(
    definition_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Delete an imported Dify workflow playbook.

    Args:
        definition_id: Playbook definition ID to delete
        db: Database session

    Requires: admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only admins can delete imported workflows"
        )

    try:
        from repositories.playbook_definition_repository import (
            PlaybookDefinitionRepository,
        )

        defn_repo = PlaybookDefinitionRepository(db)
        definition = await defn_repo.get_by_id(definition_id)

        if not definition:
            raise HTTPException(status_code=404, detail="Definition not found")

        # Only allow deleting definitions that were imported from Dify
        dify_app_id = getattr(definition, "dify_app_id", None)
        if not dify_app_id:
            raise HTTPException(
                status_code=400,
                detail="Can only delete playbook definitions imported from Dify"
            )

        # Delete the definition
        await defn_repo.delete(definition_id)

        logger.info(
            f"Deleted imported Dify workflow definition {definition_id} (Dify app: {dify_app_id})"
        )

        return {
            "success": True,
            "definition_id": definition_id,
            "message": "Workflow deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete imported workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete workflow: {str(e)}"
        )
