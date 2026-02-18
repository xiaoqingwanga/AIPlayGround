import { ReActStep, ReActThought, ReActAction, ReActObservation, ToolCall } from '@/lib/types';

interface ReActState {
  steps: ReActStep[];
  currentPhase: 'idle' | 'thinking' | 'acting' | 'observing' | 'complete';
  maxIterations: number;
  currentIteration: number;
}

export class ReActOrchestrator {
  private state: ReActState;
  private onStep: (step: ReActStep) => void;

  constructor(
    onStep: (step: ReActStep) => void,
    maxIterations: number = 10
  ) {
    this.onStep = onStep;
    this.state = {
      steps: [],
      currentPhase: 'idle',
      maxIterations,
      currentIteration: 0,
    };
  }

  /**
   * Start a new ReAct cycle with an initial thought
   */
  async start(initialThought: string, title?: string): Promise<void> {
    this.state.currentPhase = 'thinking';
    this.state.currentIteration = 0;

    const thought: ReActThought = {
      id: `thought-${Date.now()}`,
      type: 'thought',
      content: initialThought,
      title,
      timestamp: Date.now(),
    };

    this.addStep(thought);
  }

  /**
   * Record a thought that leads to an action
   */
  async recordThought(content: string, title?: string, leadsTo: 'response' | 'action' = 'action'): Promise<ReActThought> {
    this.state.currentPhase = 'thinking';

    const thought: ReActThought = {
      id: `thought-${Date.now()}`,
      type: 'thought',
      content,
      title,
      timestamp: Date.now(),
      leadsTo,
    };

    this.addStep(thought);
    return thought;
  }

  /**
   * Record an action (tool call) resulting from a thought
   */
  async recordAction(toolCall: ToolCall): Promise<ReActAction> {
    this.state.currentPhase = 'acting';

    const action: ReActAction = {
      id: `action-${Date.now()}`,
      type: 'action',
      toolCall,
      timestamp: Date.now(),
    };

    this.addStep(action);
    return action;
  }

  /**
   * Record an observation from an action's result
   */
  async recordObservation(
    actionId: string,
    result?: any,
    error?: string
  ): Promise<ReActObservation> {
    this.state.currentPhase = 'observing';

    const observation: ReActObservation = {
      id: `observation-${Date.now()}`,
      type: 'observation',
      actionId,
      result,
      error,
      timestamp: Date.now(),
    };

    this.addStep(observation);

    // Increment iteration after full cycle
    this.state.currentIteration++;

    // Check if we've reached max iterations
    if (this.state.currentIteration >= this.state.maxIterations) {
      this.state.currentPhase = 'complete';
    }

    return observation;
  }

  /**
   * Record a follow-up thought after an observation
   */
  async recordFollowUpThought(content: string, title?: string): Promise<ReActThought | null> {
    if (this.state.currentIteration >= this.state.maxIterations) {
      return null;
    }

    this.state.currentPhase = 'thinking';

    const thought: ReActThought = {
      id: `thought-${Date.now()}`,
      type: 'thought',
      content,
      title,
      timestamp: Date.now(),
    };

    this.addStep(thought);
    return thought;
  }

  /**
   * Get the current state of the ReAct cycle
   */
  getState(): ReActState {
    return { ...this.state };
  }

  /**
   * Get all steps in the current cycle
   */
  getSteps(): ReActStep[] {
    return [...this.state.steps];
  }

  /**
   * Group steps into ReAct cycles (thought -> action -> observation)
   */
  getCycles(): ReActCycle[] {
    const cycles: ReActCycle[] = [];
    let currentCycle: ReActCycle | null = null;

    for (const step of this.state.steps) {
      if (step.type === 'thought') {
        // Start a new cycle
        if (currentCycle) {
          cycles.push(currentCycle);
        }
        currentCycle = { thought: step, action: null, observation: null };
      } else if (step.type === 'action' && currentCycle) {
        currentCycle.action = step;
      } else if (step.type === 'observation' && currentCycle) {
        currentCycle.observation = step;
        cycles.push(currentCycle);
        currentCycle = null;
      }
    }

    // Don't forget the last incomplete cycle
    if (currentCycle) {
      cycles.push(currentCycle);
    }

    return cycles;
  }

  private addStep(step: ReActStep): void {
    this.state.steps.push(step);
    this.onStep(step);
  }
}

export interface ReActCycle {
  thought: ReActThought;
  action: ReActAction | null;
  observation: ReActObservation | null;
}

/**
 * Helper function to determine if a thought should lead to an action or response
 */
export function shouldTakeAction(thought: ReActThought): boolean {
  const actionIndicators = [
    /I (should|need to|will|must) (use|call|execute|run|invoke)/i,
    /let me (use|call|execute|run|invoke)/i,
    /I'?ll (use|call|execute|run|invoke)/i,
  ];

  return actionIndicators.some(pattern => pattern.test(thought.content));
}

/**
 * Helper function to extract the intended tool from a thought
 */
export function extractToolFromThought(thought: ReActThought): string | null {
  const toolPatterns: { [key: string]: RegExp } = {
    'file_read': /read (?:the )?file|file content|contents of/i,
    'file_write': /write (?:to )?(?:the )?file|save (?:to )?file|create file/i,
    'python_exec': /run python|execute python|python code/i,
    'js_exec': /run javascript|execute js|javascript code|node.js/i,
  };

  for (const [tool, pattern] of Object.entries(toolPatterns)) {
    if (pattern.test(thought.content)) {
      return tool;
    }
  }

  return null;
}
