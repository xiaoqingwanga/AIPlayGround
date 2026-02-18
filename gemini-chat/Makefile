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

setup:
	@echo "Setting up Gemini Chat..."
	@echo ""
	@echo "Setting up backend..."
	cd backend && \
		python3 -m venv .venv && \
		. .venv/bin/activate && \
		pip install -r requirements.txt && \
		pip install -r requirements-dev.txt
	@echo ""
	@echo "Setting up frontend..."
	cd frontend && npm install
	@echo ""
	@echo "Setup complete! Copy backend/.env.example to backend/.env and add your API keys."

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

test:
	@echo "Running backend tests..."
	cd backend && \
		. .venv/bin/activate && \
		pytest -v
	@echo ""
	@echo "Running frontend tests..."
	cd frontend && npm test

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

clean:
	@echo "Cleaning up..."
	cd backend && rm -rf .venv .pytest_cache .mypy_cache __pycache__ .coverage htmlcov
	cd frontend && rm -rf node_modules .next
	@echo "Cleanup complete!"
