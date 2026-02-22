# AIPlayGround

A monorepo for implementing various "AI toys" — experimental AI applications designed for learning, exploration, and pushing the boundaries of what's possible with AI APIs.

## AI Toys

### gemini-chat

A Gemini-like chatbot with a FastAPI Python backend and Next.js React frontend, implementing the ReAct (Reasoning + Acting) pattern for tool execution.

**Features:**
- Streaming responses with real-time thinking visualization
- ReAct pattern: the model reasons before taking actions
- Tool execution capabilities with visual feedback
- Built with DeepSeek API (deepseek-reasoner model)

**Quick Start:**
```bash
cd gemini-chat
make setup
cp backend/.env.example backend/.env
# Edit backend/.env and add your DEEPSEEK_API_KEY
make dev
```

See [gemini-chat/README.md](gemini-chat/README.md) for detailed setup and development instructions.

## Project Structure

```
AIPlayGround/
├── gemini-chat/          # Main AI toy: Gemini-like chatbot
│   ├── Makefile          # Development commands
│   ├── frontend/         # Next.js 16 + React 19 frontend
│   └── backend/          # Python FastAPI backend
└── docs/                 # Documentation and plans
```

## Development Tools

The `gemini-chat/` project provides a Makefile with convenient commands:

```bash
make setup          # Initial setup (install all dependencies)
make dev            # Start both backend and frontend
make dev-backend    # Start only backend (port 8000)
make dev-frontend   # Start only frontend (port 3000)
make test           # Run all tests
make lint           # Run all linters
make clean          # Clean up generated files
```

## Technology Stack

**Backend (Python):**
- FastAPI — Modern, fast web framework
- Pydantic — Data validation using Python type annotations
- structlog — Structured logging
- uvicorn — ASGI server
- httpx — Async HTTP client

**Frontend (TypeScript):**
- Next.js 16 — React framework
- React 19 — UI library
- Tailwind CSS 4 — Utility-first CSS framework
- TypeScript — Type-safe JavaScript

**AI:**
- DeepSeek API — Using the deepseek-reasoner model for reasoning and tool execution

## License

MIT
