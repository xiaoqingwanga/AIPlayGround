"""File operations tools."""

import os
from pathlib import Path
from typing import Any

from gemini_chat_backend.config import settings
from gemini_chat_backend.tools.base import BaseTool, ToolResult
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)


def _resolve_safe_path(file_path: str) -> Path:
    """Resolve a path safely within the working directory.

    Args:
        file_path: Path to resolve (relative to working directory)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path attempts to escape working directory
    """
    working_dir = Path(settings.TOOL_WORKING_DIRECTORY).resolve()
    resolved = (working_dir / file_path).resolve()

    if not str(resolved).startswith(str(working_dir)):
        raise ValueError(f"Access denied: Path outside working directory: {file_path}")

    return resolved


class FileReadTool(BaseTool):
    """Tool to read a file from the filesystem."""

    def __init__(self) -> None:
        """Initialize file read tool."""
        super().__init__(
            name="file_read",
            description="Read a file from the filesystem",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to working directory)",
                    },
                },
                "required": ["path"],
            },
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the file read tool.

        Args:
            **kwargs: Tool parameters (path)

        Returns:
            Tool execution result with file content
        """
        try:
            file_path = kwargs.get("path", "")
            if not file_path:
                return ToolResult(success=False, error="Path is required")

            full_path = _resolve_safe_path(file_path)

            if not full_path.exists():
                return ToolResult(success=False, error=f"File not found: {file_path}")

            if not full_path.is_file():
                return ToolResult(success=False, error=f"Not a file: {file_path}")

            content = full_path.read_text(encoding="utf-8")

            logger.info(f"File read successfully: {file_path}")
            return ToolResult(success=True, result={"path": file_path, "content": content})

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return ToolResult(success=False, error=str(e))


class FileWriteTool(BaseTool):
    """Tool to write content to a file."""

    def __init__(self) -> None:
        """Initialize file write tool."""
        super().__init__(
            name="file_write",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to working directory)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                },
                "required": ["path", "content"],
            },
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the file write tool.

        Args:
            **kwargs: Tool parameters (path, content)

        Returns:
            Tool execution result
        """
        try:
            file_path = kwargs.get("path", "")
            content = kwargs.get("content", "")

            if not file_path:
                return ToolResult(success=False, error="Path is required")

            full_path = _resolve_safe_path(file_path)

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            full_path.write_text(content, encoding="utf-8")

            logger.info(f"File written successfully: {file_path}")
            return ToolResult(success=True, result={"path": file_path, "success": True})

        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return ToolResult(success=False, error=str(e))
