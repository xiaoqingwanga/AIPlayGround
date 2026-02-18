# Gemini Chat

A unified AI chat application with a FastAPI Python backend and Next.js React frontend.

## Quick Start

```bash
# 1. Setup (one-time)
make setup

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your DEEPSEEK_API_KEY

# 3. Start development (runs both frontend and backend)
make dev
```

The frontend will be available at http://localhost:3000 and the backend at http://localhost:8000.

## Development Commands

```bash
# Start only backend
make dev-backend

# Start only frontend
make dev-frontend

# Run all tests
make test

# Run all linters
make lint

# Clean up generated files
make clean
```

## Project Structure

```
gemini-chat/
├── Makefile                 # Development commands
├── frontend/                # Next.js frontend
│   ├── app/                 # Next.js app router
│   ├── components/          # React components
│   ├── lib/                 # Utilities and API client
│   └── package.json
└── backend/                 # Python FastAPI backend
    ├── src/                 # Source code
    ├── tests/               # Test suite
    └── requirements.txt
```

## Documentation

- [Backend README](backend/README.md) - Backend-specific setup and development
- [API Documentation](http://localhost:8000/docs) - Auto-generated OpenAPI docs (when running)

## License

MIT
