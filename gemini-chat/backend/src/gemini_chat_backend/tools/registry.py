"""Tool registry for managing available tools."""

from typing import Any, Dict, List, Optional, Type

from gemini_chat_backend.tools.base import BaseTool, ToolResult
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    def unregister(self, name: str) -> None:
        """Unregister a tool.

        Args:
            name: Name of tool to unregister

        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")

        del self._tools[name]
        logger.info(f"Tool unregistered: {name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """List all registered tools.

        Returns:
            List of tool instances
        """
        return list(self._tools.values())

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for OpenAI API.

        Returns:
            List of tool definitions
        """
        return [tool.get_definition() for tool in self._tools.values()]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        logger.info("Tool registry cleared")

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool is registered
        """
        return name in self._tools

    def __len__(self) -> int:
        """Get number of registered tools.

        Returns:
            Number of tools
        """
        return len(self._tools)


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry instance.

    Returns:
        Global tool registry (creates if needed)
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry() -> None:
    """Reset global tool registry."""
    global _global_registry
    _global_registry = None
