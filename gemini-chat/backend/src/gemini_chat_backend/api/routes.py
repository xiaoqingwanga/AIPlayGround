"""API route registration."""

from fastapi import APIRouter, FastAPI

from gemini_chat_backend.api.endpoints import chat, health, tools


def setup_routes(app: FastAPI) -> None:
    """Set up API routes.

    Args:
        app: FastAPI application instance
    """
    # Create main API router
    api_router = APIRouter(prefix="/api/v1")

    # Include endpoint routers
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(chat.router, tags=["chat"])
    api_router.include_router(tools.router, tags=["tools"])

    # Include main router in app
    app.include_router(api_router)

    # Health check at root level (already in main.py)
    # Additional routes can be added here
