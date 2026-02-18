import { Tool } from '@/lib/types';

const DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions';

export interface DeepSeekMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_call_id?: string;
  tool_calls?: Array<{
    id: string;
    type: 'function';
    function: {
      name: string;
      arguments: string;
    };
  }>;
  /**
   * `reasoning_content` is received from DeepSeek API responses.
   * For assistant messages that include tool_calls, this field MUST be included
   * when sending the message back in conversation history. For messages without
   * tool_calls, this field should NOT be included.
   */
  reasoning_content?: string;
}

export interface DeepSeekDelta {
  role?: string;
  content?: string;
  reasoning_content?: string;
  tool_calls?: Array<{
    index?: number;
    id?: string;
    type?: 'function';
    function?: {
      name?: string;
      arguments?: string;
    };
  }>;
}

export interface CallDeepSeekOptions {
  messages: DeepSeekMessage[];
  tools: Tool[];
  stream?: boolean;
  maxIterations?: number;
}

export async function callDeepSeek({
  messages,
  tools,
  stream = true,
}: CallDeepSeekOptions) {
  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    throw new Error('DEEPSEEK_API_KEY is not set');
  }

  // DeepSeek API requirement:
  // - If an assistant message has tool_calls, it MUST also include reasoning_content
  // - Otherwise, reasoning_content should NOT be included
  const sanitizedMessages = messages.map(msg => {
    if (msg.role === 'assistant' && msg.tool_calls) {
      // When tool_calls exist, ensure reasoning_content field is present
      // (even if empty string to satisfy API requirements)
      if (!msg.reasoning_content) {
        msg.reasoning_content = '';
      }
      return msg;
    }
    // Remove reasoning_content when tool_calls are not present
    const { reasoning_content, ...safeMsg } = msg;
    return safeMsg;
  });

  // ReAct system prompt (always used)
  const systemContent = `You are an AI assistant that follows the ReAct (Reasoning + Acting) pattern.

When given a task, follow this pattern:

1. **Thought**: Think step-by-step about what you need to do. Explain your reasoning.
2. **Action**: If you need to use a tool to progress, make the tool call.
3. **Observation**: After receiving the tool result, analyze what you learned.
4. **Repeat**: Continue the Thought → Action → Observation cycle until you have enough information to provide a final answer.

**Important Guidelines:**
- Always show your reasoning in your thoughts
- Only use tools when necessary to gather information or perform actions
- After each observation, decide if you need more information or can provide the final answer
- Your final answer should directly address the user's question`;

  const response = await fetch(DEEPSEEK_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'deepseek-reasoner',
      messages: [
        {
          role: 'system',
          content: systemContent,
        },
        ...sanitizedMessages,
      ],
      tools: tools.map(tool => ({
        type: 'function',
        function: {
          name: tool.name,
          description: tool.description,
          parameters: tool.parameters,
        },
      })),
      stream,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`DeepSeek API error: ${response.status} - ${error}`);
  }

  return response;
}

// Backward compatible version of callDeepSeek
export async function callDeepSeekLegacy(
  messages: DeepSeekMessage[],
  tools: Tool[],
  stream: boolean = true
) {
  return callDeepSeek({ messages, tools, stream });
}
