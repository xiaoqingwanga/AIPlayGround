"""Chat-related Pydantic models."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A chat message.

    Attributes:
        role: Message role (system, user, assistant, or tool)
        content: Message content
        tool_calls: Optional tool calls from assistant
        tool_call_id: Tool call ID for tool role messages
        reasoning_content: Reasoning content from DeepSeek
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, alias="toolCalls")
    tool_call_id: Optional[str] = Field(None, alias="toolCallId")
    reasoning_content: Optional[str] = Field(None, alias="reasoningContent")

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
    }


class ChatRequest(BaseModel):
    """Chat request payload.

    Attributes:
        messages: List of chat messages
        stream: Whether to stream the response
        max_tokens: Maximum tokens to generate
    """

    messages: List[Message]
    stream: bool = True
    max_tokens: Optional[int] = None


class StreamEvent(BaseModel):
    """Server-sent event for streaming responses.

    Attributes:
        type: Event type (reasoning, content, tool_call, tool_result, tool_error, react_step, done, error)
        data: Event data
    """

    type: Literal[
        "reasoning",
        "content",
        "tool_call",
        "tool_result",
        "tool_error",
        "react_step",
        "done",
        "error",
    ]
    data: Any


class ChatResponse(BaseModel):
    """Chat response payload.

    Attributes:
        message: Assistant message
        react_steps: Optional ReAct steps
    """

    message: Message
    react_steps: Optional[List[Dict[str, Any]]] = None
