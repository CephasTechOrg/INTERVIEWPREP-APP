"""
Tests for LLM client (DeepSeek API integration).

Tests cover:
- Successful API calls
- Error handling and retries
- Fallback behavior
- Health status tracking
- JSON parsing with fallbacks
"""

import contextlib
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from app.core.config import settings
from app.services.llm_client import DeepSeekClient, LLMClientError


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
        """Test client initializes in fallback mode without API key."""
        with patch.object(settings, "DEEPSEEK_API_KEY", None):
            client = DeepSeekClient()
            assert client.api_key is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_chat_completion(self):
        """Test successful chat completion request."""
        mock_response = {
            "choices": [{"message": {"content": '{"response": "Test response", "reasoning": "Test reasoning"}'}}]
        }

        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=Response(200, json=mock_response)
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Test"}], response_format={"type": "json_object"}
            )

            assert result is not None
            assert "response" in result
            assert result["response"] == "Test response"

    @respx.mock
    @pytest.mark.asyncio
    async def test_network_error_with_retry(self):
        """Test retry logic on network errors."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            side_effect=[
                Response(500, json={"error": "Internal server error"}),
                Response(500, json={"error": "Internal server error"}),
                Response(200, json={"choices": [{"message": {"content": '{"response": "Success after retry"}'}}]}),
            ]
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            with patch.object(settings, "DEEPSEEK_MAX_RETRIES", 3):
                client = DeepSeekClient()
                result = await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

                assert result is not None
                assert "response" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that LLMClientError is raised after max retries."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=Response(500, json={"error": "Internal server error"})
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            with patch.object(settings, "DEEPSEEK_MAX_RETRIES", 2):
                client = DeepSeekClient()

                with pytest.raises(LLMClientError):
                    await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

    @respx.mock
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON in response."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": "Not valid JSON"}}]})
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            result = await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

            # Should return raw content when JSON parsing fails
            assert result is not None
            assert isinstance(result, dict)

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        import httpx

        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            with patch.object(settings, "DEEPSEEK_MAX_RETRIES", 1):
                client = DeepSeekClient()

                with pytest.raises(LLMClientError) as exc_info:
                    await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

                assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fallback_when_no_api_key(self):
        """Test fallback behavior when API key is not configured."""
        with patch.object(settings, "DEEPSEEK_API_KEY", None):
            client = DeepSeekClient()

            # Should return None or fallback response
            result = await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

            assert result is None or isinstance(result, dict)

    def test_get_llm_status_configured(self):
        """Test LLM status when API key is configured."""
        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()
            status = client.get_llm_status()

            assert status["configured"] is True
            assert "status" in status
            assert "fallback_mode" in status

    def test_get_llm_status_not_configured(self):
        """Test LLM status when API key is not configured."""
        with patch.object(settings, "DEEPSEEK_API_KEY", None):
            client = DeepSeekClient()
            status = client.get_llm_status()

            assert status["configured"] is False
            assert status["fallback_mode"] is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_health_tracking_on_success(self):
        """Test that health status is updated on successful request."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": '{"response": "Success"}'}}]})
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            client = DeepSeekClient()

            await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

            status = client.get_llm_status()
            assert status["last_ok_at"] is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_health_tracking_on_error(self):
        """Test that health status is updated on error."""
        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=Response(500, json={"error": "Server error"})
        )

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            with patch.object(settings, "DEEPSEEK_MAX_RETRIES", 1):
                client = DeepSeekClient()

                with contextlib.suppress(LLMClientError):
                    await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

                status = client.get_llm_status()
                assert status["last_error_at"] is not None
                assert status["last_error"] is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff between retries."""
        call_times = []

        def track_call(*args, **kwargs):
            import time

            call_times.append(time.time())
            return Response(500, json={"error": "Server error"})

        respx.post(f"{settings.DEEPSEEK_BASE_URL}/chat/completions").mock(side_effect=track_call)

        with patch.object(settings, "DEEPSEEK_API_KEY", "test-key"):
            with patch.object(settings, "DEEPSEEK_MAX_RETRIES", 3):
                with patch.object(settings, "DEEPSEEK_RETRY_BACKOFF_SECONDS", 0.1):
                    client = DeepSeekClient()

                    with contextlib.suppress(LLMClientError):
                        await client.chat_completion(messages=[{"role": "user", "content": "Test"}])

                    # Verify backoff increased between retries
                    if len(call_times) >= 2:
                        time_diff = call_times[1] - call_times[0]
                        assert time_diff >= 0.1  # At least the backoff time
