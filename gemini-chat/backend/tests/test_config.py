"""Tests for configuration module."""

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
