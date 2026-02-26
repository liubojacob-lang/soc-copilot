"""Unit tests for AI Task Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.ai_task_service import AITaskQueueService, get_ai_task_service
from models.ai_task import AITaskModel, AITaskStatus, AITaskType


@pytest.fixture
def mock_session_factory():
    """Create mock session factory."""
    session = AsyncMock()
    session_factory = MagicMock(return_value=session)
    
    # Setup context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    
    return session_factory, session


@pytest.fixture
def ai_task_service(mock_session_factory):
    """Create AI task service instance."""
    session_factory, _ = mock_session_factory
    return AITaskQueueService(session_factory)


class TestAITaskQueueService:
    """Tests for AITaskQueueService."""

    @pytest.mark.asyncio
    async def test_submit_task(self, ai_task_service, mock_session_factory):
        """Test submitting a new AI task."""
        _, session = mock_session_factory
        
        task_id = await ai_task_service.submit_task(
            task_type=AITaskType.ALERT_ANALYSIS,
            prompt="Analyze this alert",
            user_id="user-123",
            timeout_seconds=300,
        )
        
        # Verify task ID is returned
        assert task_id is not None
        assert len(task_id) == 36  # UUID format
        
        # Verify session.add was called
        assert session.add.called
        
        # Verify commit was called
        assert session.commit.called

    @pytest.mark.asyncio
    async def test_get_task_status(self, ai_task_service, mock_session_factory):
        """Test getting task status."""
        _, session = mock_session_factory
        
        # Mock task in database
        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.COMPLETED.value,
            prompt="Test prompt",
            result={"analysis": "test result"},
            created_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)
        
        status = await ai_task_service.get_task_status("test-task-id")
        
        assert status is not None
        assert status["id"] == "test-task-id"
        assert status["status"] == AITaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, ai_task_service, mock_session_factory):
        """Test getting status for non-existent task."""
        _, session = mock_session_factory
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        status = await ai_task_service.get_task_status("non-existent-id")
        
        assert status is None

    @pytest.mark.asyncio
    async def test_get_task_result_completed(self, ai_task_service, mock_session_factory):
        """Test getting result for completed task."""
        _, session = mock_session_factory
        
        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.COMPLETED.value,
            prompt="Test prompt",
            result={"analysis": "test result"},
            created_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)
        
        result = await ai_task_service.get_task_result("test-task-id")
        
        assert result is not None
        assert result["analysis"] == "test result"

    @pytest.mark.asyncio
    async def test_get_task_result_not_completed(self, ai_task_service, mock_session_factory):
        """Test getting result for non-completed task."""
        _, session = mock_session_factory
        
        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.PROCESSING.value,
            prompt="Test prompt",
            created_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)
        
        result = await ai_task_service.get_task_result("test-task-id")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_task_pending(self, ai_task_service, mock_session_factory):
        """Test cancelling a pending task."""
        _, session = mock_session_factory
        
        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.PENDING.value,
            prompt="Test prompt",
            created_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)
        
        success = await ai_task_service.cancel_task("test-task-id")
        
        assert success is True
        assert session.commit.called

    @pytest.mark.asyncio
    async def test_cancel_task_completed(self, ai_task_service, mock_session_factory):
        """Test cancelling a completed task (should fail)."""
        _, session = mock_session_factory
        
        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.COMPLETED.value,
            prompt="Test prompt",
            created_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)
        
        success = await ai_task_service.cancel_task("test-task-id")
        
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, ai_task_service, mock_session_factory):
        """Test cancelling a non-existent task."""
        _, session = mock_session_factory
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        success = await ai_task_service.cancel_task("non-existent-id")
        
        assert success is False


class TestAITaskModel:
    """Tests for AITaskModel."""

    def test_to_dict(self):
        """Test converting task to dictionary."""
        task = AITaskModel(
            id="test-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.COMPLETED.value,
            prompt="Test prompt",
            result={"key": "value"},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["id"] == "test-id"
        assert task_dict["task_type"] == AITaskType.ALERT_ANALYSIS.value
        assert task_dict["status"] == AITaskStatus.COMPLETED.value
        assert task_dict["result"] == {"key": "value"}

    def test_is_terminal(self):
        """Test checking if task is in terminal state."""
        # Non-terminal states
        task = AITaskModel(status=AITaskStatus.PENDING.value)
        assert task.is_terminal is False
        
        task = AITaskModel(status=AITaskStatus.PROCESSING.value)
        assert task.is_terminal is False
        
        # Terminal states
        task = AITaskModel(status=AITaskStatus.COMPLETED.value)
        assert task.is_terminal is True
        
        task = AITaskModel(status=AITaskStatus.FAILED.value)
        assert task.is_terminal is True
        
        task = AITaskModel(status=AITaskStatus.TIMEOUT.value)
        assert task.is_terminal is True

    def test_elapsed_seconds(self):
        """Test calculating elapsed seconds."""
        task = AITaskModel(
            status=AITaskStatus.PROCESSING.value,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        # Mock current time
        with patch('models.ai_task.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
            mock_datetime.timezone = timezone
            
            elapsed = task.elapsed_seconds
            assert elapsed == 300.0  # 5 minutes

    def test_is_timeout(self):
        """Test checking if task has timed out."""
        # Not timed out
        task = AITaskModel(
            status=AITaskStatus.PROCESSING.value,
            started_at=datetime.now(timezone.utc),
            timeout_seconds=300,
        )
        assert task.is_timeout is False
        
        # Timed out
        task = AITaskModel(
            status=AITaskStatus.PROCESSING.value,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            timeout_seconds=300,
        )
        
        with patch('models.ai_task.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
            mock_datetime.timezone = timezone
            
            assert task.is_timeout is True


class TestAITaskStatus:
    """Tests for AITaskStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert AITaskStatus.PENDING.value == "pending"
        assert AITaskStatus.PROCESSING.value == "processing"
        assert AITaskStatus.COMPLETED.value == "completed"
        assert AITaskStatus.FAILED.value == "failed"
        assert AITaskStatus.TIMEOUT.value == "timeout"


class TestAITaskType:
    """Tests for AITaskType enum."""

    def test_type_values(self):
        """Test type enum values."""
        assert AITaskType.ALERT_ANALYSIS.value == "alert_analysis"
        assert AITaskType.TIMELINE_ANALYSIS.value == "timeline_analysis"
        assert AITaskType.REPORT_GENERATION.value == "report_generation"
        assert AITaskType.CHAT_COMPLETION.value == "chat_completion"
        assert AITaskType.IOC_ANALYSIS.value == "ioc_analysis"
