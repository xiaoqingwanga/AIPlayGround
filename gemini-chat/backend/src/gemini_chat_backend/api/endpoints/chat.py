"""Chat endpoint with streaming support."""

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from gemini_chat_backend.config import settings
from gemini_chat_backend.core.deepseek import DeepSeekClient, DeepSeekError
from gemini_chat_backend.models.chat import ChatRequest, StreamEvent
from gemini_chat_backend.utils.logging import get_request_logger

router = APIRouter()

# System prompt for ReAct pattern
REACT_SYSTEM_PROMPT = """You are an AI assistant that follows the ReAct (Reasoning + Acting) pattern.

When given a task, follow this pattern:

1. **Thought**: Think step-by-step about what you need to do. Explain your reasoning.
2. **Action**: If you need to use a tool to progress, make the tool call.
3. **Observation**: After receiving the tool result, analyze what you learned.
4. **Repeat**: Continue the Thought → Action → Observation cycle until you have enough information to provide a final answer.

**Important Guidelines:**
- Always show your reasoning in your thoughts
- Only use tools when necessary to gather information or perform actions
- After each observation, decide if you need more information or can provide the final answer
- Your final answer should directly address the user's question"""


def format_sse(event: StreamEvent) -> str:
    """Format a stream event as SSE.

    Args:
        event: Stream event

    Returns:
        SSE formatted string
    """
    return f"data: {json.dumps(event.model_dump())}\n\n"


async def chat_stream(
    request: ChatRequest,
    client: DeepSeekClient,
    request_id: str,
) -> AsyncIterator[str]:
    """Generate chat stream.

    Args:
        request: Chat request
        client: DeepSeek client
        request_id: Request ID for logging

    Yields:
        SSE formatted strings
    """
    logger = get_request_logger(request_id)

    try:
        # Convert messages to dict format
        messages = [msg.model_dump() for msg in request.messages]

        # Get tools from registry (placeholder - will be implemented later)
        tools = None

        logger.info(
            "Starting chat stream",
            message_count=len(messages),
            has_tools=bool(tools),
        )

        # Stream response from DeepSeek
        async for chunk in client.chat(
            messages=messages,
            tools=tools,
            stream=True,
            max_tokens=request.max_tokens,
            system_prompt=REACT_SYSTEM_PROMPT,
        ):
            # Extract content from chunk
            delta = chunk.get("choices", [{}])[0].get("delta", {})

            if delta.get("content"):
                event = StreamEvent(
                    type="content",
                    data=delta["content"],
                )
                yield format_sse(event)

            if delta.get("reasoning_content"):
                event = StreamEvent(
                    type="reasoning",
                    data=delta["reasoning_content"],
                )
                yield format_sse(event)

            # Handle tool calls (will be expanded later)
            if delta.get("tool_calls"):
                event = StreamEvent(
                    type="tool_call",
                    data=delta["tool_calls"],
                )
                yield format_sse(event)

        # Send done event
        done_event = StreamEvent(
            type="done",
            data=None,
        )
        yield format_sse(done_event)

        logger.info("Chat stream completed")

    except DeepSeekError as e:
        logger.error(f"DeepSeek error: {e}")
        error_event = StreamEvent(
            type="error",
            data={"message": str(e)},
        )
        yield format_sse(error_event)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        error_event = StreamEvent(
            type="error",
            data={"message": "Internal server error"},
        )
        yield format_sse(error_event)


@router.post("/chat")
async def chat(
    request: ChatRequest,
) -> StreamingResponse:
    """Chat endpoint with streaming support.

    Args:
        request: Chat request with messages

    Returns:
        Streaming response with SSE events
    """
    request_id = str(uuid.uuid4())
    client = DeepSeekClient()

    return StreamingResponse(
        chat_stream(request, client, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )
