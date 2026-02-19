import { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  const { messages } = await req.json();

  // Convert frontend message format to backend format - use camelCase aliases
  const backendMessages = messages.map((m: any) => {
    const msg: any = {
      role: m.role,
      content: m.content || '',
    };
    if (m.toolCalls) {
      msg.toolCalls = m.toolCalls.map((tc: any) => ({
        id: tc.id,
        type: 'function',
        function: {
          name: tc.name,
          arguments: JSON.stringify(tc.parameters),
        },
      }));
      // Include reasoningContent for assistant messages with toolCalls
      msg.reasoningContent = m.reasoningContent || '';
    }
    if (m.toolCallId) {
      msg.toolCallId = m.toolCallId;
    }
    return msg;
  });

  try {
    // Call the backend
    const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: backendMessages,
        stream: true,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return new Response(
        `data: {"type":"content","data":"Error: Backend error - ${response.status}"}\n\ndata: {"type":"done","data":null}\n\n`,
        {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        }
      );
    }

    // Pass through the SSE stream from backend
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error: any) {
    return new Response(
      `data: {"type":"content","data":"Error: ${error.message}"}\n\ndata: {"type":"done","data":null}\n\n`,
      {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      }
    );
  }
}
