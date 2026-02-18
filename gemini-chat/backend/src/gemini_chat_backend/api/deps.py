"""FastAPI dependencies."""

from typing import AsyncGenerator

from fastapi import Request

from gemini_chat_backend.config import Settings, settings
from gemini_chat_backend.utils.logging import get_logger, get_request_logger


async def get_settings() -> Settings:
    """Get application settings.

    Returns:
        Application settings instance
    """
    return settings


async def get_logger_dep(request: Request):
    """Get logger with request context.

    Args:
        request: FastAPI request object

    Returns:
        Logger with request context
    """
    request_id = getattr(request.state, "request_id", "unknown")
    return get_request_logger(request_id=request_id)


def get_request_id(request: Request) -> str:
    """Get or generate request ID.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    request_id = getattr(request.state, "request_id", None)
    if not request_id:
        import uuid

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
    return request_id
