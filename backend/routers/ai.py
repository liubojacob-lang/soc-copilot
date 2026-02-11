"""
AI Service Router - API endpoints for SOC Copilot AI features
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from services.ai_service_enhanced import (
    get_enhanced_ai_service,
    AIAnalysisResult,
    NaturalLanguageQueryResult,
    PlaybookRecommendation,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai", "copilot"])


# Request/Response Models
class AlertAnalysisRequest(BaseModel):
    """Request for alert analysis."""

    alert_id: Optional[str] = None
    title: str
    description: str
    severity: str = "medium"
    source: str = "unknown"
    alert_type: str = "security"
    metadata: dict = Field(default_factory=dict)
    use_rag: bool = True


class AlertAnalysisResponse(BaseModel):
    """Response for alert analysis."""

    alert_id: Optional[str]
    analysis: AIAnalysisResult
    processed_at: str


class NaturalLanguageQueryRequest(BaseModel):
    """Request for natural language query."""

    query: str = Field(..., description="Natural language query")
    conversation_id: Optional[str] = None


class NaturalLanguageQueryResponse(BaseModel):
    """Response for natural language query."""

    query: str
    intent: str
    parameters: dict
    filter_criteria: dict
    response: str
    processed_at: str


class PlaybookRecommendationRequest(BaseModel):
    """Request for playbook recommendations."""

    alert_id: Optional[str] = None
    title: str
    description: str
    severity: str
    alert_type: str


class PlaybookRecommendationResponse(BaseModel):
    """Response for playbook recommendations."""

    alert_id: Optional[str]
    recommendations: List[PlaybookRecommendation]
    generated_at: str


class ChatMessage(BaseModel):
    """Chat message."""

    role: str = Field(..., regex="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Request for chat."""

    message: str
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response for chat."""

    message: str
    response: str
    conversation_id: Optional[str] = None


class ReportGenerationRequest(BaseModel):
    """Request for report generation."""

    alert_id: str
    investigation_data: dict


@router.post("/analyze-alert", response_model=AlertAnalysisResponse)
async def analyze_alert(
    request: AlertAnalysisRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Analyze a security alert using AI.

    Provides:
    - Alert summary
    - Root cause analysis
    - Recommendations
    - Confidence score
    """
    try:
        ai_service = get_enhanced_ai_service()

        alert_data = {
            "title": request.title,
            "description": request.description,
            "severity": request.severity,
            "source": request.source,
            "alert_type": request.alert_type,
            "metadata": request.metadata,
        }

        analysis = await ai_service.analyze_alert_with_rag(
            alert_data=alert_data, use_rag=request.use_rag
        )

        from datetime import datetime

        return AlertAnalysisResponse(
            alert_id=request.alert_id,
            analysis=analysis,
            processed_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error analyzing alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze alert: {str(e)}",
        )


@router.post("/query", response_model=NaturalLanguageQueryResponse)
async def natural_language_query(
    request: NaturalLanguageQueryRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Process natural language query.

    Examples:
    - "Show me high severity alerts from yesterday"
    - "What's the status of playbook run XYZ?"
    - "Analyze IP 192.168.1.100"
    """
    try:
        ai_service = get_enhanced_ai_service()

        user_context = {
            "username": current_user.username,
            "role": current_user.role.value,
            "user_id": str(current_user.id),
        }

        result = await ai_service.natural_language_query(
            query=request.query, user_context=user_context
        )

        from datetime import datetime

        return NaturalLanguageQueryResponse(
            query=request.query,
            intent=result.intent,
            parameters=result.parameters,
            filter_criteria=result.filter_criteria,
            response=result.response,
            processed_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}",
        )


@router.post("/recommend-playbooks", response_model=PlaybookRecommendationResponse)
async def recommend_playbooks(
    request: PlaybookRecommendationRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Recommend playbooks based on alert characteristics.
    """
    try:
        ai_service = get_enhanced_ai_service()

        # Get available playbooks from database
        from repositories.playbook_definition_repository import (
            PlaybookDefinitionRepository,
        )

        defn_repo = PlaybookDefinitionRepository(db)

        # Get active playbooks
        definitions, _ = await defn_repo.list_definitions(is_active=True, page_size=100)

        available_playbooks = [
            {
                "id": str(d.id),
                "name": d.name,
                "description": d.description or "",
                "version": d.version,
                "status": d.status,
            }
            for d in definitions
        ]

        alert_data = {
            "title": request.title,
            "description": request.description,
            "severity": request.severity,
            "alert_type": request.alert_type,
        }

        recommendations = await ai_service.recommend_playbooks(
            alert_data=alert_data, available_playbooks=available_playbooks
        )

        from datetime import datetime

        return PlaybookRecommendationResponse(
            alert_id=request.alert_id,
            recommendations=recommendations,
            generated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error recommending playbooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recommend playbooks: {str(e)}",
        )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Chat with SOC Copilot AI assistant.
    """
    try:
        ai_service = get_enhanced_ai_service()

        # Convert ChatMessage to dict format
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Get response (streaming simulation)
        response_chunks = []
        async for chunk in ai_service.chat_stream(
            message=request.message, conversation_history=history
        ):
            response_chunks.append(chunk)

        full_response = "".join(response_chunks)

        return ChatResponse(
            message=request.message,
            response=full_response,
            conversation_id=request.conversation_history[0].content
            if request.conversation_history
            else None,
        )

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}",
        )


@router.post("/generate-report")
async def generate_report(
    request: ReportGenerationRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Generate investigation report using AI.
    """
    try:
        ai_service = get_enhanced_ai_service()

        report = await ai_service.generate_investigation_report(
            alert_id=request.alert_id, investigation_data=request.investigation_data
        )

        return {
            "alert_id": request.alert_id,
            "report": report,
            "format": "markdown",
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/status")
async def get_ai_status(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get AI service status.
    """
    try:
        ai_service = get_enhanced_ai_service()

        return {
            "status": "available" if ai_service._initialized else "unavailable",
            "provider": ai_service.provider if ai_service._initialized else None,
            "version": "2.0",
            "features": [
                "alert_analysis",
                "natural_language_query",
                "playbook_recommendation",
                "chat",
                "report_generation",
            ],
        }

    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        return {"status": "error", "error": str(e)}
