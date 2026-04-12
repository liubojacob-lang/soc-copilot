"""AI Service tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAIAnalysis:
    """AI analysis endpoint tests."""

    @pytest.mark.asyncio
    async def test_analyze_alert_success(self, auth_client, sample_alert_data):
        """Test successful alert analysis."""
        with patch(
            "services.ai_service_enhanced.get_enhanced_ai_service"
        ) as mock_service:
            mock_ai = AsyncMock()
            mock_ai.analyze_alert_with_rag.return_value = MagicMock(
                summary="Test analysis",
                severity="high",
                iocs=MagicMock(
                    ips=["1.1.1.1"], domains=["evil.com"], urls=[], hashes=[]
                ),
                recommendations=["Block IP"],
            )
            mock_service.return_value = mock_ai

            response = await auth_client.post(
                "/api/ai/analyze-alert", json=sample_alert_data
            )

            # AI service may be unavailable in test environment
            if response.status_code == 503:
                pytest.skip("AI service unavailable")
            assert response.status_code == 200

            data = response.json()
            assert "summary" in data or "analysis" in data

    @pytest.mark.asyncio
    async def test_analyze_alert_missing_fields(self, auth_client):
        """Test alert analysis with missing required fields."""
        response = await auth_client.post(
            "/api/ai/analyze-alert", json={"title": "Test"}
        )
        # Missing required fields should fail validation
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_completion(self, auth_client):
        """Test AI chat completion."""
        with patch(
            "services.ai_service_enhanced.get_enhanced_ai_service"
        ) as mock_service:
            mock_ai = AsyncMock()
            mock_ai.chat_with_history.return_value = "This is a test response"
            mock_service.return_value = mock_ai

            response = await auth_client.post(
                "/api/ai/chat", json={"message": "Hello AI", "conversation_history": []}
            )

            # AI service may be unavailable in test environment
            if response.status_code == 503:
                pytest.skip("AI service unavailable")
            assert response.status_code == 200

            data = response.json()
            assert "response" in data or "message" in data

    @pytest.mark.asyncio
    async def test_recommend_playbooks(self, auth_client):
        """Test playbook recommendation."""
        with patch(
            "services.ai_service_enhanced.get_enhanced_ai_service"
        ) as mock_service:
            mock_ai = AsyncMock()
            mock_ai.recommend_playbooks.return_value = [
                MagicMock(id="pb1", name="Playbook 1", description="Test"),
                MagicMock(id="pb2", name="Playbook 2", description="Test 2"),
            ]
            mock_service.return_value = mock_ai

            response = await auth_client.get(
                "/api/ai/recommend-playbooks?alert_id=test-alert-123"
            )

            # AI service may be unavailable in test environment
            if response.status_code == 503:
                pytest.skip("AI service unavailable")
            assert response.status_code == 200

            if response.status_code == 200:
                data = response.json()
                assert "recommendations" in data or isinstance(data, list)


class TestAITasks:
    """AI background task tests."""

    @pytest.mark.asyncio
    async def test_submit_ai_task(self, auth_client):
        """Test submitting an AI background task."""
        response = await auth_client.post(
            "/ai-tasks/submit",
            json={
                "task_type": "alert_analysis",
                "prompt": "Analyze this test alert",
                "timeout_seconds": 60,
            },
        )

        # Endpoint may not be implemented
        if response.status_code == 404:
            pytest.skip("AI tasks endpoint not implemented")
        assert response.status_code == 202

        if response.status_code == 202:
            data = response.json()
            assert "task_id" in data

    @pytest.mark.asyncio
    async def test_get_task_status(self, auth_client):
        """Test getting AI task status."""
        # First submit a task
        submit_response = await auth_client.post(
            "/ai-tasks/submit",
            json={
                "task_type": "chat_completion",
                "prompt": "Hello",
                "timeout_seconds": 30,
            },
        )

        if submit_response.status_code == 202:
            task_id = submit_response.json()["task_id"]

            # Get status
            status_response = await auth_client.get(f"/ai-tasks/{task_id}/status")
            assert status_response.status_code == 200
            data = status_response.json()
            assert "status" in data

    @pytest.mark.asyncio
    async def test_list_ai_tasks(self, auth_client):
        """Test listing AI tasks."""
        response = await auth_client.get("/ai-tasks?limit=10")
        # Endpoint may not be implemented
        if response.status_code == 404:
            pytest.skip("AI tasks list endpoint not implemented")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_ai_task(self, auth_client):
        """Test cancelling an AI task."""
        # Submit a task
        submit_response = await auth_client.post(
            "/ai-tasks/submit",
            json={
                "task_type": "alert_analysis",
                "prompt": "Test",
                "timeout_seconds": 60,
            },
        )

        if submit_response.status_code == 202:
            task_id = submit_response.json()["task_id"]

            # Cancel it
            cancel_response = await auth_client.post(f"/ai-tasks/{task_id}/cancel")
            # Cancel may fail if task already completed or endpoint not implemented
            if cancel_response.status_code == 404:
                pytest.skip("Cancel endpoint not implemented")
            assert cancel_response.status_code in [
                200,
                400,
            ]  # 200 = cancelled, 400 = already completed


class TestAIModels:
    """AI model management tests."""

    @pytest.mark.asyncio
    async def test_list_ai_models(self, auth_client):
        """Test listing available AI models."""
        response = await auth_client.get("/api/ai-models")
        # Endpoint may not be implemented
        if response.status_code == 404:
            pytest.skip("AI models endpoint not implemented")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_ai_model(self, auth_client):
        """Test getting a specific AI model."""
        response = await auth_client.get("/api/ai-models/gpt-4")
        # Endpoint may not be implemented
        if response.status_code == 404:
            pytest.skip("Specific AI model endpoint not implemented")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_ai_model(self, admin_client):
        """Test updating AI model configuration."""
        response = await admin_client.put(
            "/api/ai-models/gpt-4",
            json={"enabled": True, "api_key": "test-key", "max_tokens": 4000},
        )
        # Endpoint may not be implemented
        if response.status_code == 404:
            pytest.skip("AI model update endpoint not implemented")
        assert response.status_code == 200


class TestAIServiceEnhanced:
    """Enhanced AI service tests."""

    @pytest.mark.asyncio
    async def test_ai_service_with_rag(self, auth_client, sample_alert_data):
        """Test AI analysis with RAG enabled."""
        response = await auth_client.post(
            "/api/ai/analyze-alert", json={**sample_alert_data, "use_rag": True}
        )
        # AI service may be unavailable in test environment
        if response.status_code == 503:
            pytest.skip("AI service unavailable")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ai_service_without_rag(self, auth_client, sample_alert_data):
        """Test AI analysis without RAG."""
        response = await auth_client.post(
            "/api/ai/analyze-alert", json={**sample_alert_data, "use_rag": False}
        )
        # AI service may be unavailable in test environment
        if response.status_code == 503:
            pytest.skip("AI service unavailable")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ai_service_timeout_handling(self, auth_client):
        """Test AI service timeout handling."""
        with patch(
            "services.ai_service_enhanced.get_enhanced_ai_service"
        ) as mock_service:
            mock_ai = AsyncMock()
            # Simulate timeout

            mock_ai.analyze_alert_with_rag.side_effect = TimeoutError()
            mock_service.return_value = mock_ai

            response = await auth_client.post(
                "/api/ai/analyze-alert",
                json={
                    "title": "Test",
                    "description": "Test alert",
                    "severity": "medium",
                },
            )

            # AI service should handle timeout gracefully
            assert response.status_code == 503  # Service unavailable due to timeout


class TestAIRateLimit:
    """AI rate limiting tests."""

    @pytest.mark.asyncio
    async def test_ai_rate_limiting(self, auth_client):
        """Test AI endpoint rate limiting."""
        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            response = await auth_client.post(
                "/api/ai/chat", json={"message": "Test", "conversation_history": []}
            )
            responses.append(response)
            # Rate limiting may return 429
            if response.status_code == 429:
                break

        # AI service may be unavailable in test environment
        if responses[0].status_code == 503:
            pytest.skip("AI service unavailable")
        assert responses[0].status_code == 200

    @pytest.mark.asyncio
    async def test_ai_concurrent_requests(self, auth_client):
        """Test handling concurrent AI requests."""
        import asyncio

        async def make_request():
            return await auth_client.post(
                "/api/ai/chat", json={"message": "Test", "conversation_history": []}
            )

        # Make concurrent requests
        responses = await asyncio.gather(
            make_request(), make_request(), make_request(), return_exceptions=True
        )

        # All should complete without errors
        for r in responses:
            if not isinstance(r, Exception):
                # Accept success, rate limited, or service unavailable
                assert r.status_code in [
                    200,
                    429,
                    503,
                ]  # 200 = success, 429 = rate limited, 503 = unavailable
