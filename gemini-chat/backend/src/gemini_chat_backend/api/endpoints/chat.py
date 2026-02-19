"""Chat endpoint with streaming support and ReAct pattern."""

import json
import uuid
from typing import Any, AsyncIterator, Dict, List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from gemini_chat_backend.config import settings
from gemini_chat_backend.core.deepseek import DeepSeekClient, DeepSeekError
from gemini_chat_backend.core.react_orchestrator import ReActOrchestrator
from gemini_chat_backend.core.reasoning_parser import (
    clean_reasoning_content,
    extract_thought_title,
)
from gemini_chat_backend.models.chat import ChatRequest, StreamEvent
from gemini_chat_backend.tools.registry import get_tool_registry
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
    """Generate chat stream with ReAct pattern.

    Args:
        request: Chat request
        client: DeepSeek client
        request_id: Request ID for logging

    Yields:
        SSE formatted strings
    """
    logger = get_request_logger(request_id)
    tool_registry = get_tool_registry()

    try:
        # Get tools from registry
        tools = tool_registry.get_definitions() if tool_registry.list_tools() else None

        logger.info(
            "Starting chat stream",
            message_count=len(request.messages),
            has_tools=bool(tools),
        )

        # Current messages state (updated with each tool call)
        # Convert Pydantic models to dicts, ONLY include fields DeepSeek recognizes
        def to_deepseek_message(msg: Any) -> Dict[str, Any]:
            """Convert message to only DeepSeek-recognized fields."""
            msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else dict(msg)
            # Also get the raw model to check extra fields
            clean: Dict[str, Any] = {
                "role": msg_dict.get("role", "user"),
                "content": msg_dict.get("content", ""),
            }
            # Check both snake_case and camelCase (from dict keys and extra fields)
            tool_calls = msg_dict.get("tool_calls") or msg_dict.get("toolCalls") or (hasattr(msg, "toolCalls") and msg.toolCalls)
            tool_call_id = msg_dict.get("tool_call_id") or msg_dict.get("toolCallId") or (hasattr(msg, "toolCallId") and msg.toolCallId)
            reasoning_content = msg_dict.get("reasoning_content") or msg_dict.get("reasoningContent") or (hasattr(msg, "reasoningContent") and msg.reasoningContent)

            if tool_calls:
                clean["tool_calls"] = tool_calls
            if tool_call_id:
                clean["tool_call_id"] = tool_call_id
            if reasoning_content:
                clean["reasoning_content"] = reasoning_content
            return clean

        current_messages: List[Dict[str, Any]] = [to_deepseek_message(m) for m in request.messages]

        # Create ReAct orchestrator
        react_orchestrator = ReActOrchestrator(
            lambda step: None,  # No-op callback, we'll send manually
            max_iterations=10,
        )

        # Main ReAct loop
        iteration = 0
        max_iterations = 10

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"ReAct iteration {iteration}/{max_iterations}")

            # Stream response from DeepSeek
            current_content = ""
            current_reasoning = ""
            tool_calls: List[Dict[str, Any]] = []

            async for chunk in client.chat(
                messages=current_messages,
                tools=tools,
                stream=True,
                max_tokens=request.max_tokens,
                system_prompt=REACT_SYSTEM_PROMPT,
            ):
                # Extract content from chunk
                delta = chunk.get("choices", [{}])[0].get("delta", {})

                if delta.get("content"):
                    content = delta["content"]
                    current_content += content
                    event = StreamEvent(
                        type="content",
                        data=content,
                    )
                    yield format_sse(event)

                if delta.get("reasoning_content"):
                    reasoning = delta["reasoning_content"]
                    current_reasoning += reasoning

                    # Clean up the full reasoning content
                    cleaned_reasoning = clean_reasoning_content(current_reasoning)

                    if cleaned_reasoning:
                        # Stream the cleaned reasoning (we stream the delta by just sending
                        # the new chunk, but ensure we don't stream gibberish)
                        # For streaming, we send the raw delta but the thought gets cleaned content
                        event = StreamEvent(
                            type="reasoning",
                            data=reasoning,
                        )
                        yield format_sse(event)

                        # Record/Update thought in ReAct orchestrator with cleaned content
                        steps = react_orchestrator.get_steps()
                        last_step = steps[-1] if steps else None

                        # Extract a title for the thought
                        thought_title = extract_thought_title(cleaned_reasoning)

                        if last_step and last_step.type == "thought":
                            # Update existing thought in-place with cleaned content
                            last_step.content = cleaned_reasoning
                            if thought_title:
                                last_step.title = thought_title
                            event = StreamEvent(
                                type="react_step",
                                data=last_step.model_dump(mode="json", by_alias=True),
                            )
                            yield format_sse(event)
                        else:
                            # No existing thought - create new one with cleaned content
                            thought = await react_orchestrator.record_thought(
                                cleaned_reasoning,
                                title=thought_title,
                                leads_to="action" if delta.get("tool_calls") else "response",
                            )
                            event = StreamEvent(
                                type="react_step",
                                data=thought.model_dump(mode="json", by_alias=True),
                            )
                            yield format_sse(event)

                # Handle tool calls
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index")
                        if idx is not None:
                            # Ensure array has space
                            while len(tool_calls) <= idx:
                                tool_calls.append({
                                    "id": f"tool-{int(uuid.uuid4())}-{len(tool_calls)}",
                                    "name": "",
                                    "arguments": "",
                                })

                            # Update with ID if provided
                            if tc.get("id"):
                                tool_calls[idx]["id"] = tc["id"]

                            # Update name
                            if tc.get("function", {}).get("name"):
                                tool_calls[idx]["name"] = tc["function"]["name"]

                            # Accumulate arguments
                            tool_calls[idx]["arguments"] += (
                                tc.get("function", {}).get("arguments", "")
                            )

            # If no tool calls, we're done
            if not tool_calls:
                logger.info("No tool calls, finishing chat")
                break

            logger.info(f"Got {len(tool_calls)} tool call(s)")

            # Add assistant message with tool calls to conversation
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": current_content,
                "reasoning_content": current_reasoning,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ],
            }
            current_messages.append(assistant_msg)

            # Execute each tool call
            for tc in tool_calls:
                tool_call_id = tc["id"]
                tool_name = tc["name"]

                # Parse arguments
                try:
                    parameters = json.loads(tc.get("arguments", "{}"))
                except json.JSONDecodeError:
                    parameters = {}

                # Create tool call object for streaming
                tool_call_data = {
                    "id": tool_call_id,
                    "name": tool_name,
                    "parameters": parameters,
                    "timestamp": int(uuid.uuid4().time_low),
                }

                # Send tool_call event
                event = StreamEvent(
                    type="tool_call",
                    data=tool_call_data,
                )
                yield format_sse(event)

                # Record as action in ReAct orchestrator
                action = await react_orchestrator.record_action(tool_call_data)
                event = StreamEvent(
                    type="react_step",
                    data=action.model_dump(mode="json", by_alias=True),
                )
                yield format_sse(event)

                # Get and execute the tool
                tool = tool_registry.get(tool_name) if tool_registry else None

                if tool:
                    try:
                        result = await tool.execute(**parameters)

                        if result.success:
                            # Send tool_result event
                            event = StreamEvent(
                                type="tool_result",
                                data={
                                    "toolCallId": tool_call_id,
                                    "result": result.result,
                                },
                            )
                            yield format_sse(event)

                            # Record as observation
                            observation = await react_orchestrator.record_observation(
                                action.id,
                                result=result.result,
                            )
                            event = StreamEvent(
                                type="react_step",
                                data=observation.model_dump(mode="json", by_alias=True),
                            )
                            yield format_sse(event)

                            # Add tool message
                            current_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(result.result) if result.result else "",
                            })
                        else:
                            # Send tool_error event
                            event = StreamEvent(
                                type="tool_error",
                                data={
                                    "toolCallId": tool_call_id,
                                    "error": result.error or "Unknown error",
                                },
                            )
                            yield format_sse(event)

                            # Record as observation with error
                            observation = await react_orchestrator.record_observation(
                                action.id,
                                error=result.error,
                            )
                            event = StreamEvent(
                                type="react_step",
                                data=observation.model_dump(mode="json", by_alias=True),
                            )
                            yield format_sse(event)

                            # Add tool message with error
                            current_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f"Error: {result.error}" if result.error else "Error",
                            })

                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        event = StreamEvent(
                            type="tool_error",
                            data={
                                "toolCallId": tool_call_id,
                                "error": str(e),
                            },
                        )
                        yield format_sse(event)

                        observation = await react_orchestrator.record_observation(
                            action.id,
                            error=str(e),
                        )
                        event = StreamEvent(
                            type="react_step",
                            data=observation.model_dump(mode="json", by_alias=True),
                        )
                        yield format_sse(event)

                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": f"Error: {e}",
                        })
                else:
                    # Tool not found
                    error_msg = f"Error: Tool '{tool_name}' not found"
                    event = StreamEvent(
                        type="tool_error",
                        data={
                            "toolCallId": tool_call_id,
                            "error": error_msg,
                        },
                    )
                    yield format_sse(event)

                    observation = await react_orchestrator.record_observation(
                        action.id,
                        error=error_msg,
                    )
                    event = StreamEvent(
                        type="react_step",
                        data=observation.model_dump(mode="json", by_alias=True),
                    )
                    yield format_sse(event)

                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": error_msg,
                    })

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
    """Chat endpoint with streaming support and ReAct pattern.

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
