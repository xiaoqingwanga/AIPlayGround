"""Code execution tools."""

import asyncio
import sys
from typing import Any

from gemini_chat_backend.tools.base import BaseTool, ToolResult
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)


class PythonExecTool(BaseTool):
    """Tool to execute Python code."""

    def __init__(self) -> None:
        """Initialize Python exec tool."""
        super().__init__(
            name="python_exec",
            description="Execute Python code (timeout: 30s). Use single quotes for strings inside code.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute (prefer single quotes for internal strings)",
                    },
                },
                "required": ["code"],
            },
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute Python code.

        Args:
            **kwargs: Tool parameters (code)

        Returns:
            Tool execution result with stdout and stderr
        """
        try:
            code = kwargs.get("code", "")
            if not code:
                return ToolResult(success=False, error="Code is required")

            # Run Python code as subprocess - no need to escape quotes when passing as separate argument
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                # Wait with timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(success=False, error="Execution timeout (30s)")

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            logger.info("Python code executed successfully")
            return ToolResult(success=True, result={"stdout": stdout, "stderr": stderr})

        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return ToolResult(success=False, error=str(e))


class JSExecTool(BaseTool):
    """Tool to execute JavaScript code."""

    def __init__(self) -> None:
        """Initialize JavaScript exec tool."""
        super().__init__(
            name="js_exec",
            description="Execute JavaScript code (timeout: 5s)",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "JavaScript code to execute",
                    },
                },
                "required": ["code"],
            },
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute JavaScript code.

        Args:
            **kwargs: Tool parameters (code)

        Returns:
            Tool execution result
        """
        try:
            code = kwargs.get("code", "")
            if not code:
                return ToolResult(success=False, error="Code is required")

            # Try to find node executable
            node_cmd = "node"
            if sys.platform == "win32":
                node_cmd = "node.exe"

            # Escape quotes safely
            escaped_code = code.replace("'", "\\'").replace("`", "\\`")

            proc = await asyncio.create_subprocess_exec(
                node_cmd,
                "-e",
                escaped_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(success=False, error="Execution timeout (5s)")

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if stderr:
                return ToolResult(success=False, error=stderr)

            logger.info("JavaScript code executed successfully")
            return ToolResult(success=True, result={"result": stdout})

        except FileNotFoundError:
            return ToolResult(success=False, error="Node.js not found in PATH")
        except Exception as e:
            logger.error(f"Error executing JavaScript code: {e}")
            return ToolResult(success=False, error=str(e))
