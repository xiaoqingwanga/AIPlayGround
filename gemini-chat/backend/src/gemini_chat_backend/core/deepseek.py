"""DeepSeek API client for Gemini Chat Backend."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from gemini_chat_backend.config import settings
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)


class DeepSeekError(Exception):
    """Raised when DeepSeek API returns an error."""

    pass


class DeepSeekClient:
    """Client for DeepSeek API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key (defaults to settings.DEEPSEEK_API_KEY)
            api_url: DeepSeek API URL (defaults to settings.DEEPSEEK_API_URL)
            model: Model to use (defaults to settings.DEEPSEEK_MODEL)
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.api_url = api_url or settings.DEEPSEEK_API_URL
        self.model = model or settings.DEEPSEEK_MODEL

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "DeepSeek client initialized",
            model=self.model,
            api_url=self.api_url,
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send chat request to DeepSeek API.

        Args:
            messages: List of chat messages
            tools: Optional list of tools for function calling
            stream: Whether to stream the response
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend

        Yields:
            Response chunks (for streaming) or complete response

        Raises:
            DeepSeekError: If API request fails
        """
        # Prepare messages with system prompt if provided
        prepared_messages = self._prepare_messages(messages, system_prompt)

        # Build request payload
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": prepared_messages,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools

        if max_tokens:
            payload["max_tokens"] = max_tokens

        logger.info(
            "Sending chat request to DeepSeek",
            message_count=len(prepared_messages),
            has_tools=bool(tools),
            stream=stream,
        )

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120.0,
                ) as response:
                    response.raise_for_status()

                    if stream:
                        # Stream response chunks
                        async for chunk in self._parse_stream(response):
                            yield chunk
                    else:
                        # Return complete response
                        content = await response.aread()
                        data = json.loads(content)
                        yield data

        except httpx.HTTPStatusError as e:
            error_msg = f"DeepSeek API error: {e.response.status_code}"
            try:
                error_data = await e.response.aread()
                error_msg += f" - {error_data.decode()}"
            except Exception:
                pass
            logger.error(error_msg)
            raise DeepSeekError(error_msg) from e

        except httpx.RequestError as e:
            error_msg = f"DeepSeek request error: {str(e)}"
            logger.error(error_msg)
            raise DeepSeekError(error_msg) from e

    def _prepare_messages(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Prepare messages with system prompt and sanitization.

        Args:
            messages: Original messages
            system_prompt: Optional system prompt to prepend

        Returns:
            Prepared messages
        """
        result = []

        # Add system prompt if provided
        if system_prompt:
            result.append({
                "role": "system",
                "content": system_prompt,
            })

        # Process and sanitize messages
        for msg in messages:
            # DeepSeek API requirement: reasoning_content only when tool_calls present
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Must include reasoning_content (even if empty)
                if not msg.get("reasoning_content"):
                    msg["reasoning_content"] = ""
            else:
                # Remove reasoning_content when no tool_calls
                msg.pop("reasoning_content", None)

            result.append(msg)

        return result

    async def _parse_stream(
        self,
        response: httpx.Response,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Parse streaming response from DeepSeek.

        Args:
            response: HTTP response object

        Yields:
            Parsed response chunks
        """
        buffer = ""

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    yield chunk
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse stream chunk: {data}")
                    continue
