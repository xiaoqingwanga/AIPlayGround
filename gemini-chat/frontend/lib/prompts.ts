export const REACT_SYSTEM_PROMPT = `You are an AI assistant that follows the ReAct (Reasoning + Acting) pattern.

When given a task, follow this pattern:

1. **Thought**: Think step-by-step about what you need to do. Explain your reasoning.
2. **Action**: If you need to use a tool to progress, make the tool call.
3. **Observation**: After receiving the tool result, analyze what you learned.
4. **Repeat**: Continue the Thought → Action → Observation cycle until you have enough information to provide a final answer.

**Important Guidelines:**
- Always show your reasoning in your thoughts
- Only use tools when necessary to gather information or perform actions
- After each observation, decide if you need more information or can provide the final answer
- Your final answer should directly address the user's question

**Available Tools:**
- <file_read>: Read file contents
- <file_write>: Write to a file
- <python_exec>: Execute Python code
- <js_exec>: Execute JavaScript code
`;

export const REACT_FEW_SHOT_EXAMPLES = `
Example interaction:

User: What files are in the current directory?

Assistant:
Thought: The user wants to know what files are in the current directory. I need to use a tool to list the files. I'll use the python_exec tool to run a command that lists files.

Action: I will call the python_exec tool to list files in the current directory.

<function=python_exec>
{"code": "import os; print('\\n'.join(os.listdir('.')))"}
</function>

Observation: The result shows a list of files including README.md, package.json, src/, etc.

Thought: Now I have the file listing. I can provide a helpful response to the user about what files are present in the directory.

Final Answer: Here are the files in the current directory:
- README.md
- package.json
- src/ (directory)
- ... (etc)
`;

export const getReActSystemPrompt = (includeExamples: boolean = true): string => {
  let prompt = REACT_SYSTEM_PROMPT;
  if (includeExamples) {
    prompt += '\n\n' + REACT_FEW_SHOT_EXAMPLES;
  }
  return prompt;
};

// Helper function to format a ReAct thought for display
export function formatReActThought(content: string): { title: string; body: string } {
  const lines = content.split('\n').filter(l => l.trim());

  if (lines.length === 0) {
    return { title: 'Thought', body: content };
  }

  // Try to extract a title from the first line
  const firstLine = lines[0].trim();

  // Check for common prefixes to use as title
  const prefixMatch = firstLine.match(/^(Thought|Analysis|Planning|Reasoning|Decision):\s*(.+)/i);
  if (prefixMatch) {
    return {
      title: prefixMatch[1],
      body: prefixMatch[2] + '\n' + lines.slice(1).join('\n'),
    };
  }

  // If first line is short, use it as title
  if (firstLine.length < 60 && !firstLine.endsWith('.')) {
    return {
      title: firstLine,
      body: lines.slice(1).join('\n'),
    };
  }

  return { title: 'Thought', body: content };
}

// Helper function to extract tool intent from thought content
export function extractToolIntent(content: string): { tool: string | null; intent: string } {
  const toolPatterns: { [key: string]: RegExp[] } = {
    'file_read': [
      /read (?:the )?file/i,
      /file content/i,
      /contents? of/i,
      /open (?:the )?file/i,
    ],
    'file_write': [
      /write (?:to )?(?:the )?file/i,
      /save (?:to )?file/i,
      /create file/i,
      /update (?:the )?file/i,
    ],
    'python_exec': [
      /run python/i,
      /execute python/i,
      /python code/i,
      /use python/i,
    ],
    'js_exec': [
      /run javascript/i,
      /execute js/i,
      /javascript code/i,
      /node\.js/i,
      /use javascript/i,
    ],
  };

  for (const [tool, patterns] of Object.entries(toolPatterns)) {
    for (const pattern of patterns) {
      if (pattern.test(content)) {
        // Extract the intent (sentence containing the match)
        const match = content.match(new RegExp(`[^.!?]*${pattern.source}[^.!?]*[.!?]?`, 'i'));
        return { tool, intent: match?.[0] || content.slice(0, 100) };
      }
    }
  }

  return { tool: null, intent: content.slice(0, 100) };
}
