"""Dify workflow integration service.

This module provides integration with Dify workflow engine,
allowing SOC Copilot to import, edit, and execute Dify workflows.
"""

import httpx
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class DifyConfig:
    """Dify configuration settings."""

    def __init__(self):
        self.api_url = getattr(settings, "dify_api_url", "http://localhost:3001")
        self.api_key = getattr(settings, "dify_api_key", "")
        self.workspace_id = getattr(settings, "dify_workspace_id", "")
        self.timeout = 30


class DifyWorkflowNode(BaseModel):
    """Dify workflow node model."""
    id: str
    type: str = Field(..., description="Node type (e.g., 'start', 'llm', 'code', 'if-else')")
    data: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    target: Optional[str] = Field(None, description="Target node for edges")


class DifyWorkflowEdge(BaseModel):
    """Dify workflow edge model."""
    id: str
    source: str
    target: str
    data: Dict[str, Any] = Field(default_factory=dict)


class DifyWorkflow(BaseModel):
    """Dify workflow model."""
    id: Optional[str] = None
    app_id: Optional[str] = None
    name: str
    description: str = ""
    mode: str = "workflow"
    version: str = "1.0.0"
    graph: Dict[str, Any] = Field(default_factory=dict)
    environment_variables: List[Dict[str, str]] = Field(default_factory=list)
    conversation_variables: List[Dict[str, str]] = Field(default_factory=list)


class DifyWorkflowExecutionRequest(BaseModel):
    """Request to execute a Dify workflow."""
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Workflow input variables")
    user: str = "soc-copilot"
    response_mode: str = "blocking"  # blocking | streaming
    files: List[str] = Field(default_factory=list)


class DifyWorkflowExecutionResponse(BaseModel):
    """Response from Dify workflow execution."""
    workflow_id: str
    task_id: str
    status: str
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_metadata: Optional[Dict[str, Any]] = None


class DifyClient:
    """Client for Dify API interactions."""

    def __init__(self, config: Optional[DifyConfig] = None):
        self.config = config or DifyConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper authentication."""
        if self._client is None:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.config.api_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows from Dify.

        Returns:
            List of workflow metadata
        """
        try:
            client = await self._get_client()

            # Check if we have a platform/workspace API key (starts with 'pat-' or 'platform-')
            # or an app-level API key (starts with 'app-')
            api_key = self.config.api_key or ""

            if api_key.startswith("app-"):
                # App-level key: can only access the single app associated with this key
                # Use the workflow execution API to get basic app info
                logger.info("Using app-level API key - will attempt to fetch the associated app")

                # Try to get app info from the execution API endpoint
                response = await client.post("/v1/workflows/run", json={
                    "inputs": {},
                    "response_mode": "blocking",
                    "user": "soc-copilot"
                }, timeout=5.0)

                # If we get a response (even an error about inputs), the app exists
                # Extract app ID from error message or try to get app details
                if response.status_code in (400, 401):
                    # App exists but needs proper inputs
                    return [{
                        "id": self._extract_app_id_from_key(api_key),
                        "name": "Dify App (app-level key)",
                        "description": "Use the app ID from your Dify Console",
                        "mode": "workflow",
                        "created_at": "",
                    }]
                elif response.status_code == 404:
                    logger.warning("App not found with the provided API key")
                    return []

                # If successful, we got some data back
                return [{
                    "id": "unknown",
                    "name": "Dify App",
                    "description": "Connected via app-level API key",
                    "mode": "workflow",
                    "created_at": "",
                }]

            else:
                # Platform/workspace API key: try to fetch all apps
                response = await client.get("/console/api/apps")
                response.raise_for_status()

                data = response.json()

                # Handle different response formats
                if isinstance(data, dict):
                    apps = data.get("apps", data.get("data", data.get("items", [])))
                else:
                    apps = data if isinstance(data, list) else []

                # Format workflows
                workflows = []
                for app in apps:
                    if isinstance(app, dict):
                        workflows.append({
                            "id": app.get("id", ""),
                            "name": app.get("name", ""),
                            "description": app.get("description", ""),
                            "mode": app.get("mode", "workflow"),
                            "created_at": app.get("created_at", ""),
                        })

                logger.info(f"Retrieved {len(workflows)} workflows from Dify")
                return workflows

        except httpx.HTTPStatusError as e:
            logger.warning(f"Dify API error when listing workflows: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to list Dify workflows: {e}")
            return []

    def _extract_app_id_from_key(self, api_key: str) -> str:
        """Extract app ID from API key if possible.

        For app-level keys, the actual app ID needs to be obtained from Dify Console.
        This is a placeholder - users should manually enter their app ID.
        """
        # app-level keys don't contain the app ID
        return "enter-your-app-id"

    async def get_workflow(self, app_id: str) -> Optional[DifyWorkflow]:
        """Get a specific workflow by app ID.

        Args:
            app_id: Dify application ID

        Returns:
            Dify workflow or None if not found
        """
        try:
            client = await self._get_client()
            # Dify 1.12.x uses /console/api/apps/{app_id} for app details
            response = await client.get(f"/console/api/apps/{app_id}")
            response.raise_for_status()

            data = response.json()
            # Handle different response formats
            if isinstance(data, dict):
                app_data = data.get("app", data)
            else:
                app_data = data

            # Extract workflow graph if available
            graph = {}
            if isinstance(app_data, dict):
                # Dify stores workflow in different formats
                graph = app_data.get("graph", {})
                if not graph and "mode" in app_data:
                    # Workflow mode app
                    graph = app_data.get("workflow", {})

            return DifyWorkflow(
                id=app_data.get("id") if isinstance(app_data, dict) else str(app_data),
                app_id=app_data.get("id") if isinstance(app_data, dict) else str(app_data),
                name=app_data.get("name", "") if isinstance(app_data, dict) else "",
                description=app_data.get("description", "") if isinstance(app_data, dict) else "",
                mode=app_data.get("mode", "workflow") if isinstance(app_data, dict) else "workflow",
                graph=graph,
                environment_variables=app_data.get("environment_variables", []) if isinstance(app_data, dict) else [],
                conversation_variables=app_data.get("conversation_variables", []) if isinstance(app_data, dict) else [],
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Workflow not found: {app_id}")
                return None
            logger.error(f"Dify API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to get Dify workflow: {e}")
            return None

    async def execute_workflow(
        self,
        app_id: str,
        inputs: Dict[str, Any],
        user: str = "soc-copilot",
        mode: str = "dry_run"
    ) -> DifyWorkflowExecutionResponse:
        """Execute a Dify workflow.

        Args:
            app_id: Dify application ID
            inputs: Input variables for the workflow
            user: User identifier
            mode: Execution mode (dry_run or apply)

        Returns:
            Execution response with outputs and status
        """
        try:
            client = await self._get_client()

            # Add dry_run mode to inputs
            execution_inputs = {**inputs, "_mode": mode}

            # Dify 1.12.x uses /console/api/apps/{app_id}/run for workflow execution
            response = await client.post(
                f"/console/api/apps/{app_id}/run",
                json={
                    "inputs": execution_inputs,
                    "user": user,
                    "response_mode": "blocking",
                    "files": [],
                }
            )
            response.raise_for_status()

            data = response.json()

            # Handle different response formats
            if isinstance(data, dict):
                result_data = data.get("data", data)
            else:
                result_data = {"result": data}

            return DifyWorkflowExecutionResponse(
                workflow_id=app_id,
                task_id=data.get("task_id", data.get("run_id", "")),
                status=data.get("status", "success"),
                outputs=result_data,
                error=data.get("error"),
                execution_metadata=data.get("metadata", {}),
            )

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Dify execution error: {e.response.status_code} - {error_text}")

            # Return error response instead of raising
            return DifyWorkflowExecutionResponse(
                workflow_id=app_id,
                task_id="",
                status="failed",
                error=f"HTTP {e.response.status_code}: {error_text}"
            )
        except Exception as e:
            logger.error(f"Failed to execute Dify workflow: {e}")

            return DifyWorkflowExecutionResponse(
                workflow_id=app_id,
                task_id="",
                status="failed",
                error=str(e)
            )

    async def import_workflow_to_dify(
        self,
        workflow: DifyWorkflow
    ) -> Optional[str]:
        """Import a SOC Copilot workflow into Dify.

        Args:
            workflow: Workflow to import

        Returns:
            Created app ID or None if failed
        """
        try:
            client = await self._get_client()

            response = await client.post(
                "/v1/apps/import",
                json={
                    "name": workflow.name,
                    "description": workflow.description,
                    "mode": "workflow",
                    "graph": workflow.graph,
                    "environment_variables": workflow.environment_variables,
                }
            )
            response.raise_for_status()

            data = response.json()
            app_id = data.get("id", data.get("app_id"))

            logger.info(f"Imported workflow '{workflow.name}' to Dify as {app_id}")
            return app_id

        except Exception as e:
            logger.error(f"Failed to import workflow to Dify: {e}")
            return None

    async def sync_workflow_from_dify(self, app_id: str) -> Optional[DifyWorkflow]:
        """Synchronize a workflow from Dify to SOC Copilot.

        Args:
            app_id: Dify application ID to sync

        Returns:
            Synced workflow or None if failed
        """
        return await self.get_workflow(app_id)


# Global client instance
_dify_client: Optional[DifyClient] = None


def get_dify_client() -> DifyClient:
    """Get or create global Dify client instance."""
    global _dify_client
    if _dify_client is None:
        _dify_client = DifyClient()
    return _dify_client


async def close_dify_client():
    """Close the global Dify client."""
    global _dify_client
    if _dify_client:
        await _dify_client.close()
        _dify_client = None
# Trigger reload
# Trigger
