"""Tool modules for Gemini Chat Backend."""

from gemini_chat_backend.tools.base import BaseTool, ToolResult
from gemini_chat_backend.tools.exec import JSExecTool, PythonExecTool
from gemini_chat_backend.tools.file import FileReadTool, FileWriteTool
from gemini_chat_backend.tools.registry import ToolRegistry, get_tool_registry
from gemini_chat_backend.utils.logging import get_logger
from gemini_chat_backend.config import settings

logger = get_logger(__name__)


def register_tools() -> None:
    """Register all available tools in the global registry.

    Call this on application startup to make tools available.
    """
    registry = get_tool_registry()

    # Always register read tools
    registry.register(FileReadTool())

    # Conditionally register write/execution tools
    if not settings.TOOL_READ_ONLY_MODE:
        registry.register(FileWriteTool())
        registry.register(PythonExecTool())
        registry.register(JSExecTool())
    else:
        logger.info("Read-only mode enabled: write/execution tools are disabled")

    logger.info(f"Registered {len(registry)} tools: {[t.name for t in registry.list_tools()]}")


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "get_tool_registry",
    "register_tools",
    "FileReadTool",
    "FileWriteTool",
    "PythonExecTool",
    "JSExecTool",
]
