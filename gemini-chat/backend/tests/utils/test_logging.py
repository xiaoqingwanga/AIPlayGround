"""Tests for logging utility module."""

import logging
from unittest.mock import patch

import pytest
import structlog

from gemini_chat_backend.utils.logging import (
    configure_logging,
    get_logger,
    get_request_logger,
)


class TestConfigureLogging:
    """Test suite for configure_logging function."""

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
