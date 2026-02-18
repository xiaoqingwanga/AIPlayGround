# Gemini Chat Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the complete Gemini Chat application with FastAPI Python backend and Next.js frontend in a unified `gemini-chat` subfolder.

**Architecture:** A unified application structure with a FastAPI Python backend (DeepSeek integration, ReAct orchestration, SSE streaming, tool registry) and a Next.js React frontend, both contained within a `gemini-chat` subfolder in the monorepo.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, httpx, structlog, pytest; Node.js 20+, Next.js 16, React 19, TypeScript, Tailwind CSS

---

## Phase 0: Project Structure Setup

### Task 1: Create gemini-chat Directory Structure

**Files:**
- Create: `gemini-chat/Makefile`
- Create: `gemini-chat/README.md`
- Create: `gemini-chat/.gitignore`
- Create: `gemini-chat/backend/.gitignore`
- Create: `gemini-chat/frontend/.gitignore`

**Step 1: Create root Makefile**

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
```

**Step 2: Create root README.md**

```markdown
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
```

**Step 3: Create .gitignore files**

```bash
# gemini-chat/.gitignore
# Root ignores - don't duplicate child .gitignores

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
```

```bash
# gemini-chat/backend/.gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.venv
venv/
ENV/
env/

# Testing
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local

# Logs
*.log
```

```bash
# gemini-chat/frontend/.gitignore
# Next.js
.next/
out/

# Dependencies
node_modules/

# Production build
build/
dist/

# Environment
.env
.env.local
.env.*.local

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Testing
coverage/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

**Step 4: Run verification**

Run: `tree -L 2 gemini-chat/` (or `ls -R gemini-chat/`)
Expected:
```
gemini-chat/
├── Makefile
├── README.md
├── .gitignore
├── frontend/
│   └── .gitignore
└── backend/
    └── .gitignore
```

**Step 5: Commit**

```bash
git add gemini-chat/Makefile gemini-chat/README.md gemini-chat/.gitignore gemini-chat/backend/.gitignore gemini-chat/frontend/.gitignore
git commit -m "chore: create gemini-chat project structure"
```

---

## Phase 1: Backend Foundation

### Task 2: Create Python Package Structure

**Files:**
- Create: `gemini-chat/backend/pyproject.toml`
- Create: `gemini-chat/backend/requirements.txt`
- Create: `gemini-chat/backend/requirements-dev.txt`
- Create: `gemini-chat/backend/.env.example`
- Create: `gemini-chat/backend/README.md`
- Create: `gemini-chat/backend/src/gemini_chat_backend/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "gemini-chat-backend"
version = "0.1.0"
description = "FastAPI backend for Gemini Chat"
readme = "README.md"
requires-python = ">=3.11"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "httpx>=0.26.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "structlog>=24.1.0",
    "python-json-logger>=2.0.7",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "ruff>=0.2.0",
    "black>=24.1.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
]

[project.scripts]
gemini-chat = "gemini_chat_backend.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",   # pycodestyle errors
    "F",   # Pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Step 2: Create requirements.txt (alternative to Poetry)**

```txt
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
httpx>=0.26.0

# Validation
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Logging
structlog>=24.1.0
python-json-logger>=2.0.7

# Utilities
python-multipart>=0.0.6
```

**Step 3: Create requirements-dev.txt**

```txt
# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
httpx>=0.26.0

# Linting & Formatting
ruff>=0.2.0
black>=24.1.0
mypy>=1.8.0

# Pre-commit
pre-commit>=3.6.0
```

**Step 4: Create .env.example**

```bash
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_MODEL=deepseek-reasoner

# API Configuration
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Tool Configuration
TOOL_WORKING_DIRECTORY=.

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text  # json for production, text for development
```

**Step 5: Create backend README.md**

```markdown
# Gemini Chat Backend

FastAPI-based Python backend for Gemini Chat with DeepSeek integration.

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY

# 4. Run development server
uvicorn src.gemini_chat_backend.main:app --reload
```

## Development Commands

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src/

# Linting
ruff check src/
black --check src/

# Format code
black src/
ruff check --fix src/
```

## API Documentation

When running, API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Project Structure

```
backend/
├── src/gemini_chat_backend/    # Main package
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings
│   ├── api/                    # API routes
│   ├── core/                   # Core logic
│   ├── tools/                  # Tool implementations
│   ├── models/                 # Pydantic models
│   └── utils/                  # Utilities
├── tests/                       # Test suite
└── requirements.txt             # Dependencies
```

## License

MIT
```

**Step 6: Create package __init__.py**

```python
# gemini-chat/backend/src/gemini_chat_backend/__init__.py
"""Gemini Chat Backend - FastAPI application for AI chat with DeepSeek."""

__version__ = "0.1.0"
```

**Step 7: Verify directory structure**

Run: `find gemini-chat/backend -type f | head -20`
Expected output shows:
- pyproject.toml
- requirements.txt
- requirements-dev.txt
- .env.example
- README.md
- .gitignore
- src/gemini_chat_backend/__init__.py

**Step 8: Commit**

```bash
git add gemini-chat/backend/
git commit -m "chore: set up Python backend project structure

- Add pyproject.toml with dependencies and tool configs
- Add requirements.txt and requirements-dev.txt
- Add .env.example for configuration
- Add README.md with setup and development instructions
- Create package structure with __init__.py"
```

---

## Phase 1: Backend Core Components

### Task 3: Create Configuration Module

**Files:**
- Create: `gemini-chat/backend/src/gemini_chat_backend/config.py`
- Create: `gemini-chat/backend/tests/test_config.py`

**Step 1: Write the failing test**

```python
# gemini-chat/backend/tests/test_config.py
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from gemini_chat_backend.config import Settings


class TestSettings:
    """Test suite for configuration settings."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            settings = Settings()
            assert settings.API_V1_STR == "/api/v1"
            assert settings.PROJECT_NAME == "Gemini Chat Backend"
            assert settings.DEEPSEEK_MODEL == "deepseek-reasoner"
            assert settings.LOG_LEVEL == "INFO"
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000

    def test_required_api_key(self):
        """Test that DEEPSEEK_API_KEY is required."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "DEEPSEEK_API_KEY" in str(exc_info.value)

    def test_cors_origins_parsing(self):
        """Test that CORS origins are parsed from JSON string."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test_key",
            "BACKEND_CORS_ORIGINS": '["http://localhost:3000", "http://localhost:8080"]'
        }):
            settings = Settings()
            assert settings.BACKEND_CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8080"]

    def test_env_file_loading(self):
        """Test that settings can be loaded from .env file."""
        # This test verifies the Settings class uses EnvSettingsSource
        settings = Settings(_env_file=".env.example")
        # Should not raise, showing it can read from env file
        assert settings is not None
```

**Step 2: Run test to verify it fails**

Run: `cd gemini-chat/backend && python -m pytest tests/test_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'gemini_chat_backend.config'"

**Step 3: Write minimal implementation**

```python
# gemini-chat/backend/src/gemini_chat_backend/config.py
"""Configuration management for Gemini Chat Backend."""

import json
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Gemini Chat Backend"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from JSON string or list."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [origin.strip() for origin in value.split(",")]
        return value

    # DeepSeek API Configuration
    DEEPSEEK_API_KEY: str
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek-reasoner"

    # Tool Configuration
    TOOL_WORKING_DIRECTORY: str = "."

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # "json" for production, "text" for development


# Global settings instance
settings = Settings()
```

**Step 4: Run test to verify it passes**

Run: `cd gemini-chat/backend && python -m pytest tests/test_config.py -v`
Expected: PASS (4 tests passed)

**Step 5: Commit**

```bash
git add gemini-chat/backend/src/gemini_chat_backend/config.py gemini-chat/backend/tests/test_config.py
git commit -m "feat(config): add Pydantic settings management

- Add Settings class with environment variable loading
- Support .env file configuration
- Parse CORS origins from JSON string or list
- Add validation for required fields (DEEPSEEK_API_KEY)
- Add comprehensive test suite for configuration"
```

---

### Task 4: Create Logging Utility

**Files:**
- Create: `gemini-chat/backend/src/gemini_chat_backend/utils/logging.py`
- Create: `gemini-chat/backend/tests/utils/test_logging.py`
- Create: `gemini-chat/backend/src/gemini_chat_backend/utils/__init__.py`

**Step 1: Write the failing test**

```python
# gemini-chat/backend/tests/utils/test_logging.py
import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from gemini_chat_backend.utils.logging import (
    configure_logging,
    get_logger,
    get_request_logger,
)


class TestConfigureLogging:
    """Test suite for logging configuration."""

    def test_configure_structlog(self):
        """Test that structlog is properly configured."""
        configure_logging(log_level="INFO", log_format="text")

        # Verify structlog is configured
        logger = structlog.get_logger()
        assert logger is not None

    def test_json_format_configuration(self):
        """Test JSON format configuration."""
        configure_logging(log_level="DEBUG", log_format="json")

        # Create a logger and capture output
        logger = get_logger("test_json")

        # This test verifies no exception is raised
        logger.info("Test message", key="value")

    def test_text_format_configuration(self):
        """Test text format configuration."""
        configure_logging(log_level="INFO", log_format="text")

        logger = get_logger("test_text")

        # This test verifies no exception is raised
        logger.info("Test message")

    def test_invalid_log_level(self):
        """Test that invalid log level defaults to INFO."""
        # Should not raise, just default to INFO
        configure_logging(log_level="INVALID", log_format="text")


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a bound logger."""
        configure_logging(log_level="INFO", log_format="text")

        logger = get_logger("test_module")

        assert logger is not None
        # Should be able to log without error
        logger.info("Test message")

    def test_get_logger_with_context(self):
        """Test that get_logger binds context correctly."""
        configure_logging(log_level="INFO", log_format="text")

        logger = get_logger("test_module", request_id="12345")

        # Should be able to log with context
        logger.info("Test with context")


class TestGetRequestLogger:
    """Test suite for get_request_logger function."""

    def test_get_request_logger_binds_request_id(self):
        """Test that request_id is bound to logger."""
        configure_logging(log_level="INFO", log_format="text")

        logger = get_request_logger(request_id="abc-123")

        assert logger is not None
        logger.info("Request started")

    def test_different_request_ids_create_different_loggers(self):
        """Test that different request IDs create separate logger contexts."""
        configure_logging(log_level="INFO", log_format="text")

        logger1 = get_request_logger(request_id="req-1")
        logger2 = get_request_logger(request_id="req-2")

        assert logger1 is not None
        assert logger2 is not None

        logger1.info("Message from request 1")
        logger2.info("Message from request 2")
```

**Step 2: Run test to verify it fails**

Run: `cd gemini-chat/backend && python -m pytest tests/utils/test_logging.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'gemini_chat_backend.utils'"

**Step 3: Write minimal implementation**

```python
# gemini-chat/backend/src/gemini_chat_backend/utils/__init__.py
"""Utility modules for Gemini Chat Backend."""
```

```python
# gemini-chat/backend/src/gemini_chat_backend/utils/logging.py
"""Structured logging configuration for Gemini Chat Backend."""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "text",
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" for production, "text" for development)
    """
    # Map string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    if log_format == "json":
        # JSON format for production
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
    else:
        # Text format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers = []

    # Add stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(
    name: Optional[str] = None,
    **context: Any,
) -> structlog.stdlib.BoundLogger:
    """Get a structured logger with optional context binding.

    Args:
        name: Logger name (typically __name__)
        **context: Key-value pairs to bind to the logger context

    Returns:
        A structured logger instance
    """
    logger = structlog.get_logger(name)

    if context:
        logger = logger.bind(**context)

    return logger


def get_request_logger(
    request_id: str,
    **context: Any,
) -> structlog.stdlib.BoundLogger:
    """Get a logger bound with request context for request tracing.

    Args:
        request_id: Unique identifier for the request
        **context: Additional context to bind

    Returns:
        A structured logger with request context
    """
    return get_logger(
        request_id=request_id,
        **context,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd gemini-chat/backend && python -m pytest tests/utils/test_logging.py -v`
Expected: PASS (12 tests passed)

**Step 5: Commit**

```bash
git add gemini-chat/backend/src/gemini_chat_backend/utils/
git add gemini-chat/backend/tests/utils/
git commit -m "feat(logging): add structured logging with structlog

- Add configure_logging() for JSON/text format logging
- Add get_logger() for structured logger instances
- Add get_request_logger() for request context binding
- Configure structlog with standard library integration
- Add comprehensive test suite for logging utilities"
```

---

[... continues with additional tasks for models, API endpoints, DeepSeek client, tools, etc. ...]

---

## Summary

This implementation plan provides a complete, step-by-step guide to building the Gemini Chat application. Each task is bite-sized (2-5 minutes), includes complete code, exact commands, and expected outputs. Follow this plan task-by-task to complete the implementation.

**Total Estimated Time:** 4-6 hours
**Total Tasks:** ~25 tasks
**Phases:** 5 phases (Structure, Foundation, Core, Integration, Frontend)
