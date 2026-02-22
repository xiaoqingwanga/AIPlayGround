"""Chat endpoint with streaming support and ReAct pattern."""

import json
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from gemini_chat_backend.config import settings
from gemini_chat_backend.core.deepseek import DeepSeekClient, DeepSeekError
from gemini_chat_backend.core.reasoning_parser import extract_thought_title
from gemini_chat_backend.models.react import (
    ReActAction,
    ReActObservation,
    ReActStep,
    ReActThought,
)
from gemini_chat_backend.models.chat import ChatRequest, StreamEvent
from gemini_chat_backend.tools.registry import get_tool_registry
from gemini_chat_backend.utils.logging import get_request_logger

router = APIRouter()

# System prompt for ReAct pattern
REACT_SYSTEM_PROMPT = """You are an AI assistant that follows the ReAct (Reasoning + Acting) pattern.

**Core Principle: Think First, Call Tools Wisely**

When given a task, follow this pattern:

1. **Thought**: Think step-by-step about what you need to do. Explain your reasoning.
2. **Action**: Use a tool ONLY when necessary to progress.
3. **Observation**: After receiving the tool result, analyze what you learned.
4. **Repeat**: Continue the Thought → Action → Observation cycle until you have enough information to provide a final answer.

---

**When SHOULD you call tools?**

Consider calling tools only when ANY of these conditions are met:
- User explicitly asks for real-time information (weather, time, stock prices, news, etc.)
- Need to execute code, run programs, or access the file system
- Need to search the internet for current information
- Need mathematical calculations beyond basic arithmetic (complex data analysis)
- Need to call external APIs for specific data

**When should you NOT call tools?**

Provide direct answers when ANY of these conditions are met:
- Greetings, casual chat, or social conversation
- Questions about your identity, capabilities, or basic introduction (without actual calls)
- Creative writing, text composition, summarization, or translation
- General knowledge questions or explanations within your training data
- User requests advice, opinions, or analytical perspectives
- Code review, logic analysis, or similar tasks that don't require execution
- Questions that can be answered from conversation context

**Tool Usage Decision Process:**

1. First, ask: Can I answer this question with existing knowledge or conversation context?
   - If YES → Answer directly, do NOT call tools

2. Second, ask: Does the question explicitly require external information or operations?
   - If NO → Explain why no tool is needed, then answer directly

3. Call tools only if BOTH steps above confirm the need

---

**Important Guidelines:**
- Always show your reasoning in your thoughts, especially decisions about "why NOT to call tools"
- Tool calls consume time and resources; use them judiciously
- Avoid calling tools just to "show off" capabilities
- Prioritize direct answers unless there's a clear reason to use a tool
- If uncertain, try answering without tools first
- After each observation, decide if you need more information or can provide the final answer
- Your final answer should directly address the user's question

**Example Comparisons:**

❌ Do NOT do this:
User: "Hello"
Thought: "Let me call the weather tool" ← WRONG, greetings don't need tools

✅ Do this instead:
User: "Hello"
Thought: "This is a greeting, I can respond directly" ← CORRECT

❌ Do NOT do this:
User: "Explain what recursion is"
Thought: "Let me search for the definition of recursion" ← WRONG, this is basic knowledge

✅ Do this instead:
User: "Explain what recursion is"
Thought: "Recursion is a fundamental concept in computer science, I can explain it directly" ← CORRECT

✅ When tools are genuinely needed:
User: "What's the weather in Beijing today?"
Thought: "Need to query real-time weather information, should call the weather tool" ← CORRECT"""


def format_sse(event: StreamEvent) -> str:
    """Format a stream event as SSE.

    Args:
        event: Stream event

    Returns:
        SSE formatted string
    """
    return f"data: {json.dumps(event.model_dump())}\n\n"


def _ensure_thought_exists(
    last_step: Optional[ReActStep],
    tool_name: str,
) -> Tuple[Optional[ReActStep], Optional[ReActThought]]:
    """Ensure a thought step exists before creating an action.

    If last step is not a thought, creates a placeholder thought.
    This handles cases where DeepSeek sends tool_calls without reasoning_content.

    Args:
        last_step: The last ReAct step created
        tool_name: Name of the tool being called (for placeholder context)

    Returns:
        Tuple of (updated last_step, created thought or None)
    """
    if last_step and last_step.type == "thought":
        return last_step, None

    # Create a placeholder thought
    placeholder_content = f"Executing tool call without explicit reasoning: {tool_name}"
    thought = ReActThought(
        id=f"thought-{int(time.time() * 1000)}",
        content=placeholder_content,
        title="Implicit reasoning",
        leads_to="action",
    )

    return thought, thought


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
        def to_deepseek_message(msg: Message) -> Dict[str, Any]:
            """Convert message to only DeepSeek-recognized fields."""
            return msg.model_dump(exclude_none=True)

        current_messages: List[Dict[str, Any]] = [to_deepseek_message(m) for m in request.messages]

        # Track the last ReAct step for in-place updates during streaming
        last_step: Optional[ReActStep] = None

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

                    if current_reasoning:
                        # Stream the reasoning
                        event = StreamEvent(
                            type="reasoning",
                            data=reasoning,
                        )
                        yield format_sse(event)

                        # Extract a title for the thought
                        thought_title = extract_thought_title(current_reasoning)

                        if last_step and last_step.type == "thought":
                            # Update existing thought in-place
                            last_step.content = current_reasoning
                            if thought_title:
                                last_step.title = thought_title
                            event = StreamEvent(
                                type="react_step",
                                data=last_step.model_dump(mode="json", by_alias=True),
                            )
                            yield format_sse(event)
                        else:
                            # No existing thought - create new one
                            thought = ReActThought(
                                id=f"thought-{int(time.time() * 1000)}",
                                content=current_reasoning,
                                title=thought_title,
                                leads_to="action" if delta.get("tool_calls") else "response",
                            )
                            last_step = thought
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

                # Ensure a thought exists before creating an action
                last_step, new_thought = _ensure_thought_exists(last_step, tool_name)

                # If a placeholder thought was created, yield it
                if new_thought:
                    event = StreamEvent(
                        type="react_step",
                        data=new_thought.model_dump(mode="json", by_alias=True),
                    )
                    yield format_sse(event)

                # Record as action
                action = ReActAction(
                    id=f"action-{int(time.time() * 1000)}",
                    tool_call=tool_call_data,
                )
                last_step = action
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
                            observation = ReActObservation(
                                id=f"observation-{int(time.time() * 1000)}",
                                action_id=action.id,
                                result=result.result,
                            )
                            last_step = observation
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
                            observation = ReActObservation(
                                id=f"observation-{int(time.time() * 1000)}",
                                action_id=action.id,
                                error=result.error,
                            )
                            last_step = observation
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

                        observation = ReActObservation(
                            id=f"observation-{int(time.time() * 1000)}",
                            action_id=action.id,
                            error=str(e),
                        )
                        last_step = observation
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

                    observation = ReActObservation(
                        id=f"observation-{int(time.time() * 1000)}",
                        action_id=action.id,
                        error=error_msg,
                    )
                    last_step = observation
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
