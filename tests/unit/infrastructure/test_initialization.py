"""Unit tests for infrastructure initialization module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from src.infrastructure.initialization import (
    initialize_infrastructure,
    shutdown_infrastructure,
)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestInitializeInfrastructure:
    """Test infrastructure initialization behavior."""

    @patch("src.infrastructure.initialization.get_logger")
    def test_initializes_successfully(self, mock_get_logger: MagicMock) -> None:
        """Initializes infrastructure successfully with dependency injection."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Should not raise any exceptions
        initialize_infrastructure()

        # Verify logging
        mock_logger.info.assert_any_call(
            "Initializing infrastructure services", environment="development"
        )
        mock_logger.info.assert_any_call("Infrastructure initialization completed successfully")

    @patch("src.infrastructure.initialization.configure_repository_provider")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_initialization_failures_gracefully(
        self,
        mock_get_logger: MagicMock,
        mock_configure_health_checker: MagicMock,
        mock_configure_api_key_validator: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_configure_repository_provider: MagicMock,
    ) -> None:
        """Should handle initialization failures and log errors appropriately."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Make one of the configure functions raise an exception
        test_error = ValueError("Configuration failed")
        mock_configure_health_checker.side_effect = test_error

        # Should re-raise the exception after logging
        with pytest.raises(ValueError, match="Configuration failed"):
            initialize_infrastructure()

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            "Infrastructure initialization failed", error="Configuration failed"
        )

        # Verify initialization was attempted
        mock_logger.info.assert_called_with(
            "Initializing infrastructure services", environment="development"
        )


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestShutdownInfrastructure:
    """Test infrastructure shutdown behavior."""

    @patch("src.infrastructure.initialization.get_logger")
    def test_shuts_down_infrastructure_successfully(self, mock_get_logger: MagicMock) -> None:
        """Shuts down infrastructure successfully with dependency injection."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Should not raise any exceptions
        shutdown_infrastructure()

        # Verify logging
        mock_logger.info.assert_any_call("Infrastructure shutdown completed")
