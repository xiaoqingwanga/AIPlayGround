"""Tool modules for Gemini Chat Backend."""

from gemini_chat_backend.tools.base import BaseTool, ToolResult
from gemini_chat_backend.tools.exec import JSExecTool, PythonExecTool
from gemini_chat_backend.tools.file import FileReadTool, FileWriteTool
from gemini_chat_backend.tools.registry import ToolRegistry, get_tool_registry
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)


def register_tools() -> None:
    """Register all available tools in the global registry.

    Call this on application startup to make tools available.
    """
    registry = get_tool_registry()

    # Register file tools
    registry.register(FileReadTool())
    registry.register(FileWriteTool())

    # Register execution tools
    registry.register(PythonExecTool())
    registry.register(JSExecTool())

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
