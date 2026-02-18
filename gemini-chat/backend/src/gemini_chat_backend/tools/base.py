"""Base tool class."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Tool execution result.

    Attributes:
        success: Whether the execution was successful
        result: The result data (if successful)
        error: Error message (if failed)
    """

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class BaseTool(ABC):
    """Base class for all tools.

    Attributes:
        name: Tool name
        description: Tool description
        parameters: JSON schema for tool parameters
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        pass

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for OpenAI API.

        Returns:
            Tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
