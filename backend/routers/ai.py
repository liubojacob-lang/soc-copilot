"""
AI Service Router - API endpoints for SOC Copilot AI features
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
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

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str

    model_config = ConfigDict(protected_namespaces=())


class ChatRequest(BaseModel):
    """Request for chat."""

    message: str
    model_id: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = None

    model_config = ConfigDict(protected_namespaces=())


class ChatResponse(BaseModel):
    """Response for chat."""

    message: str
    response: str
    conversation_id: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class ReportGenerationRequest(BaseModel):
    """Request for report generation."""

    alert_id: str
    investigation_data: dict

    model_config = ConfigDict(protected_namespaces=())


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
            "role": current_user.role,
            "user_id": str(current_user.id),
        }

        result = await ai_service.natural_language_query(
            query=request.query, user_context=user_context
        )

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
    db: AsyncSession = Depends(get_session),
):
    """
    Chat with SOC Copilot AI assistant.
    """
    try:
        ai_service = get_enhanced_ai_service()

        # Get model to use
        model_id = request.model_id
        model_provider = None

        if model_id:
            # User specified a model - verify it exists and is enabled
            from repositories.ai_model_repository import AIModelRepository
            model_repo = AIModelRepository(db)
            model = await model_repo.get_by_id(model_id)
            if not model or not model.enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {model_id} not found or not enabled",
                )
            model_provider = model.provider
            logger.info(f"Using requested model: {model_id} (provider: {model_provider})")
        else:
            # Use user's default model
            from repositories.ai_model_repository import AIUserSettingRepository, AIModelRepository
            setting_repo = AIUserSettingRepository(db)
            model_repo = AIModelRepository(db)

            # Get user's preferred model
            user_settings = await setting_repo.get_by_user_id(str(current_user.id))
            user_model_id = user_settings.default_model_id if user_settings else None

            if user_model_id:
                model = await model_repo.get_by_id(user_model_id)
                if model and model.enabled:
                    model_id = user_model_id
                    model_provider = model.provider
                    logger.info(f"Using user's default model: {model_id}")

            # If no user default, fall back to service default
            if not model_id:
                model_id = None
                model_provider = None
                logger.info(f"Using service default provider: {ai_service.provider}")

        # Convert ChatMessage to dict format
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Get complete response directly
        logger.info(f"Processing chat request: {request.message[:50]}...")
        full_response = await ai_service.chat(
            message=request.message,
            conversation_history=history,
            model_id=model_id,
            model_provider=model_provider,
        )
        logger.info(f"Chat response received: {len(full_response)} chars")

        conversation_id = None
        if request.conversation_history and len(request.conversation_history) > 0:
            conversation_id = request.conversation_history[0].content

        return ChatResponse(
            message=request.message,
            response=full_response,
            conversation_id=conversation_id,
        )

    except HTTPException:
        raise
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

        # Check if AI service is properly initialized
        if not ai_service._initialized:
            logger.warning(
                f"AI service not initialized. Provider: {ai_service.provider}"
            )
            return {
                "status": "unavailable",
                "provider": ai_service.provider,
                "version": "2.0",
                "error": "AI service not initialized - please check API key configuration",
                "features": [],
            }

        # Verify LLM is available
        if not ai_service.llm:
            logger.warning(f"LLM provider is None for: {ai_service.provider}")
            return {
                "status": "unavailable",
                "provider": ai_service.provider,
                "version": "2.0",
                "error": f"No LLM instance for provider: {ai_service.provider}",
                "features": [],
            }

        return {
            "status": "available",
            "provider": ai_service.provider,
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
        import traceback

        logger.error(f"Error getting AI status: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "provider": getattr(settings, "ai_provider", "unknown"),
        }
