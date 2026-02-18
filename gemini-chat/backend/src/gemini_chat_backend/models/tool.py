"""Tool-related Pydantic models."""

from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Tool parameter definition.

    Attributes:
        name: Parameter name
        type: Parameter type (string, integer, boolean, etc.)
        description: Parameter description
        required: Whether the parameter is required
    """

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True


class ToolDefinition(BaseModel):
    """Tool definition for API schema.

    Attributes:
        name: Tool name
        description: Tool description
        parameters: Tool parameters
    """

    name: str
    description: str
    parameters: List[ToolParameter]

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format.

        Returns:
            OpenAI function definition
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolCall(BaseModel):
    """Tool call from assistant.

    Attributes:
        id: Tool call ID
        name: Tool name
        parameters: Tool parameters
        result: Tool execution result (populated after execution)
        error: Error message if execution failed
    """

    id: str
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None


class ToolResult(BaseModel):
    """Tool execution result.

    Attributes:
        tool_call_id: Associated tool call ID
        result: Execution result
        error: Error message if failed
    """

    tool_call_id: str
    result: Optional[Any] = None
    error: Optional[str] = None


class Tool:
    """Tool class with execution capability.

    Attributes:
        name: Tool name
        description: Tool description
        parameters: Tool parameters
        handler: Tool execution handler
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter],
        handler: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ValueError: If required parameters are missing
        """
        # Validate parameters
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"Required parameter '{param.name}' missing")

        # Call handler
        import inspect

        if inspect.iscoroutinefunction(self.handler):
            return await self.handler(**kwargs)
        return self.handler(**kwargs)

    def to_definition(self) -> ToolDefinition:
        """Get tool definition for API schema.

        Returns:
            Tool definition
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )
