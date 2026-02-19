"""ReAct (Reasoning + Acting) pattern orchestrator."""

import time
from typing import Any, Callable, List, Literal, Optional

from gemini_chat_backend.models.react import (
    ReActAction,
    ReActObservation,
    ReActStep,
    ReActThought,
)
from gemini_chat_backend.utils.logging import get_logger

logger = get_logger(__name__)


class ReActOrchestrator:
    """Orchestrator for the ReAct (Reasoning + Acting) pattern.

    Manages the thought -> action -> observation cycle and streams
    events as they occur.
    """

    def __init__(
        self,
        on_step: Callable[[ReActStep], None],
        max_iterations: int = 10,
    ) -> None:
        """Initialize ReAct orchestrator.

        Args:
            on_step: Callback called when a new step is added
            max_iterations: Maximum number of ReAct cycles
        """
        self.on_step = on_step
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.steps: List[ReActStep] = []
        self.current_phase: Literal[
            "idle", "thinking", "acting", "observing", "complete"
        ] = "idle"

    async def record_thought(
        self,
        content: str,
        title: Optional[str] = None,
        leads_to: Optional[Literal["response", "action"]] = None,
    ) -> ReActThought:
        """Record a thought step.

        Args:
            content: The reasoning content
            title: Optional title for the thought
            leads_to: What this thought leads to (response or action)

        Returns:
            The created ReActThought
        """
        self.current_phase = "thinking"

        thought = ReActThought(
            id=f"thought-{int(time.time() * 1000)}",
            type="thought",
            content=content,
            title=title,
            leads_to=leads_to,
        )

        self._add_step(thought)
        logger.debug(f"Recorded thought: {content[:100]}...")
        return thought

    async def record_action(
        self,
        tool_call: dict[str, Any],
    ) -> ReActAction:
        """Record an action (tool call) step.

        Args:
            tool_call: The tool call to execute

        Returns:
            The created ReActAction
        """
        self.current_phase = "acting"

        action = ReActAction(
            id=f"action-{int(time.time() * 1000)}",
            type="action",
            tool_call=tool_call,
        )

        self._add_step(action)
        logger.debug(f"Recorded action: {tool_call.get('name')}")
        return action

    async def record_observation(
        self,
        action_id: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> ReActObservation:
        """Record an observation from an action's result.

        Args:
            action_id: Reference to the action that produced this observation
            result: Tool execution result
            error: Error message if execution failed

        Returns:
            The created ReActObservation
        """
        self.current_phase = "observing"

        observation = ReActObservation(
            id=f"observation-{int(time.time() * 1000)}",
            type="observation",
            action_id=action_id,
            result=result,
            error=error,
        )

        self._add_step(observation)

        # Increment iteration after full cycle
        self.current_iteration += 1

        # Check if we've reached max iterations
        if self.current_iteration >= self.max_iterations:
            self.current_phase = "complete"
            logger.warning(f"Reached max iterations: {self.max_iterations}")

        logger.debug(f"Recorded observation for action: {action_id}")
        return observation

    async def record_follow_up_thought(
        self,
        content: str,
        title: Optional[str] = None,
    ) -> Optional[ReActThought]:
        """Record a follow-up thought after an observation.

        Args:
            content: The reasoning content
            title: Optional title for the thought

        Returns:
            The created ReActThought, or None if max iterations reached
        """
        if self.current_iteration >= self.max_iterations:
            return None

        self.current_phase = "thinking"

        thought = ReActThought(
            id=f"thought-{int(time.time() * 1000)}",
            type="thought",
            content=content,
            title=title,
        )

        self._add_step(thought)
        return thought

    def get_steps(self) -> List[ReActStep]:
        """Get all steps in the current cycle.

        Returns:
            List of all ReAct steps
        """
        return list(self.steps)

    def get_state(self) -> dict[str, Any]:
        """Get the current state of the ReAct cycle.

        Returns:
            State dictionary
        """
        return {
            "steps": [step.model_dump() for step in self.steps],
            "current_phase": self.current_phase,
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
        }

    def _add_step(self, step: ReActStep) -> None:
        """Add a step and call the callback.

        Args:
            step: The ReAct step to add
        """
        self.steps.append(step)
        self.on_step(step)
