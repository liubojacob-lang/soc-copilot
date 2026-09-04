"""AI Task API endpoints.

Provides endpoints for:
- Submitting AI tasks for background processing
- Polling task status
- Retrieving task results
- Cancelling tasks
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from dependencies.auth import get_current_user
from models.ai_task import AITaskStatus, AITaskType
from services.ai_task_service import get_ai_task_service

router = APIRouter(prefix="/api/v1/ai-tasks", tags=["AI Tasks"])


class SubmitAITaskRequest(BaseModel):
    """Request model for submitting an AI task."""

    model_config = {"protected_namespaces": ()}

    task_type: str = Field(..., description="Type of AI task")
    prompt: str = Field(..., description="Prompt for the AI")
    input_data: dict[str, Any] | None = Field(
        default=None, description="Additional input data"
    )
    model_id: str | None = Field(default=None, description="Specific model to use")
    provider: str | None = Field(default=None, description="AI provider")
    timeout_seconds: int = Field(
        default=300, ge=30, le=1800, description="Task timeout in seconds"
    )
    priority: int = Field(default=0, ge=0, le=10, description="Task priority")


class SubmitAITaskResponse(BaseModel):
    """Response model for task submission."""

    task_id: str
    message: str = "Task submitted successfully"


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    id: str
    task_type: str
    status: str
    input_data: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    user_id: str | None = None
    retry_count: int = 0
    elapsed_seconds: float | None = None
    progress_percent: int | None = None


class TaskListResponse(BaseModel):
    """Response model for task list."""

    tasks: list[TaskStatusResponse]
    total: int


class CancelTaskResponse(BaseModel):
    """Response model for task cancellation."""

    success: bool
    message: str


@router.post(
    "/submit",
    response_model=SubmitAITaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit AI task for background processing",
    description="Submit an AI task to be processed in the background. Returns a task ID for status polling.",
)
async def submit_ai_task(
    request: SubmitAITaskRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit an AI task for background processing.

    This endpoint accepts AI tasks and queues them for background processing.
    Use the returned task_id to poll for status and results.

    - **task_type**: Type of AI task (alert_analysis, timeline_analysis, report_generation, chat_completion, ioc_analysis)
    - **prompt**: The prompt to send to the AI model
    - **input_data**: Optional additional input data
    - **timeout_seconds**: Maximum time to wait for completion (30-1800 seconds)
    - **priority**: Task priority (0-10, higher = more urgent)
    """
    # Validate task type
    try:
        task_type = AITaskType(request.task_type)
    except ValueError:
        valid_types = [t.value for t in AITaskType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task_type. Must be one of: {valid_types}",
        )

    service = get_ai_task_service()
    user_id = current_user.get("id") if current_user else None

    task_id = await service.submit_task(
        task_type=task_type,
        prompt=request.prompt,
        input_data=request.input_data,
        model_id=request.model_id,
        provider=request.provider,
        user_id=user_id,
        timeout_seconds=request.timeout_seconds,
        priority=request.priority,
    )

    return SubmitAITaskResponse(
        task_id=task_id,
        message="Task submitted successfully. Poll /ai-tasks/{task_id}/status for progress.",
    )


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="Get AI task status",
    description="Get the current status of an AI task including progress and results if completed.",
)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the current status of an AI task.

    Returns the task status, progress, and results if completed.

    Status values:
    - **pending**: Task is waiting to be processed
    - **processing**: Task is currently being processed
    - **completed**: Task finished successfully, result available
    - **failed**: Task failed, check error_message
    - **timeout**: Task exceeded timeout limit
    """
    service = get_ai_task_service()
    task_status = await service.get_task_status(task_id)

    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Calculate progress
    progress_percent = None
    if task_status["status"] == AITaskStatus.COMPLETED.value:
        progress_percent = 100
    elif task_status["status"] == AITaskStatus.PROCESSING.value:
        # Estimate progress based on elapsed time
        # This is a rough estimate; actual progress depends on the task
        progress_percent = 50

    return TaskStatusResponse(
        **task_status,
        progress_percent=progress_percent,
    )


@router.get(
    "/{task_id}/result",
    summary="Get AI task result",
    description="Get the result of a completed AI task.",
)
async def get_task_result(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the result of a completed AI task.

    Only returns results for completed tasks.
    Returns 404 if task not found or not completed.
    """
    service = get_ai_task_service()
    result = await service.get_task_result(task_id)

    if result is None:
        # Check if task exists
        task_status = await service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not completed. Current status: {task_status['status']}",
        )

    return {"task_id": task_id, "result": result}


@router.post(
    "/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel AI task",
    description="Cancel a pending or processing AI task.",
)
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a pending or processing AI task.

    Only tasks in pending or processing state can be cancelled.
    Completed, failed, or timeout tasks cannot be cancelled.
    """
    service = get_ai_task_service()
    success = await service.cancel_task(task_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel task. Task may not exist or is already in terminal state.",
        )

    return CancelTaskResponse(
        success=True,
        message=f"Task {task_id} cancelled successfully",
    )


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List AI tasks",
    description="List AI tasks for the current user with optional filtering.",
)
async def list_tasks(
    status_filter: str | None = None,
    task_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """List AI tasks for the current user.

    - **status_filter**: Filter by task status (pending, processing, completed, failed, timeout)
    - **task_type**: Filter by task type
    - **limit**: Maximum number of tasks to return (default 20)
    - **offset**: Offset for pagination
    """
    from sqlalchemy import and_, func, select

    from db.session import AsyncSessionLocal
    from models.ai_task import AITaskModel

    user_id = current_user.get("id") if current_user else None

    async with AsyncSessionLocal() as session:
        # Build query
        conditions = []
        if user_id:
            conditions.append(AITaskModel.user_id == user_id)
        if status_filter:
            conditions.append(AITaskModel.status == status_filter)
        if task_type:
            conditions.append(AITaskModel.task_type == task_type)

        # Get total count
        count_stmt = select(func.count()).select_from(AITaskModel)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total_result = await session.execute(count_stmt)
        total = total_result.scalar()

        # Get tasks
        stmt = (
            select(AITaskModel)
            .order_by(AITaskModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        tasks = result.scalars().all()

        return TaskListResponse(
            tasks=[
                TaskStatusResponse(
                    **task.to_dict(),
                    progress_percent=(
                        100 if task.status == AITaskStatus.COMPLETED.value else None
                    ),
                )
                for task in tasks
            ],
            total=total,
        )


@router.get(
    "/types",
    summary="Get available task types",
    description="Get list of available AI task types.",
)
async def get_task_types():
    """Get available AI task types."""
    return {
        "task_types": [
            {"value": t.value, "description": _get_task_type_description(t)}
            for t in AITaskType
        ]
    }


def _get_task_type_description(task_type: AITaskType) -> str:
    """Get description for a task type."""
    descriptions = {
        AITaskType.ALERT_ANALYSIS: "Analyze security alerts and provide insights",
        AITaskType.TIMELINE_ANALYSIS: "Analyze event timelines for patterns",
        AITaskType.REPORT_GENERATION: "Generate security reports",
        AITaskType.CHAT_COMPLETION: "General chat completion tasks",
        AITaskType.IOC_ANALYSIS: "Analyze indicators of compromise",
    }
    return descriptions.get(task_type, "No description available")
