"""
Tests for LLM client (DeepSeek API integration).

Tests cover:
- Successful API calls
- Error handling and retries
- Health status tracking
- JSON parsing failures
"""

from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

from app.core.config import settings
from app.services.llm_client import DeepSeekClient, LLMClientError, get_llm_status


@pytest.mark.unit
@pytest.mark.llm
class TestDeepSeekClient:
    """Test suite for DeepSeek LLM client."""

    def test_client_initialization_with_api_key(self):
        """Test client initializes correctly with API key."""
        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            assert client.api_key == "test-key"
            assert client.base_url == settings.DEEPSEEK_BASE_URL
            assert client.model == settings.DEEPSEEK_MODEL

    def test_client_initialization_without_api_key(self):
        """Test client initializes without API key."""
        with patch.object(settings, "DEEPSEEK_API_KEY", None):
            client = DeepSeekClient()
            assert client.api_key is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_chat_completion(self):
        """Test successful chat request."""
        mock_response = {"choices": [{"message": {"content": '{"overall_score": 80}'}}]}
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            return_value=Response(200, json=mock_response)
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            result = await client.chat_json("system", "user")

            assert result["overall_score"] == 80

    @respx.mock
    @pytest.mark.asyncio
    async def test_network_error_with_retry(self):
        """Test retry logic on server errors."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            side_effect=[
                Response(500, json={"error": "Internal server error"}),
                Response(500, json={"error": "Internal server error"}),
                Response(200, json={"choices": [{"message": {"content": "Success after retry"}}]}),
            ]
        )

        with (
            patch.object(settings, "DEEPSEEK_API_KEY", "test-key"),
            patch.object(settings, "DEEPSEEK_MAX_RETRIES", 2),
        ):
            client = DeepSeekClient()
            result = await client.chat("system", "user")

            assert result == "Success after retry"

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that LLMClientError is raised after max retries."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            return_value=Response(500, json={"error": "Internal server error"})
        )

        with (
            patch.object(settings, "DEEPSEEK_API_KEY", "test-key"),
            patch.object(settings, "DEEPSEEK_MAX_RETRIES", 1),
        ):
            client = DeepSeekClient()

            with pytest.raises(LLMClientError):
                await client.chat("system", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON in response."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": "Not valid JSON"}}]})
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            with pytest.raises(LLMClientError):
                await client.chat_json("system", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        with (
            patch.object(settings, "DEEPSEEK_API_KEY", "test-key"),
            patch.object(settings, "DEEPSEEK_MAX_RETRIES", 1),
        ):
            client = DeepSeekClient()

            with pytest.raises(LLMClientError) as exc_info:
                await client.chat("system", "user")

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        """Test error when API key is not configured."""
        with patch.object(settings, "DEEPSEEK_API_KEY", None):
            client = DeepSeekClient()

            with pytest.raises(LLMClientError):
                await client.chat("system", "user")

    def test_get_llm_status_configured(self):
        """Test LLM status when API key is configured."""
        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            status = get_llm_status()

            assert status["configured"] is True
            assert "status" in status
            assert "fallback_mode" in status

    def test_get_llm_status_not_configured(self):
        """Test LLM status when API key is not configured."""
        with patch.object(settings, "DEEPSEEK_API_KEY", None):
            status = get_llm_status()

            assert status["configured"] is False
            assert status["fallback_mode"] is True
            assert status["status"] == "offline"

    @respx.mock
    @pytest.mark.asyncio
    async def test_health_tracking_on_success(self):
        """Test health status updated on successful request."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": "Success"}}]})
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            await client.chat("system", "user")

            status = get_llm_status()
            assert status["last_ok_at"] is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_health_tracking_on_error(self):
        """Test health status updated on error."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions").mock(
            return_value=Response(500, json={"error": "Server error"})
        )

        with (
            patch.object(settings, "DEEPSEEK_API_KEY", "test-key"),
            patch.object(settings, "DEEPSEEK_MAX_RETRIES", 0),
        ):
            client = DeepSeekClient()

            with pytest.raises(LLMClientError):
                await client.chat("system", "user")

            status = get_llm_status()
            assert status["last_error_at"] is not None
            assert status["last_error"] is not None

    def test_retry_backoff_increases(self):
        """Test retry backoff grows with attempts."""
        with patch.object(settings, "DEEPSEEK_RETRY_BACKOFF_SECONDS", 0.1):
            client = DeepSeekClient()
            with patch("random.random", return_value=0.0):
                assert client._retry_delay(0) == pytest.approx(0.1)
                assert client._retry_delay(1) == pytest.approx(0.2)
