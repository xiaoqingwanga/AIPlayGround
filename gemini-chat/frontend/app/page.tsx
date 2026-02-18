'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Message, StreamEvent, ToolCall, ThinkingStep, Conversation, ReActStep, ReActThought, ReActAction, ReActObservation } from '@/lib/types';

const STORAGE_KEY = 'deepseek-chat-conversations';
const SIDEBAR_WIDTH = 260;

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function getDefaultTitle(messages: Message[]): string {
  const firstUser = messages.find(m => m.role === 'user');
  if (!firstUser) return 'New Conversation';
  const title = firstUser.content.slice(0, 50);
  return title.length === 50 ? title + '...' : title;
}

function loadConversations(): Conversation[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

function saveConversations(conversations: Conversation[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const saved = loadConversations();
    setConversations(saved);
    if (saved.length > 0) {
      setCurrentConversationId(saved[0].id);
    } else {
      const newConv: Conversation = {
        id: generateId(),
        title: 'New Conversation',
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      setConversations([newConv]);
      setCurrentConversationId(newConv.id);
    }
  }, []);

  // Save to localStorage whenever conversations change
  useEffect(() => {
    if (conversations.length > 0) {
      saveConversations(conversations);
    }
  }, [conversations]);

  const currentConversation = conversations.find(c => c.id === currentConversationId);
  const messages = currentConversation?.messages || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const createNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: generateId(),
      title: 'New Conversation',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setConversations(prev => [newConv, ...prev]);
    setCurrentConversationId(newConv.id);
  }, []);

  const deleteConversation = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== id);
      if (filtered.length === 0) {
        const newConv: Conversation = {
          id: generateId(),
          title: 'New Conversation',
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        return [newConv];
      }
      if (currentConversationId === id) {
        setCurrentConversationId(filtered[0].id);
      }
      return filtered;
    });
  }, [currentConversationId]);

  const updateConversation = useCallback((id: string, updates: Partial<Conversation>) => {
    setConversations(prev => prev.map(c =>
      c.id === id ? { ...c, ...updates, updatedAt: Date.now() } : c
    ));
  }, []);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading || !currentConversationId) return;

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    const updatedMessages = [...messages, userMessage];
    updateConversation(currentConversationId, {
      messages: updatedMessages,
      title: getDefaultTitle(updatedMessages),
    });
    setInput('');
    setIsLoading(true);

    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      thinking: '',
      reactSteps: [],
      toolCalls: [],
    };

    updateConversation(currentConversationId, {
      messages: [...updatedMessages, assistantMessage],
    });

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: updatedMessages.map(m => ({
            role: m.role,
            content: m.content,
            // Include tool_calls for assistant messages
            tool_calls: m.toolCalls?.length ? m.toolCalls.map(tc => ({
              id: tc.id,
              type: 'function' as const,
              function: {
                name: tc.name,
                arguments: JSON.stringify(tc.parameters),
              },
            })) : undefined,
            // Include tool_call_id for tool messages
            tool_call_id: m.toolCallId,
            reasoningContent: m.reasoningContent,
          })),
        }),
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentContent = '';
      let currentThinking = '';
      let currentReasoning = '';
      let currentReactSteps: ReActStep[] = [];
      let currentToolCalls: ToolCall[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const event: StreamEvent = JSON.parse(line.slice(6));

            switch (event.type) {
              case 'reasoning':
                currentThinking += event.data;
                currentReasoning += event.data;
                break;
              case 'react_step':
                // Add ReAct step
                const reactStep = event.data as ReActStep;
                // Check if we already have this step
                const existingReactIndex = currentReactSteps.findIndex(s => s.id === reactStep.id);
                if (existingReactIndex >= 0) {
                  currentReactSteps[existingReactIndex] = reactStep;
                } else {
                  currentReactSteps = [...currentReactSteps, reactStep];
                }
                break;
              case 'content':
                currentContent += event.data;
                break;
              case 'tool_call':
                currentToolCalls = [...currentToolCalls, event.data];
                break;
              case 'tool_result':
                currentToolCalls = currentToolCalls.map(tc =>
                  tc.id === event.data.toolCallId
                    ? { ...tc, result: event.data.result }
                    : tc
                );
                // Add tool message to conversation history
                const toolMessage: Message = {
                  id: generateId(),
                  role: 'tool',
                  content: JSON.stringify(event.data.result),
                  toolCallId: event.data.toolCallId,
                  timestamp: Date.now(),
                };
                updatedMessages.push(toolMessage);
                break;
              case 'tool_error':
                currentToolCalls = currentToolCalls.map(tc =>
                  tc.id === event.data.toolCallId
                    ? { ...tc, error: event.data.error }
                    : tc
                );
                // Add tool error message to conversation history
                const toolErrorMessage: Message = {
                  id: generateId(),
                  role: 'tool',
                  content: `Error: ${event.data.error}`,
                  toolCallId: event.data.toolCallId,
                  timestamp: Date.now(),
                };
                updatedMessages.push(toolErrorMessage);
                break;
            }

            // Update the message with current state
            updateConversation(currentConversationId, {
              messages: [...updatedMessages, {
                ...assistantMessage,
                content: currentContent,
                thinking: currentThinking,
                reasoningContent: currentReasoning,
                reactSteps: currentReactSteps,
                toolCalls: currentToolCalls,
              }],
            });
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
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <aside
        className="flex flex-col border-r border-gray-800 bg-gray-950"
        style={{ width: SIDEBAR_WIDTH }}
      >
        <div className="p-4 border-b border-gray-800">
          <button
            onClick={createNewConversation}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-lg">+</span>
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map(conv => (
            <div
              key={conv.id}
              onClick={() => setCurrentConversationId(conv.id)}
              className={`group relative p-3 rounded-lg cursor-pointer transition-colors ${
                conv.id === currentConversationId
                  ? 'bg-gray-800'
                  : 'hover:bg-gray-800/50'
              }`}
            >
              <div className="pr-6">
                <div className="font-medium text-sm truncate">
                  {conv.title}
                </div>
                <div className="text-xs text-gray-500 mt-1 truncate">
                  {conv.messages.length > 0
                    ? conv.messages[conv.messages.length - 1].content.slice(0, 40)
                    : 'No messages yet'}
                </div>
              </div>
              <button
                onClick={(e) => deleteConversation(conv.id, e)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
                title="Delete conversation"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-gray-800 p-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">
            {currentConversation?.title || 'DeepSeek Chat'}
          </h1>

        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-20">
              <h2 className="text-2xl font-semibold mb-2">Welcome!</h2>
              <p>Ask me anything. I can read/write files and execute code.</p>
            </div>
          )}

          {messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
            <div className="text-gray-500 flex items-center gap-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              <span className="ml-2">Thinking...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <footer className="border-t border-gray-800 p-4">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={isLoading}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 disabled:opacity-50 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-2 rounded-lg font-medium transition-colors"
            >
              Send
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const [showTools, setShowTools] = useState(true);
  const [showReAct, setShowReAct] = useState(true);

  const hasReactSteps = message.reactSteps && message.reactSteps.length > 0;

  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-3xl ${message.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>

        {/* ReAct Steps Section */}
        {message.role === 'assistant' && hasReactSteps && (
          <div className="mt-2 w-full mb-2">
            <button
              onClick={() => setShowReAct(!showReAct)}
              className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              <span>🔄</span>
              {showReAct ? 'Hide' : 'Show'} ReAct Pattern
              {` (${message.reactSteps?.length} steps)`}
            </button>

            {showReAct && (
              <ReActDisplay steps={message.reactSteps || []} />
            )}
          </div>
        )}

        {/* Main Content */}
        {message.content && (
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
        )}

        {/* Tool Calls Section */}
        {message.role === 'assistant' && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 w-full">
            <button
              onClick={() => setShowTools(!showTools)}
              className="text-sm text-gray-500 hover:text-gray-300 flex items-center gap-1"
            >
              <span>🔧</span>
              {showTools ? 'Hide' : 'Show'} Tool Calls ({message.toolCalls.length})
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

// Helper function to group ReAct steps into cycles
function groupReActStepsIntoCycles(steps: ReActStep[]): Array<{
  thought: ReActThought | null;
  action: ReActAction | null;
  observation: ReActObservation | null;
}> {
  const cycles: Array<{
    thought: ReActThought | null;
    action: ReActAction | null;
    observation: ReActObservation | null;
  }> = [];

  let currentCycle: {
    thought: ReActThought | null;
    action: ReActAction | null;
    observation: ReActObservation | null;
  } = { thought: null, action: null, observation: null };

  for (const step of steps) {
    if (step.type === 'thought') {
      // Start a new cycle when we see a thought
      if (currentCycle.thought || currentCycle.action || currentCycle.observation) {
        cycles.push(currentCycle);
      }
      currentCycle = { thought: step, action: null, observation: null };
    } else if (step.type === 'action') {
      currentCycle.action = step;
    } else if (step.type === 'observation') {
      currentCycle.observation = step;
      // Complete the cycle
      cycles.push(currentCycle);
      currentCycle = { thought: null, action: null, observation: null };
    }
  }

  // Don't forget the last incomplete cycle
  if (currentCycle.thought || currentCycle.action || currentCycle.observation) {
    cycles.push(currentCycle);
  }

  return cycles;
}

function ReActDisplay({ steps }: { steps: ReActStep[] }) {
  const cycles = groupReActStepsIntoCycles(steps);

  if (cycles.length === 0) return null;

  // Check if all cycles are just standalone thoughts
  const allAreThoughtsOnly = cycles.every(c => c.thought && !c.action && !c.observation);

  return (
    <div className="mt-4 space-y-4">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
        {allAreThoughtsOnly ? 'Reasoning' : `ReAct Pattern (${cycles.length} cycle${cycles.length > 1 ? 's' : ''})`}
      </div>

      {cycles.map((cycle, cycleIdx) => {
        const isStandaloneThought = cycle.thought && !cycle.action && !cycle.observation;

        if (isStandaloneThought) {
          return (
            <div key={cycleIdx} className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
              <div className="text-xs text-blue-400 uppercase tracking-wide mb-2 font-semibold">
                🤔 Reasoning
              </div>
              {cycle.thought!.title && (
                <div className="text-sm font-medium text-blue-300 mb-2">{cycle.thought!.title}</div>
              )}
              <div className="text-sm text-gray-200 whitespace-pre-wrap">{cycle.thought!.content}</div>
            </div>
          );
        }

        return (
          <div key={cycleIdx} className="border border-gray-700 rounded-lg p-4 bg-gray-900/50">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-mono text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                Cycle {cycleIdx + 1}
              </span>
            </div>

            {/* Thought */}
            {cycle.thought && (
              <div className="mb-4 pl-4 border-l-2 border-blue-500">
                <div className="text-xs text-blue-400 uppercase tracking-wide mb-1 font-semibold">Thought</div>
                {cycle.thought.title && (
                  <div className="text-sm font-medium text-blue-300 mb-1">{cycle.thought.title}</div>
                )}
                <div className="text-sm text-gray-200 whitespace-pre-wrap">{cycle.thought.content}</div>
              </div>
            )}

            {/* Action */}
            {cycle.action && (
              <div className="mb-4 pl-4 border-l-2 border-yellow-500">
                <div className="text-xs text-yellow-400 uppercase tracking-wide mb-1 font-semibold">Action</div>
                <div className="text-sm text-gray-200">
                  <span className="font-mono text-yellow-300">{cycle.action.toolCall.name}</span>
                  <pre className="mt-1 text-xs bg-gray-800 p-2 rounded overflow-x-auto">
                    {JSON.stringify(cycle.action.toolCall.parameters, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Observation */}
            {cycle.observation && (
              <div className="pl-4 border-l-2 border-green-500">
                <div className="text-xs text-green-400 uppercase tracking-wide mb-1 font-semibold">Observation</div>
                <div className="text-sm text-gray-200">
                  {cycle.observation.error ? (
                    <span className="text-red-400">Error: {cycle.observation.error}</span>
                  ) : (
                    <pre className="text-xs bg-gray-800 p-2 rounded overflow-x-auto">
                      {JSON.stringify(cycle.observation.result, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
