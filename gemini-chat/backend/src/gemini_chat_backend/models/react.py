"""ReAct pattern Pydantic models."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ReActThought(BaseModel):
    """ReAct thought step.

    Attributes:
        id: Thought ID
        type: Step type (always "thought")
        content: Thought content
        title: Optional thought title
        timestamp: Thought timestamp
        leads_to: What comes after this thought (response or action)
    """

    id: str
    type: Literal["thought"] = "thought"
    content: str
    title: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    leads_to: Optional[Literal["response", "action"]] = None


class ReActAction(BaseModel):
    """ReAct action step.

    Attributes:
        id: Action ID
        type: Step type (always "action")
        tool_call: The tool call to execute
        timestamp: Action timestamp
    """

    id: str
    type: Literal["action"] = "action"
    tool_call: Dict[str, Any]  # ToolCall serialized as dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReActObservation(BaseModel):
    """ReAct observation step.

    Attributes:
        id: Observation ID
        type: Step type (always "observation")
        action_id: Reference to the action that produced this observation
        result: Tool execution result
        error: Error message if execution failed
        timestamp: Observation timestamp
    """

    id: str
    type: Literal["observation"] = "observation"
    action_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Union type for all ReAct steps
ReActStep = Union[ReActThought, ReActAction, ReActObservation]


class ReActCycle(BaseModel):
    """ReAct cycle (thought -> action -> observation).

    Attributes:
        thought: The thought step
        action: The action step (optional)
        observation: The observation step (optional)
    """

    thought: ReActThought
    action: Optional[ReActAction] = None
    observation: Optional[ReActObservation] = None


class ReActState(BaseModel):
    """ReAct orchestration state.

    Attributes:
        steps: All steps in the ReAct cycle
        current_phase: Current phase (idle, thinking, acting, observing, complete)
        max_iterations: Maximum number of iterations
        current_iteration: Current iteration count
    """

    steps: List[ReActStep] = Field(default_factory=list)
    current_phase: Literal[
        "idle", "thinking", "acting", "observing", "complete"
    ] = "idle"
    max_iterations: int = 10
    current_iteration: int = 0
