"""Tests for DeepSeek client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gemini_chat_backend.core.deepseek import DeepSeekClient, DeepSeekError


class TestDeepSeekClient:
    """Test suite for DeepSeekClient."""

    @pytest.fixture
    def client(self) -> DeepSeekClient:
        """Create a DeepSeekClient instance."""
        return DeepSeekClient(
            api_key="test_key",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model",
        )

    def test_init(self, client: DeepSeekClient) -> None:
        """Test client initialization."""
        assert client.api_key == "test_key"
        assert client.api_url == "https://api.test.com/v1/chat/completions"
        assert client.model == "test-model"
        assert client.headers["Authorization"] == "Bearer test_key"
        assert client.headers["Content-Type"] == "application/json"

    def test_prepare_messages_with_system_prompt(self, client: DeepSeekClient) -> None:
        """Test message preparation with system prompt."""
        messages = [{"role": "user", "content": "Hello"}]

        result = client._prepare_messages(messages, system_prompt="You are helpful")

        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful"
        assert result[1]["role"] == "user"

    def test_prepare_messages_sanitizes_reasoning_content(self, client: DeepSeekClient) -> None:
        """Test that reasoning_content is sanitized correctly."""
        messages = [
            {
                "role": "assistant",
                "content": "Test",
                "tool_calls": [{"id": "1"}],
                "reasoning_content": "",
            },
            {
                "role": "assistant",
                "content": "Test 2",
                "reasoning_content": "Should be removed",
            },
        ]

        result = client._prepare_messages(messages)

        # First message should have reasoning_content
        assert "reasoning_content" in result[0]
        # Second message should have reasoning_content removed
        assert "reasoning_content" not in result[1]

    @pytest.mark.asyncio
    async def test_chat_streaming_success(self, client: DeepSeekClient) -> None:
        """Test successful streaming chat."""
        mock_response = MagicMock()
        mock_response.aiter_lines = AsyncMock(return_value=[
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            b'data: [DONE]',
        ])
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient.stream", return_value=mock_client):
            chunks = []
            async for chunk in client.chat([{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)

            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_http_error(self, client: DeepSeekClient) -> None:
        """Test that HTTP errors are raised as DeepSeekError."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error",
            request=MagicMock(),
            response=MagicMock(status_code=500, text="Server Error"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient.stream", return_value=mock_client):
            with pytest.raises(DeepSeekError) as exc_info:
                async for _ in client.chat([{"role": "user", "content": "Hi"}]):
                    pass

            assert "DeepSeek API error" in str(exc_info.value)
