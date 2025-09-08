"""Unit tests for infrastructure initialization module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.initialization import (
    initialize_infrastructure,
    shutdown_infrastructure,
)


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
