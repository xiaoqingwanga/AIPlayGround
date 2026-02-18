"""Tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from gemini_chat_backend.main import app, create_app


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_check_returns_healthy(self, client: TestClient) -> None:
        """Test that health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_check_content_type(self, client: TestClient) -> None:
        """Test that health check returns JSON content type."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestAppCreation:
    """Test suite for FastAPI app creation."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test that create_app returns a FastAPI instance."""
        from fastapi import FastAPI

        test_app = create_app()
        assert isinstance(test_app, FastAPI)

    def test_app_has_correct_title(self) -> None:
        """Test that app has correct title."""
        test_app = create_app()
        assert test_app.title == "Gemini Chat Backend"


class TestAppInstance:
    """Test suite for the global app instance."""

    def test_global_app_exists(self) -> None:
        """Test that the global app instance exists."""
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)
