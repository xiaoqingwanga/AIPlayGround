"""Health check endpoint."""

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health check response with status
    """
    return HealthResponse(status="healthy")


@router.get("/ready", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def readiness_check() -> HealthResponse:
    """Readiness check endpoint.

    Returns:
        Readiness check response with status
    """
    return HealthResponse(status="ready")
