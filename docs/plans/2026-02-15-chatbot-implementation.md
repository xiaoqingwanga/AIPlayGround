# Chatbot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Next.js chatbot with step-by-step thinking display, tool calling (file read/write, Python/JS execution), and DeepSeek API integration.

**Architecture:** Next.js App Router with API routes for backend logic, Server-Sent Events for streaming real-time thinking steps and tool calls to the frontend.

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS, DeepSeek API

---

## Task 1: Initialize Next.js Project

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `next.config.js`
- Create: `tailwind.config.ts`
- Create: `postcss.config.js`
- Create: `.gitignore`
- Create: `.env.local.example`

**Step 1: Initialize Next.js with TypeScript and Tailwind**

Run:
```bash
cd /Users/liamwang/Repos/AIPlayGround
npx create-next-app@latest . --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```

Expected: Next.js scaffolds the project.

**Step 2: Create .env.local.example**

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
TOOL_WORKING_DIRECTORY=/Users/liamwang/Repos/AIPlayGround
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: initialize Next.js project"
```

---

## Task 2: Create Type Definitions

**Files:**
- Create: `lib/types.ts`

**Step 1: Write type definitions**

```typescript
// Message types
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  thinkingSteps?: ThinkingStep[];
  toolCalls?: ToolCall[];
}

export interface ThinkingStep {
  id: string;
  type: 'task' | 'reasoning' | 'reflection' | 'tool_planning';
  content: string;
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
  | { type: 'thinking'; data: ThinkingStep }
  | { type: 'tool_call'; data: ToolCall }
  | { type: 'tool_result'; data: { toolCallId: string; result: any } }
  | { type: 'tool_error'; data: { toolCallId: string; error: string } }
  | { type: 'content'; data: string }
  | { type: 'done'; data: null };
```

**Step 2: Commit**

```bash
git add lib/types.ts
git commit -m "feat: add TypeScript type definitions"
```

---

## Task 3: Implement DeepSeek API Client

**Files:**
- Create: `lib/deepseek.ts`

**Step 1: Write the DeepSeek client**

```typescript
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
}

export async function callDeepSeek(
  messages: DeepSeekMessage[],
  tools: Tool[],
  stream: boolean = true
) {
  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    throw new Error('DEEPSEEK_API_KEY is not set');
  }

  const response = await fetch(DEEPSEEK_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant that shows your thinking process step by step. When planning, use clear sections: Task Decomposition, Reasoning, Self-Reflection, Tool Planning. You can use tools to read/write files and execute code.',
        },
        ...messages,
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
```

**Step 2: Commit**

```bash
git add lib/deepseek.ts
git commit -m "feat: add DeepSeek API client"
```

---

## Task 4: Implement SSE Stream Helpers

**Files:**
- Create: `lib/stream.ts`

**Step 1: Write stream utilities**

```typescript
import { StreamEvent } from '@/lib/types';

export function createEventStream() {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array>;

  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
    },
  });

  function send(event: StreamEvent) {
    const data = `data: ${JSON.stringify(event)}\n\n`;
    controller.enqueue(encoder.encode(data));
  }

  function close() {
    controller.close();
  }

  return { stream, send, close };
}

export async function parseSSEStream(reader: ReadableStreamDefaultReader<Uint8Array>) {
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch {
          // Skip malformed JSON
        }
      }
    }
  }
}
```

**Step 2: Commit**

```bash
git add lib/stream.ts
git commit -m "feat: add SSE stream helpers"
```

---

## Task 5: Implement File Tools

**Files:**
- Create: `app/api/tools/file.ts`

**Step 1: Write file tool implementations**

```typescript
import * as fs from 'fs/promises';
import * as path from 'path';
import { Tool } from '@/lib/types';

function getWorkingDir() {
  return process.env.TOOL_WORKING_DIRECTORY || process.cwd();
}

function resolveSafePath(filePath: string) {
  const workingDir = getWorkingDir();
  const resolved = path.resolve(workingDir, filePath);
  if (!resolved.startsWith(workingDir)) {
    throw new Error('Access denied: Path outside working directory');
  }
  return resolved;
}

export const fileReadTool: Tool = {
  name: 'file_read',
  description: 'Read a file from the filesystem',
  parameters: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'Path to the file (relative to working directory)',
      },
    },
    required: ['path'],
  },
  async execute({ path: filePath }) {
    const fullPath = resolveSafePath(filePath);
    const content = await fs.readFile(fullPath, 'utf-8');
    return { path: filePath, content };
  },
};

export const fileWriteTool: Tool = {
  name: 'file_write',
  description: 'Write content to a file',
  parameters: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'Path to the file (relative to working directory)',
      },
      content: {
        type: 'string',
        description: 'Content to write',
      },
    },
    required: ['path', 'content'],
  },
  async execute({ path: filePath, content }) {
    const fullPath = resolveSafePath(filePath);
    const dir = path.dirname(fullPath);
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(fullPath, content, 'utf-8');
    return { path: filePath, success: true };
  },
};
```

**Step 2: Commit**

```bash
git add app/api/tools/file.ts
git commit -m "feat: add file read/write tools"
```

---

## Task 6: Implement Code Execution Tools

**Files:**
- Create: `app/api/tools/exec.ts`

**Step 1: Write code execution tools**

```typescript
import { exec } from 'child_process';
import { promisify } from 'util';
import * as vm from 'vm';
import { Tool } from '@/lib/types';

const execAsync = promisify(exec);

export const pythonExecTool: Tool = {
  name: 'python_exec',
  description: 'Execute Python code (timeout: 30s)',
  parameters: {
    type: 'object',
    properties: {
      code: {
        type: 'string',
        description: 'Python code to execute',
      },
    },
    required: ['code'],
  },
  async execute({ code }) {
    try {
      const { stdout, stderr } = await execAsync(`python3 -c "${code.replace(/"/g, '\\"')}"`, {
        timeout: 30000,
      });
      return { stdout, stderr };
    } catch (error: any) {
      return {
        stdout: error.stdout || '',
        stderr: error.stderr || error.message,
      };
    }
  },
};

export const jsExecTool: Tool = {
  name: 'js_exec',
  description: 'Execute JavaScript code in a sandbox',
  parameters: {
    type: 'object',
    properties: {
      code: {
        type: 'string',
        description: 'JavaScript code to execute',
      },
    },
    required: ['code'],
  },
  async execute({ code }) {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        resolve({ error: 'Execution timeout (5s)' });
      }, 5000);

      try {
        const context = vm.createContext({});
        const result = vm.runInContext(code, context, { timeout: 5000 });
        clearTimeout(timeout);
        resolve({ result });
      } catch (error: any) {
        clearTimeout(timeout);
        resolve({ error: error.message });
      }
    });
  },
};
```

**Step 2: Commit**

```bash
git add app/api/tools/exec.ts
git commit -m "feat: add Python and JavaScript execution tools"
```

---

## Task 7: Create Tool Registry

**Files:**
- Create: `app/api/tools/index.ts`

**Step 1: Write tool registry**

```typescript
import { Tool } from '@/lib/types';
import { fileReadTool, fileWriteTool } from './file';
import { pythonExecTool, jsExecTool } from './exec';

export const tools: Tool[] = [
  fileReadTool,
  fileWriteTool,
  pythonExecTool,
  jsExecTool,
];

export function getTool(name: string): Tool | undefined {
  return tools.find(t => t.name === name);
}
```

**Step 2: Commit**

```bash
git add app/api/tools/index.ts
git commit -m "feat: add tool registry"
```

---

## Task 8: Implement Chat API Endpoint

**Files:**
- Create: `app/api/chat/route.ts`

**Step 1: Write the chat API route**

```typescript
import { NextRequest } from 'next/server';
import { callDeepSeek, DeepSeekMessage } from '@/lib/deepseek';
import { createEventStream } from '@/lib/stream';
import { tools, getTool } from '@/api/tools';
import { ThinkingStep, ToolCall } from '@/lib/types';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const { messages } = await req.json();
  const { stream, send, close } = createEventStream();

  // Run async chat logic
  (async () => {
    try {
      const deepseekMessages: DeepSeekMessage[] = messages.map((m: any) => ({
        role: m.role,
        content: m.content,
      }));

      let response = await callDeepSeek(deepseekMessages, tools, true);
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentContent = '';
      let toolCalls: Array<{ id: string; name: string; arguments: string }> = [];

      // First pass: stream response and collect tool calls
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') continue;

            try {
              const data = JSON.parse(dataStr);
              const choice = data.choices?.[0];
              const delta = choice?.delta;

              if (delta?.content) {
                currentContent += delta.content;
                send({ type: 'content', data: delta.content });
              }

              if (delta?.tool_calls) {
                for (const tc of delta.tool_calls) {
                  if (tc.index !== undefined && toolCalls[tc.index]) {
                    toolCalls[tc.index].arguments += tc.function?.arguments || '';
                  } else if (tc.function?.name) {
                    toolCalls.push({
                      id: tc.id || `tool-${Date.now()}`,
                      name: tc.function.name,
                      arguments: tc.function.arguments || '',
                    });
                  }
                }
              }
            } catch {
              // Skip parsing errors
            }
          }
        }
      }

      // Execute tool calls if any
      if (toolCalls.length > 0) {
        deepseekMessages.push({
          role: 'assistant',
          content: currentContent,
          tool_calls: toolCalls.map(tc => ({
            id: tc.id,
            type: 'function',
            function: {
              name: tc.name,
              arguments: tc.arguments,
            },
          })),
        });

        for (const tc of toolCalls) {
          const toolCallId = tc.id;
          const tool = getTool(tc.name);

          send({
            type: 'tool_call',
            data: {
              id: toolCallId,
              name: tc.name,
              parameters: JSON.parse(tc.arguments || '{}'),
              timestamp: Date.now(),
            } as ToolCall,
          });

          if (tool) {
            try {
              const params = JSON.parse(tc.arguments || '{}');
              const result = await tool.execute(params);
              send({
                type: 'tool_result',
                data: { toolCallId, result },
              });
              deepseekMessages.push({
                role: 'tool',
                tool_call_id: toolCallId,
                content: JSON.stringify(result),
              });
            } catch (error: any) {
              send({
                type: 'tool_error',
                data: { toolCallId, error: error.message },
              });
              deepseekMessages.push({
                role: 'tool',
                tool_call_id: toolCallId,
                content: `Error: ${error.message}`,
              });
            }
          }
        }

        // Get final response after tool calls
        const finalResponse = await callDeepSeek(deepseekMessages, tools, true);
        const finalReader = finalResponse.body!.getReader();
        let finalBuffer = '';

        while (true) {
          const { done, value } = await finalReader.read();
          if (done) break;

          finalBuffer += decoder.decode(value, { stream: true });
          const lines = finalBuffer.split('\n');
          finalBuffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              if (dataStr === '[DONE]') continue;
              try {
                const data = JSON.parse(dataStr);
                const content = data.choices?.[0]?.delta?.content;
                if (content) {
                  send({ type: 'content', data: content });
                }
              } catch {
                // Skip
              }
            }
          }
        }
      }

      send({ type: 'done', data: null });
    } catch (error: any) {
      send({ type: 'content', data: `Error: ${error.message}` });
      send({ type: 'done', data: null });
    } finally {
      close();
    }
  })();

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

**Step 2: Commit**

```bash
git add app/api/chat/route.ts
git commit -m "feat: implement chat API endpoint with streaming"
```

---

## Task 9: Create Main Chat UI

**Files:**
- Modify: `app/page.tsx`
- Create: `app/globals.css` (may already exist)
- Modify: `app/layout.tsx`

**Step 1: Write the main chat page**

```tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, StreamEvent, ThinkingStep, ToolCall } from '@/lib/types';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const assistantMessage: Message = {
      id: `msg-${Date.now() + 1}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      thinkingSteps: [],
      toolCalls: [],
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messages.concat(userMessage).map(m => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const event: StreamEvent = JSON.parse(line.slice(6));
            setMessages(prev => prev.map(m => {
              if (m.id !== assistantMessage.id) return m;

              switch (event.type) {
                case 'content':
                  return { ...m, content: m.content + event.data };
                case 'tool_call':
                  return { ...m, toolCalls: [...(m.toolCalls || []), event.data] };
                case 'tool_result':
                  return {
                    ...m,
                    toolCalls: m.toolCalls?.map(tc =>
                      tc.id === event.data.toolCallId
                        ? { ...tc, result: event.data.result }
                        : tc
                    ),
                  };
                case 'tool_error':
                  return {
                    ...m,
                    toolCalls: m.toolCalls?.map(tc =>
                      tc.id === event.data.toolCallId
                        ? { ...tc, error: event.data.error }
                        : tc
                    ),
                  };
                default:
                  return m;
              }
            }));
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100">
      <header className="border-b border-gray-800 p-4">
        <h1 className="text-xl font-bold">DeepSeek Chatbot</h1>
      </header>

      <main className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <h2 className="text-2xl font-semibold mb-2">Welcome!</h2>
            <p>Ask me anything. I can read/write files and execute code.</p>
          </div>
        )}

        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="text-gray-500">Thinking...</div>
        )}

        <div ref={messagesEndRef} />
      </main>

      <footer className="border-t border-gray-800 p-4">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={isLoading}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-2 rounded-lg font-medium"
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const [showTools, setShowTools] = useState(true);

  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-3xl ${message.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`px-4 py-2 rounded-lg ${
            message.role === 'user'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-100'
          }`}
        >
          {message.content.split('\n').map((line, i) => (
            <div key={i}>{line || <br />}</div>
          ))}
        </div>

        {message.role === 'assistant' && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 w-full">
            <button
              onClick={() => setShowTools(!showTools)}
              className="text-sm text-gray-500 hover:text-gray-300"
            >
              {showTools ? 'Hide' : 'Show'} tool calls ({message.toolCalls.length})
            </button>

            {showTools && (
              <div className="mt-2 space-y-2">
                {message.toolCalls.map(toolCall => (
                  <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  const [showResult, setShowResult] = useState(false);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
      <div className="flex justify-between items-start">
        <span className="font-mono text-sm text-yellow-400">
          {toolCall.name}
        </span>
        <span className="text-xs text-gray-500">
          {new Date(toolCall.timestamp).toLocaleTimeString()}
        </span>
      </div>
      <pre className="text-xs text-gray-400 mt-1 overflow-x-auto">
        {JSON.stringify(toolCall.parameters, null, 2)}
      </pre>

      {(toolCall.result || toolCall.error) && (
        <div className="mt-2">
          <button
            onClick={() => setShowResult(!showResult)}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            {showResult ? 'Hide' : 'Show'} {toolCall.error ? 'Error' : 'Result'}
          </button>
          {showResult && (
            <pre className={`text-xs mt-1 p-2 rounded overflow-x-auto ${
              toolCall.error ? 'bg-red-900/30 text-red-300' : 'bg-green-900/30 text-green-300'
            }`}>
              {toolCall.error || JSON.stringify(toolCall.result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Ensure layout.tsx is correct**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeepSeek Chatbot",
  description: "Chatbot with thinking steps and tool use",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

**Step 3: Commit**

```bash
git add app/page.tsx app/layout.tsx
git commit -m "feat: add main chat UI"
```

---

## Task 10: Create .env.local and Test

**Files:**
- Create: `.env.local` (from .env.local.example)

**Step 1: Copy .env.local.example to .env.local**

```bash
cp .env.local.example .env.local
```

**Step 2: Tell user to add their DeepSeek API key**

(Manual step: User needs to edit `.env.local` and add their DeepSeek API key)

**Step 3: Install dependencies and run dev server**

```bash
npm install
npm run dev
```

Expected: Server starts on http://localhost:3000

**Step 4: Commit .gitignore if needed**

```bash
echo ".env.local" >> .gitignore
git add .gitignore
git commit -m "chore: add .env.local to gitignore"
```

---

## Summary

This plan creates a complete chatbot with:
- Next.js 15 + TypeScript + Tailwind CSS
- DeepSeek API integration with streaming
- File read/write tools (sandboxed to working directory)
- Python and JavaScript code execution
- Real-time tool call display in the UI
