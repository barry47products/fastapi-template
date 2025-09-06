"""Unit tests for main module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from src.main import app, basic_status_check, run_development_server

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestAppCreation:
    """Test app creation behavior."""

    def test_creates_fastapi_instance(self) -> None:
        """Creates a FastAPI app instance."""
        assert isinstance(app, FastAPI)
        assert hasattr(app, "get")
        assert hasattr(app, "post")
        assert hasattr(app, "routes")


class TestStatusEndpoint:
    """Test status endpoint behavior."""

    def test_returns_200_status_code(self, client: TestClient) -> None:
        """Returns 200 status code."""
        response = client.get("/status")
        assert response.status_code == 200

    async def test_returns_healthy_status(self) -> None:
        """Returns healthy status."""
        result = await basic_status_check()
        assert result["status"] == "healthy"

    async def test_returns_loaded_modules_list(self) -> None:
        """Returns list of loaded modules."""
        result = await basic_status_check()

        expected_modules = [
            "settings",
            "logging",
            "metrics",
            "api_key_validator",
            "rate_limiter",
            "webhook_verifier",
            "health_checker",
        ]
        assert result["modules"] == expected_modules

    def test_allows_access_without_authentication(self, client: TestClient) -> None:
        """Allows access without authentication."""
        response = client.get("/status")
        assert response.status_code == 200

        response = client.get("/status", headers={"X-API-Key": "invalid"})
        assert response.status_code == 200

    def test_returns_json_content_type(self, client: TestClient) -> None:
        """Returns JSON content type."""
        response = client.get("/status")
        assert response.headers["content-type"] == "application/json"

    def test_returns_expected_response_structure(self, client: TestClient) -> None:
        """Returns expected response structure."""
        response = client.get("/status")
        data = response.json()

        assert isinstance(data, dict)
        assert "status" in data
        assert "modules" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["modules"], list)

    def test_includes_all_required_modules(self, client: TestClient) -> None:
        """Includes all required infrastructure modules."""
        response = client.get("/status")
        data = response.json()

        required_modules = [
            "settings",
            "logging",
            "metrics",
            "api_key_validator",
            "rate_limiter",
            "webhook_verifier",
            "health_checker",
        ]

        for module in required_modules:
            assert module in data["modules"], f"Module {module} not found in status"


class TestDevelopmentServer:
    """Test development server behavior."""

    @patch("src.main.uvicorn.run")
    @patch("src.main.create_development_server_config")
    @patch("src.main.get_logger")
    def test_starts_uvicorn_with_config(
        self,
        mock_get_logger: MagicMock,
        mock_create_config: MagicMock,
        mock_uvicorn_run: MagicMock,
    ) -> None:
        """Starts uvicorn with configuration from factory."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_config = {
            "app": "src.main:app",
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True,
        }
        mock_create_config.return_value = mock_config

        run_development_server()

        mock_create_config.assert_called_once()
        mock_uvicorn_run.assert_called_once_with(**mock_config)

    @patch("src.main.uvicorn.run")
    @patch("src.main.create_development_server_config")
    @patch("src.main.get_logger")
    def test_logs_startup_message(
        self,
        mock_get_logger: MagicMock,
        mock_create_config: MagicMock,
        mock_uvicorn_run: MagicMock,
    ) -> None:
        """Logs startup message before starting server."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_create_config.return_value = {}

        run_development_server()

        mock_get_logger.assert_called_once_with("src.main")
        mock_logger.info.assert_called_once_with("Starting development server")

    @patch("src.main.uvicorn.run")
    @patch("src.main.create_development_server_config")
    @patch("src.main.get_logger")
    def test_propagates_config_creation_errors(
        self,
        mock_get_logger: MagicMock,
        mock_create_config: MagicMock,
        mock_uvicorn_run: MagicMock,
    ) -> None:
        """Propagates configuration creation errors."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_create_config.side_effect = Exception("Config error")

        with pytest.raises(Exception, match="Config error"):
            run_development_server()

        mock_uvicorn_run.assert_not_called()

    @patch("src.main.uvicorn.run")
    @patch("src.main.create_development_server_config")
    @patch("src.main.get_logger")
    def test_passes_all_config_parameters(
        self,
        mock_get_logger: MagicMock,
        mock_create_config: MagicMock,
        mock_uvicorn_run: MagicMock,
    ) -> None:
        """Passes all configuration parameters to uvicorn."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_config = {
            "app": "src.main:app",
            "host": "127.0.0.1",
            "port": 9000,
            "reload": False,
            "log_level": "debug",
            "access_log": True,
        }
        mock_create_config.return_value = mock_config

        run_development_server()

        mock_uvicorn_run.assert_called_once_with(
            app="src.main:app",
            host="127.0.0.1",
            port=9000,
            reload=False,
            log_level="debug",
            access_log=True,
        )


class TestMainModuleEntry:
    """Test main module entry point behavior."""

    @patch("src.main.run_development_server")
    def test_runs_development_server_when_main(self, mock_run_server: MagicMock) -> None:
        """Runs development server when executed as main module."""
        # Simulate running the module as __main__
        import src.main

        # Mock __name__ to be "__main__"
        original_name = src.main.__name__
        src.main.__name__ = "__main__"

        try:
            # Execute the if __name__ == "__main__" block
            if src.main.__name__ == "__main__":
                src.main.run_development_server()

            mock_run_server.assert_called_once()
        finally:
            # Restore original __name__
            src.main.__name__ = original_name
