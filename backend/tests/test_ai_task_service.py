"""Unit tests for AI Task Service."""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ai_task import AITaskModel, AITaskStatus, AITaskType
from services.ai_task_service import AITaskQueueService


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
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)

        status = await ai_task_service.get_task_status("test-task-id")

        assert status is not None
        assert status["id"] == "test-task-id"
        assert status["status"] == AITaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(
        self, ai_task_service, mock_session_factory
    ):
        """Test getting status for non-existent task."""
        _, session = mock_session_factory

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        status = await ai_task_service.get_task_status("non-existent-id")

        assert status is None

    @pytest.mark.asyncio
    async def test_get_task_result_completed(
        self, ai_task_service, mock_session_factory
    ):
        """Test getting result for completed task."""
        _, session = mock_session_factory

        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.COMPLETED.value,
            prompt="Test prompt",
            result={"analysis": "test result"},
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        session.execute = AsyncMock(return_value=mock_result)

        result = await ai_task_service.get_task_result("test-task-id")

        assert result is not None
        assert result["analysis"] == "test result"

    @pytest.mark.asyncio
    async def test_get_task_result_not_completed(
        self, ai_task_service, mock_session_factory
    ):
        """Test getting result for non-completed task."""
        _, session = mock_session_factory

        mock_task = AITaskModel(
            id="test-task-id",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.PROCESSING.value,
            prompt="Test prompt",
            created_at=datetime.now(UTC),
            timeout_seconds=300,
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
            created_at=datetime.now(UTC),
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
            created_at=datetime.now(UTC),
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

    @pytest.mark.asyncio
    async def test_process_task_persists_tuple_result_correctly(
        self, ai_task_service, mock_session_factory
    ):
        """P0-1 regression: _process_task must unpack the (result, model, degraded) tuple.

        Previously it assigned the whole tuple to `result` and stored it as
        {"content": <tuple>}. Now it unpacks and stores structured metadata.
        """
        _, session = mock_session_factory

        # First query: return a PENDING task to process
        task = AITaskModel(
            id="proc-1",
            task_type=AITaskType.CHAT_COMPLETION.value,
            status=AITaskStatus.PENDING.value,
            prompt="summarize this",
            created_at=datetime.now(UTC),
            timeout_seconds=300,
        )
        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = task
        # Second query (result refresh) returns the same task object
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = task

        session.execute = AsyncMock(side_effect=[first_result, second_result])

        # Mock the LLM service to return a properly-shaped tuple
        with patch("services.ai_task_service.get_llm_retry_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.generate_structured = AsyncMock(
                return_value=("summary text", "glm-4-test", False)
            )
            mock_get_llm.return_value = mock_llm

            await ai_task_service._process_task("proc-1")

        # The task result must be a dict with content/model_used/degraded —
        # NOT a bare tuple and NOT {"content": <tuple>}.
        assert task.status == AITaskStatus.COMPLETED.value
        assert isinstance(task.result, dict)
        assert task.result["content"] == "summary text"
        assert task.result["model_used"] == "glm-4-test"
        assert task.result["degraded"] is False
        # generate_structured must be called with response_class=None
        call_kwargs = mock_llm.generate_structured.call_args.kwargs
        assert call_kwargs["response_class"] is None

    @pytest.mark.asyncio
    async def test_process_task_degraded_result_still_persisted(
        self, ai_task_service, mock_session_factory
    ):
        """When LLM degrades (empty content), the task still reaches COMPLETED."""
        _, session = mock_session_factory

        task = AITaskModel(
            id="proc-2",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.PENDING.value,
            prompt="analyze",
            created_at=datetime.now(UTC),
            timeout_seconds=300,
        )
        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = task
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = task
        session.execute = AsyncMock(side_effect=[first_result, second_result])

        with patch("services.ai_task_service.get_llm_retry_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.generate_structured = AsyncMock(
                return_value=("", "glm-4-test", True)  # degraded
            )
            mock_get_llm.return_value = mock_llm

            await ai_task_service._process_task("proc-2")

        assert task.status == AITaskStatus.COMPLETED.value
        assert task.result["degraded"] is True
        assert task.result["content"] == ""

    @pytest.mark.asyncio
    async def test_process_task_backfills_alert_triage(
        self, ai_task_service, mock_session_factory
    ):
        """T2.5: Verify alert.raw_data is backfilled when alert analysis task finishes."""
        from models.security_alert import SecurityAlert

        _, session = mock_session_factory

        task = AITaskModel(
            id="task-alert-1",
            task_type=AITaskType.ALERT_ANALYSIS.value,
            status=AITaskStatus.PENDING.value,
            prompt="analyze alert",
            input_data={"alert_id": "42"},
            created_at=datetime.now(UTC),
            timeout_seconds=300,
        )
        fake_alert = SecurityAlert(
            id=42,
            title="Suspicious SSH Login",
            severity="high",
            source="wazuh",
            external_event_id="ext-1",
            event_type="brute_force",
            raw_data={"pipeline": {"ai_task_id": "task-alert-1"}},
        )

        res_task1 = MagicMock()
        res_task1.scalar_one_or_none.return_value = task
        res_task2 = MagicMock()
        res_task2.scalar_one_or_none.return_value = task
        res_alert = MagicMock()
        res_alert.scalar_one_or_none.return_value = fake_alert

        session.execute = AsyncMock(side_effect=[res_task1, res_task2, res_alert])

        with patch("services.ai_task_service.get_llm_retry_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.generate_structured = AsyncMock(
                return_value=(
                    "分析结论：存在密码爆破攻击，建议严重度: critical",
                    "glm-4-flash",
                    False,
                )
            )
            mock_get_llm.return_value = mock_llm

            await ai_task_service._process_task("task-alert-1")

        assert task.status == AITaskStatus.COMPLETED.value
        # Verify alert raw_data was updated with triage information
        assert "pipeline" in fake_alert.raw_data
        triage = fake_alert.raw_data["pipeline"].get("ai_triage")
        assert triage is not None
        assert "密码爆破攻击" in triage["summary"]
        assert triage["task_id"] == "task-alert-1"
        assert triage["model_used"] == "glm-4-flash"
        assert triage["degraded"] is False
        assert fake_alert.raw_data["pipeline"].get("ai_suggested_severity") == "critical"



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
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
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
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Mock current time
        with patch("models.ai_task.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC)
            mock_datetime.timezone = timezone

            elapsed = task.elapsed_seconds
            assert elapsed == 300.0  # 5 minutes

    def test_is_timeout(self):
        """Test checking if task has timed out."""
        # Not timed out
        task = AITaskModel(
            status=AITaskStatus.PROCESSING.value,
            started_at=datetime.now(UTC),
            timeout_seconds=300,
        )
        assert task.is_timeout is False

        # Timed out
        task = AITaskModel(
            status=AITaskStatus.PROCESSING.value,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            timeout_seconds=300,
        )

        with patch("models.ai_task.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC)
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
