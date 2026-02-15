# Chatbot with Thinking Steps & Tool Use - Design Document

**Date:** 2026-02-15
**Author:** AIPlayGround Project

## Overview

A web-based chatbot that displays step-by-step thinking (task decomposition, self-reflection), can call tools, and uses the DeepSeek API.

## Architecture

**Stack:** Next.js 15 (App Router) + TypeScript + Tailwind CSS

**Data Flow:**
1. User sends message → Frontend
2. Frontend calls `/api/chat` with streaming response
3. Backend orchestrates: DeepSeek API ↔ Tool executor
4. Backend streams events via SSE
5. Frontend renders in real-time

## Components

### Frontend (React)
- Single page chat interface
- Expandable message sections: Thinking, Tool Calls, Final Response
- Streaming markdown rendering
- Tailwind CSS styling

### Backend (API Routes)
- `/api/chat` - Main chat endpoint (SSE stream)
- Tool registry in `/app/api/tools/`

## Tools (Backend Only)

1. `file_read` - Read local files
2. `file_write` - Write to local files
3. `python_exec` - Execute Python code (subprocess sandbox)
4. `js_exec` - Execute JavaScript code (vm module)

## Project Structure

```
/
├── app/
│   ├── page.tsx              # Main chat UI
│   ├── globals.css            # Tailwind imports
│   ├── layout.tsx             # Root layout
│   └── api/
│       ├── chat/
│       │   └── route.ts       # Main chat endpoint
│       └── tools/
│           ├── index.ts       # Tool registry
│           ├── file.ts        # file_read, file_write
│           └── exec.ts        # python_exec, js_exec
├── lib/
│   ├── deepseek.ts            # DeepSeek API client
│   ├── types.ts               # TypeScript interfaces
│   └── stream.ts              # SSE stream helpers
└── .env.local                 # DEEPSEEK_API_KEY
```
