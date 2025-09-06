"""Unit tests for administrative API dependencies."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.service_registry import ServiceRegistry
from src.interfaces.api.dependencies.admin_deps import get_service_registry_dependency


class TestGetServiceRegistryDependency:
    """Test service registry dependency for admin endpoints."""

    @patch("src.interfaces.api.dependencies.admin_deps.get_service_registry")
    def test_returns_service_registry_instance(self, mock_get_registry: MagicMock) -> None:
        """Returns service registry singleton instance."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        result = get_service_registry_dependency()

        assert result is mock_registry
        mock_get_registry.assert_called_once()

    @patch("src.interfaces.api.dependencies.admin_deps.get_service_registry")
    def test_calls_get_service_registry_function(self, mock_get_registry: MagicMock) -> None:
        """Calls get_service_registry function."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        get_service_registry_dependency()

        mock_get_registry.assert_called_once_with()

    @patch("src.interfaces.api.dependencies.admin_deps.get_service_registry")
    def test_dependency_is_singleton_like(self, mock_get_registry: MagicMock) -> None:
        """Dependency returns singleton-like behavior through get_service_registry."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        result1 = get_service_registry_dependency()
        result2 = get_service_registry_dependency()

        # Both calls should call the underlying function
        assert mock_get_registry.call_count == 2
        # Both should return the same mock object (singleton behavior)
        assert result1 is mock_registry
        assert result2 is mock_registry

    @patch("src.interfaces.api.dependencies.admin_deps.get_service_registry")
    def test_propagates_service_registry_exceptions(self, mock_get_registry: MagicMock) -> None:
        """Propagates exceptions from get_service_registry."""
        mock_get_registry.side_effect = RuntimeError("Service registry not initialized")

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            get_service_registry_dependency()

    def test_function_has_correct_return_type_annotation(self) -> None:
        """Function has correct return type annotation."""
        from typing import get_type_hints

        hints = get_type_hints(get_service_registry_dependency)
        assert hints["return"] == ServiceRegistry

    def test_function_has_no_parameters(self) -> None:
        """Function takes no parameters."""
        import inspect

        sig = inspect.signature(get_service_registry_dependency)
        assert len(sig.parameters) == 0

    def test_function_is_synchronous(self) -> None:
        """Function is synchronous (not async)."""
        import inspect

        assert not inspect.iscoroutinefunction(get_service_registry_dependency)
