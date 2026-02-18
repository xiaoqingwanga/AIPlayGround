import { NextRequest } from 'next/server';
import { callDeepSeek, DeepSeekMessage, DeepSeekDelta } from '@/lib/deepseek';
import { createEventStream } from '@/lib/stream';
import { tools, getTool } from '../tools';
import { ToolCall, ReActStep, ReActThought, ReActAction, ReActObservation } from '@/lib/types';
import { ReActOrchestrator } from '@/lib/react-orchestrator';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function validateConversationHistory(messages: any[]): any[] {
  // Create a copy to avoid mutating original
  const validatedMessages = [...messages];

  // Track tool calls and responses
  const pendingToolCalls = new Map<string, boolean>();

  for (let i = 0; i < validatedMessages.length; i++) {
    const msg = validatedMessages[i];

    if (msg.role === 'assistant' && msg.tool_calls) {
      // New tool calls - mark them as pending
      for (const tc of msg.tool_calls) {
        if (tc.id) {
          pendingToolCalls.set(tc.id, false); // false = not responded to yet
        }
      }
    } else if (msg.role === 'tool' && msg.tool_call_id) {
      // Tool response - mark as responded
      pendingToolCalls.set(msg.tool_call_id, true);
    }
  }

  // Check if any tool calls are pending without responses
  const missingResponses = Array.from(pendingToolCalls.entries())
    .filter(([_, responded]) => !responded)
    .map(([id]) => id);

  if (missingResponses.length > 0) {
    console.warn(`Warning: Found ${missingResponses.length} tool call(s) without responses:`, missingResponses);
    // Optionally, we could add placeholder error responses here
    // For now, just log warning
  }

  return validatedMessages;
}

export async function POST(req: NextRequest) {
  const { messages } = await req.json();
  const { stream, send, close } = createEventStream();

  // Run async chat logic
  (async () => {
    try {
      // Validate conversation history first
      const validatedMessages = validateConversationHistory(messages);
      const deepseekMessages: DeepSeekMessage[] = validatedMessages.map((m: any) => {
        // Important: Include reasoning_content ONLY if tool_calls are present (DeepSeek requires this!)
        const msg: DeepSeekMessage = {
          role: m.role,
          content: m.content || '', // Ensure content has default value
        };
        if (m.tool_calls) {
          msg.tool_calls = m.tool_calls;
          // For assistant messages with tool_calls, we MUST include reasoning_content
          // (even if empty to satisfy DeepSeek API requirements)
          msg.reasoning_content = m.reasoningContent || '';
        }
        if (m.tool_call_id) {
          msg.tool_call_id = m.tool_call_id;
        }
        return msg;
      });

      // Create ReAct orchestrator (always enabled)
      const reactOrchestrator = new ReActOrchestrator(
        (step: ReActStep) => {
          send({ type: 'react_step', data: step });
        },
        10 // max iterations
      );

      let response = await callDeepSeek({
        messages: deepseekMessages,
        tools,
        stream: true,
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentContent = '';
      let currentReasoning = '';
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
              const delta = choice?.delta as DeepSeekDelta;

              if (delta?.reasoning_content) {
                currentReasoning += delta.reasoning_content;
                send({ type: 'reasoning', data: delta.reasoning_content });

                // Record thoughts: always update in-place, only create new thought when needed
                if (reactOrchestrator) {
                  const steps = reactOrchestrator.getSteps();
                  const lastStep = steps[steps.length - 1] as ReActThought | undefined;

                  if (lastStep?.type === 'thought') {
                    // Update existing thought in-place
                    lastStep.content = currentReasoning;
                    send({ type: 'react_step', data: lastStep });
                  } else {
                    // No existing thought in current cycle - create new one
                    reactOrchestrator.recordThought(currentReasoning, undefined, 'response');
                  }
                }
              }

              if (delta?.content) {
                currentContent += delta.content;
                send({ type: 'content', data: delta.content });
              }

              if (delta?.tool_calls) {
                for (const tc of delta.tool_calls) {
                  if (tc.index !== undefined) {
                    // Ensure array has space for this index
                    if (!toolCalls[tc.index]) {
                      // Generate stable ID once per index
                      const stableId = `tool-${Date.now()}-${tc.index}`;
                      toolCalls[tc.index] = {
                        id: tc.id || stableId,
                        name: tc.function?.name || '',
                        arguments: tc.function?.arguments || '',
                      };
                    } else {
                      // Update with API-provided ID if available
                      if (tc.id && !toolCalls[tc.index].id.startsWith('tool-')) {
                        toolCalls[tc.index].id = tc.id;
                      }
                      // Update name if not set yet
                      if (!toolCalls[tc.index].name && tc.function?.name) {
                        toolCalls[tc.index].name = tc.function.name;
                      }
                      // Accumulate arguments
                      toolCalls[tc.index].arguments += tc.function?.arguments || '';
                    }
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
          reasoning_content: currentReasoning,
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

          // Create the tool call object
          let parameters = {};
          try {
            parameters = JSON.parse(tc.arguments || '{}');
          } catch {
            parameters = {};
          }
          const toolCall: ToolCall = {
            id: toolCallId,
            name: tc.name,
            parameters,
            timestamp: Date.now(),
          };

          send({
            type: 'tool_call',
            data: toolCall,
          });

          // Record as action
          if (reactOrchestrator) {
            await reactOrchestrator.recordAction(toolCall);
          }

          if (tool) {
            try {
              let params = {};
              try {
                params = JSON.parse(tc.arguments || '{}');
              } catch {
                params = {};
              }
              const result = await tool.execute(params);
              send({
                type: 'tool_result',
                data: { toolCallId, result },
              });

              // Record as observation
              if (reactOrchestrator) {
                await reactOrchestrator.recordObservation(toolCallId, result);
              }

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

              // Record as observation with error
              if (reactOrchestrator) {
                await reactOrchestrator.recordObservation(toolCallId, undefined, error.message);
              }

              deepseekMessages.push({
                role: 'tool',
                tool_call_id: toolCallId,
                content: `Error: ${error.message}`,
              });
            }
          } else {
            // Tool not found - still send tool message with error
            const errorMessage = `Error: Tool '${tc.name}' not found`;
            send({
              type: 'tool_error',
              data: { toolCallId, error: errorMessage },
            });

            // Record as observation with error
            if (reactOrchestrator) {
              await reactOrchestrator.recordObservation(toolCallId, undefined, errorMessage);
            }

            deepseekMessages.push({
              role: 'tool',
              tool_call_id: toolCallId,
              content: errorMessage,
            });
          }
        }

        // Get final response after tool calls
        const finalResponse = await callDeepSeek({
          messages: deepseekMessages,
          tools,
          stream: true,
        });
        const finalReader = finalResponse.body!.getReader();
        let finalBuffer = '';
        let finalReasoning = '';

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
                const delta = data.choices?.[0]?.delta as DeepSeekDelta;
                if (delta?.reasoning_content) {
                  finalReasoning += delta.reasoning_content;
                  send({ type: 'reasoning', data: delta.reasoning_content });

                  // Record final reasoning thoughts: always update in-place
                  if (reactOrchestrator) {
                    const steps = reactOrchestrator.getSteps();
                    const lastStep = steps[steps.length - 1] as ReActThought | undefined;

                    if (lastStep?.type === 'thought') {
                      // Update existing thought in-place
                      lastStep.content = finalReasoning;
                      send({ type: 'react_step', data: lastStep });
                    } else {
                      // No existing thought in current cycle - create new one
                      reactOrchestrator.recordThought(finalReasoning, undefined, 'response');
                    }
                  }
                }
                if (delta?.content) {
                  send({ type: 'content', data: delta.content });
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
