"""Tools endpoint."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from gemini_chat_backend.tools.registry import get_tool_registry
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""

    tool_name: str
    parameters: dict[str, Any]


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""

    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None


@router.get("/tools", tags=["tools"])
async def list_tools() -> dict[str, Any]:
    """List available tools.

    Returns:
        List of available tools
    """
    registry = get_tool_registry()
    tools = registry.list_tools()

    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]
    }


@router.post("/tools/execute", tags=["tools"])
async def execute_tool(
    request: ToolExecuteRequest,
) -> ToolExecuteResponse:
    """Execute a tool.

    Args:
        request: Tool execution request

    Returns:
        Tool execution response

    Raises:
        HTTPException: If tool execution fails
    """
    registry = get_tool_registry()
    tool = registry.get(request.tool_name)

    if not tool:
        logger.warning(f"Tool not found: {request.tool_name}")
        return ToolExecuteResponse(
            success=False,
            error=f"Tool '{request.tool_name}' not found",
        )

    try:
        logger.info(f"Executing tool: {request.tool_name}")
        result = await tool.execute(**request.parameters)

        if result.success:
            logger.info(f"Tool executed successfully: {request.tool_name}")
        else:
            logger.warning(f"Tool execution failed: {request.tool_name} - {result.error}")

        return ToolExecuteResponse(
            success=result.success,
            result=result.result,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Unexpected error executing tool {request.tool_name}: {e}")
        return ToolExecuteResponse(
            success=False,
            error=str(e),
        )
