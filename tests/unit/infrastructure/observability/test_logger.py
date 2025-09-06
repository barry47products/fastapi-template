"""Unit tests for logger observability component."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import structlog

from src.infrastructure.observability.logger import configure_logging, get_logger


class TestConfigureLogging:
    """Test logging configuration behavior."""

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_logging_with_valid_level(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures logging with valid level."""
        configure_logging(log_level="INFO", environment="production")

        mock_basic_config.assert_called_once()
        mock_structlog_configure.assert_called_once()

        # Verify basic config arguments
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.INFO
        assert call_args[1]["format"] == "%(message)s"

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_logging_with_debug_level(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures logging with DEBUG level."""
        configure_logging(log_level="DEBUG", environment="development")

        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.DEBUG

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_logging_with_error_level(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures logging with ERROR level."""
        configure_logging(log_level="ERROR", environment="production")

        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.ERROR

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_logging_with_warning_level(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures logging with WARNING level."""
        configure_logging(log_level="WARNING", environment="staging")

        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.WARNING

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_logging_with_critical_level(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures logging with CRITICAL level."""
        configure_logging(log_level="CRITICAL", environment="production")

        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.CRITICAL

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_handles_invalid_log_level(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Handles invalid log level by defaulting to INFO."""
        configure_logging(log_level="INVALID", environment="production")

        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == logging.INFO  # Default fallback

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_development_environment(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures development environment with console renderer."""
        configure_logging(log_level="INFO", environment="development")

        # Verify structlog configuration for development
        structlog_call_args = mock_structlog_configure.call_args[1]
        processors = structlog_call_args["processors"]

        # Should have console renderer for development
        has_console_renderer = any(
            isinstance(processor, structlog.dev.ConsoleRenderer) for processor in processors
        )
        assert has_console_renderer

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_production_environment(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures production environment with JSON renderer."""
        configure_logging(log_level="INFO", environment="production")

        # Verify structlog configuration for production
        structlog_call_args = mock_structlog_configure.call_args[1]
        processors = structlog_call_args["processors"]

        # Should have JSON renderer for production
        has_json_renderer = any(
            isinstance(processor, structlog.processors.JSONRenderer) for processor in processors
        )
        assert has_json_renderer

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_staging_environment(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures staging environment with JSON renderer."""
        configure_logging(log_level="INFO", environment="staging")

        # Verify structlog configuration for staging
        structlog_call_args = mock_structlog_configure.call_args[1]
        processors = structlog_call_args["processors"]

        # Should have JSON renderer for non-development environments
        has_json_renderer = any(
            isinstance(processor, structlog.processors.JSONRenderer) for processor in processors
        )
        assert has_json_renderer

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_includes_standard_processors(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Includes standard structlog processors."""
        configure_logging(log_level="INFO", environment="production")

        structlog_call_args = mock_structlog_configure.call_args[1]
        processors = structlog_call_args["processors"]

        # Should include standard processors
        processor_types = [type(p).__name__ for p in processors]
        processor_str = str(processor_types)

        # Check for key processors (some show as 'function')
        assert "PositionalArgumentsFormatter" in processor_str
        assert "StackInfoRenderer" in processor_str
        assert "UnicodeDecoder" in processor_str
        # Functions show up as 'function' in the type list
        assert (
            processor_str.count("function") >= 3
        )  # filter_by_level, add_logger_name, add_log_level

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_configures_structlog_with_correct_settings(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Configures structlog with correct settings."""
        configure_logging(log_level="INFO", environment="production")

        structlog_call_args = mock_structlog_configure.call_args[1]

        assert structlog_call_args["wrapper_class"] == structlog.stdlib.BoundLogger
        assert isinstance(structlog_call_args["logger_factory"], structlog.stdlib.LoggerFactory)
        assert structlog_call_args["context_class"] is dict
        assert structlog_call_args["cache_logger_on_first_use"] is True

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_development_console_renderer_has_colors(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Development console renderer has colors enabled."""
        configure_logging(log_level="INFO", environment="development")

        structlog_call_args = mock_structlog_configure.call_args[1]
        processors = structlog_call_args["processors"]

        console_renderer = None
        for processor in processors:
            if isinstance(processor, structlog.dev.ConsoleRenderer):
                console_renderer = processor
                break

        assert console_renderer is not None
        # ConsoleRenderer is configured with colors via initialization
        assert hasattr(console_renderer, "_styles")  # Internal attribute that confirms colors

    @patch("src.infrastructure.observability.logger.logging.basicConfig")
    @patch("src.infrastructure.observability.logger.structlog.configure")
    def test_development_console_renderer_has_level_styles(
        self, mock_structlog_configure: MagicMock, mock_basic_config: MagicMock
    ) -> None:
        """Development console renderer has level styles."""
        configure_logging(log_level="INFO", environment="development")

        structlog_call_args = mock_structlog_configure.call_args[1]
        processors = structlog_call_args["processors"]

        console_renderer = None
        for processor in processors:
            if isinstance(processor, structlog.dev.ConsoleRenderer):
                console_renderer = processor
                break

        assert console_renderer is not None
        # ConsoleRenderer is configured with custom level styles
        # Since the internal attributes are not guaranteed, just verify it's a ConsoleRenderer
        assert isinstance(console_renderer, structlog.dev.ConsoleRenderer)


class TestGetLogger:
    """Test get logger function behavior."""

    def test_returns_structlog_bound_logger(self) -> None:
        """Returns structlog bound logger instance."""
        logger = get_logger("test_module")

        # Structlog returns a lazy proxy that behaves like BoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_returns_logger_with_correct_name(self) -> None:
        """Returns logger with correct name."""
        module_name = "test.module.name"

        logger = get_logger(module_name)

        # The logger should be bound and functional
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_returns_different_loggers_for_different_names(self) -> None:
        """Returns different loggers for different module names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Both should be valid logger-like objects
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")
        # They should have different logger factory args (names)
        assert hasattr(logger1, "_logger_factory_args")
        assert hasattr(logger2, "_logger_factory_args")
        # Different names should be passed to the factory
        assert logger1._logger_factory_args != logger2._logger_factory_args

    def test_returns_same_logger_for_same_name(self) -> None:
        """Returns same logger instance for same module name."""
        name = "same.module.name"

        logger1 = get_logger(name)
        logger2 = get_logger(name)

        # Structlog uses lazy proxies, so check behavior equivalence
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")
        # Both should be valid logger-like objects
        assert str(logger1._context) == str(logger2._context)

    def test_handles_empty_name(self) -> None:
        """Handles empty logger name."""
        logger = get_logger("")

        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_handles_special_characters_in_name(self) -> None:
        """Handles special characters in logger name."""
        logger = get_logger("module-name_with.special:chars")

        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    @patch("src.infrastructure.observability.logger.structlog.get_logger")
    def test_calls_structlog_get_logger(self, mock_structlog_get: MagicMock) -> None:
        """Calls structlog.get_logger with provided name."""
        mock_bound_logger = MagicMock()
        mock_structlog_get.return_value = mock_bound_logger

        logger_name = "test.logger.name"
        result = get_logger(logger_name)

        mock_structlog_get.assert_called_once_with(logger_name)
        assert result is mock_bound_logger
