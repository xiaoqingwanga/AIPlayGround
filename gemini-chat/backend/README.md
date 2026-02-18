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
