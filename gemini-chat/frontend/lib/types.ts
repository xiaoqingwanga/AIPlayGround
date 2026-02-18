// Conversation types
export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

// ReAct step types
export interface ReActThought {
  id: string;
  type: 'thought';
  content: string;           // The reasoning/thinking content
  title?: string;           // Optional title for this thought
  timestamp: number;
  leadsTo?: 'response' | 'action';  // What comes after this thought
}

export interface ReActAction {
  id: string;
  type: 'action';
  toolCall: ToolCall;       // The tool call to execute
  timestamp: number;
}

export interface ReActObservation {
  id: string;
  type: 'observation';
  actionId: string;         // Reference to the action that produced this
  result?: any;             // Tool execution result
  error?: string;           // Error message if failed
  timestamp: number;
}

export type ReActStep = ReActThought | ReActAction | ReActObservation;

// Message types
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: number;
  thinking?: string;
  thinkingSteps?: ThinkingStep[];
  reactSteps?: ReActStep[];  // New: ReAct pattern steps
  toolCalls?: ToolCall[];
  toolCallId?: string;  // Required for 'tool' role messages to associate with tool calls
  reasoningContent?: string;  // DeepSeek reasoning_content for assistant messages with tool_calls (MUST be present, even if empty)
}

export interface ThinkingStep {
  id: string;
  type: 'task' | 'reasoning' | 'reflection' | 'tool_planning';
  title: string;
  content: string;
  reflection?: string;
  timestamp: number;
}

export interface ToolCall {
  id: string;
  name: string;
  parameters: Record<string, any>;
  result?: any;
  error?: string;
  timestamp: number;
}

// Tool definitions
export interface Tool {
  name: string;
  description: string;
  parameters: {
    type: 'object';
    properties: Record<string, any>;
    required: string[];
  };
  execute: (params: any) => Promise<any>;
}

// Stream event types
export type StreamEvent =
  | { type: 'reasoning'; data: string }
  | { type: 'thinking'; data: ThinkingStep }
  | { type: 'react_step'; data: ReActStep }  // New: ReAct step event
  | { type: 'tool_call'; data: ToolCall }
  | { type: 'tool_result'; data: { toolCallId: string; result: any } }
  | { type: 'tool_error'; data: { toolCallId: string; error: string } }
  | { type: 'content'; data: string }
  | { type: 'done'; data: null };
