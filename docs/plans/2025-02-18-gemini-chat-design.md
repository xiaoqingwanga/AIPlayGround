# Gemini Chat Design Document

**Date**: 2025-02-18
**Status**: Approved

## 1. Overview

This document describes the reimplementation of the AI Playground backend in Python using FastAPI, alongside the existing Next.js frontend. Both frontend and backend are consolidated into a unified `gemini-chat` subfolder within the monorepo.

### 1.1 Goals

- Reimplement the Node.js/TypeScript backend in Python (FastAPI)
- Maintain full feature parity with existing implementation
- Add enhancements: structured logging, better error handling, health checks
- Consolidate frontend and backend in a single `gemini-chat` subfolder
- Provide simple development workflow for local development

### 1.2 Non-Goals

- Production deployment configuration (out of scope for this phase)
- Database persistence (maintain stateless design)
- Authentication/authorization (not in current scope)

## 2. Architecture

### 2.1 High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        gemini-chat/                              │
│  ┌──────────────────────┐      ┌──────────────────────────────┐  │
│  │    frontend/         │      │      backend/                │  │
│  │  (Next.js + React)   │◄────►│   (FastAPI + Python)         │  │
│  │                      │ HTTP │                              │  │
│  │  - Chat UI           │      │  - DeepSeek Integration      │  │
│  │  - Message streaming │      │  - Tool Registry             │  │
│  │  - ReAct visualization│     │  - ReAct Orchestrator        │  │
│  │                      │      │  - SSE Streaming             │  │
│  └──────────────────────┘      └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   DeepSeek API    │
                    │  (deepseek-reasoner│
                    │   with tool calls)│
                    └───────────────────┘
```

### 2.2 Communication Flow

1. **Frontend** sends POST request to `/api/v1/chat` with conversation history
2. **Backend** streams SSE events back to frontend:
   - `reasoning` - DeepSeek's reasoning content
   - `content` - Response content
   - `tool_call` - Tool execution request
   - `tool_result` - Tool execution result
   - `react_step` - ReAct orchestration step
   - `done` - Stream completion

### 2.3 Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| HTTP Client | httpx (async) |
| Validation | Pydantic v2 |
| Logging | structlog |
| Testing | pytest, pytest-asyncio |
| Server | uvicorn |
| Type Checking | mypy |
| Linting | ruff, black |
| Dependency Management | Poetry or pip |

## 3. Project Structure

```
gemini-chat/
├── Makefile                     # Common development commands
├── README.md                    # Project setup and development guide
├── .gitignore                   # Combined ignore rules
│
├── frontend/                    # Next.js frontend (moved from root)
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── .env.local.example
│   ├── .eslintrc.json
│   │
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── components/
│   │       ├── Chat.tsx
│   │       ├── MessageList.tsx
│   │       ├── ToolCall.tsx
│   │       └── ReActViewer.tsx
│   │
│   ├── lib/
│   │   ├── api.ts              # Updated to call Python backend
│   │   ├── types.ts
│   │   └── utils.ts
│   │
│   └── public/
│
└── backend/                     # Python FastAPI backend
    ├── pyproject.toml           # Poetry/pip dependencies
    ├── requirements.txt         # Alternative dep file
    ├── requirements-dev.txt     # Dev dependencies
    ├── .env.example             # Environment variables template
    ├── README.md                # Backend-specific docs
    ├── .gitignore               # Python gitignore
    │
    ├── src/
    │   └── gemini_chat_backend/  # Main package
    │       ├── __init__.py
    │       │
    │       ├── main.py           # FastAPI app entry point
    │       ├── config.py         # Pydantic settings
    │       │
    │       ├── api/
    │       │   ├── __init__.py
    │       │   ├── deps.py       # FastAPI dependencies
    │       │   ├── routes.py     # Route registration
    │       │   └── endpoints/
    │       │       ├── __init__.py
    │       │       ├── chat.py
    │       │       ├── health.py
    │       │       └── tools.py
    │       │
    │       ├── core/
    │       │   ├── __init__.py
    │       │   ├── deepseek.py
    │       │   ├── streaming.py
    │       │   └── react.py
    │       │
    │       ├── tools/
    │       │   ├── __init__.py
    │       │   ├── registry.py
    │       │   ├── base.py
    │       │   ├── file.py
    │       │   └── exec.py
    │       │
    │       ├── models/
    │       │   ├── __init__.py
    │       │   ├── chat.py
    │       │   ├── tool.py
    │       │   └── react.py
    │       │
    │       └── utils/
    │           ├── __init__.py
    │           ├── logging.py
    │           └── exceptions.py
    │
    ├── tests/
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── test_api/
    │   ├── test_core/
    │   └── test_tools/
    │
    └── scripts/
        ├── dev.sh
        ├── test.sh
        └── setup.sh
```

## 4. Updated Makefile

```makefile
# gemini-chat/Makefile

.PHONY: help install dev dev-backend dev-frontend test lint clean setup

# Default ports
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

help:
	@echo "Gemini Chat - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial setup (install all dependencies)"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start both backend and frontend"
	@echo "  make dev-backend    - Start only backend"
	@echo "  make dev-frontend   - Start only frontend"
	@echo ""
	@echo "Quality:"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run all linters"
	@echo "  make clean          - Clean up generated files"

# Setup
setup:
	@echo "Setting up Gemini Chat..."
	@echo ""
	@echo "Setting up backend..."
	cd backend && \
		python -m venv .venv && \
		. .venv/bin/activate && \
		pip install -r requirements.txt && \
		pip install -r requirements-dev.txt
	@echo ""
	@echo "Setting up frontend..."
	cd frontend && npm install
	@echo ""
	@echo "Setup complete! Copy backend/.env.example to backend/.env and add your API keys."

# Development

dev:
	@echo "Starting Gemini Chat (backend + frontend)..."
	@make -j 2 dev-backend dev-frontend

dev-backend:
	@echo "Starting backend on port $(BACKEND_PORT)..."
	cd backend && \
		. .venv/bin/activate && \
		uvicorn src.gemini_chat_backend.main:app --reload --port $(BACKEND_PORT)

dev-frontend:
	@echo "Starting frontend on port $(FRONTEND_PORT)..."
	cd frontend && npm run dev

# Testing
test:
	@echo "Running backend tests..."
	cd backend && \
		. .venv/bin/activate && \
		pytest -v
	@echo ""
	@echo "Running frontend tests..."
	cd frontend && npm test

# Linting
lint:
	@echo "Linting backend..."
	cd backend && \
		. .venv/bin/activate && \
		ruff check src/ && \
		black --check src/ && \
		mypy src/
	@echo ""
	@echo "Linting frontend..."
	cd frontend && npm run lint

# Cleanup
clean:
	@echo "Cleaning up..."
	cd backend && rm -rf .venv .pytest_cache .mypy_cache __pycache__ .coverage htmlcov
	cd frontend && rm -rf node_modules .next
	@echo "Cleanup complete!"
```

## 5. Key Configuration Files

### Backend `.env.example`

```bash
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_MODEL=deepseek-reasoner

# API Configuration
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Tool Configuration
TOOL_WORKING_DIRECTORY=.

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or text for development
```

### Frontend `.env.local.example`

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Development
NEXT_PUBLIC_APP_NAME=Gemini Chat
```

---

**This completes the revised design with both frontend and backend in the `gemini-chat` subfolder.**

Shall I proceed to:
1. Write the full design document to `docs/plans/2025-02-18-gemini-chat-design.md`
2. Invoke the `writing-plans` skill to create the implementation plan?