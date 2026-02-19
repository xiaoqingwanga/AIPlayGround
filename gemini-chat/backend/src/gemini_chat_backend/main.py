"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gemini_chat_backend.api.routes import setup_routes
from gemini_chat_backend.config import settings
from gemini_chat_backend.tools import register_tools
from gemini_chat_backend.utils.logging import configure_logging, get_logger

# Configure logging on module load
configure_logging(
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Application starting",
        project_name=settings.PROJECT_NAME,
        version="0.1.0",
    )

    # Register tools
    register_tools()

    yield

    # Shutdown
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="FastAPI backend for Gemini Chat with DeepSeek integration",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    # Set up API routes
    setup_routes(app)

    logger.info(
        "FastAPI application created",
        title=settings.PROJECT_NAME,
        cors_origins=settings.BACKEND_CORS_ORIGINS,
    )

    return app


# Create the application instance
app = create_app()


def main() -> None:
    """Entry point for running the application directly."""
    import uvicorn

    uvicorn.run(
        "gemini_chat_backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
