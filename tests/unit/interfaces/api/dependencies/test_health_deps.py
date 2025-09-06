"""Unit tests for health check API dependencies."""

from __future__ import annotations

import inspect
from typing import get_type_hints
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.service_registry import ServiceRegistry
from src.interfaces.api.dependencies.health_deps import (
    get_health_checker,
    get_service_registry_dependency,
)


class TestGetServiceRegistryDependency:
    """Test service registry dependency for health endpoints."""

    @patch("src.interfaces.api.dependencies.health_deps.get_service_registry")
    def test_returns_service_registry_instance(self, mock_get_registry: MagicMock) -> None:
        """Returns service registry singleton instance."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        result = get_service_registry_dependency()

        assert result is mock_registry
        mock_get_registry.assert_called_once()

    @patch("src.interfaces.api.dependencies.health_deps.get_service_registry")
    def test_calls_get_service_registry_function(self, mock_get_registry: MagicMock) -> None:
        """Calls get_service_registry function."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        get_service_registry_dependency()

        mock_get_registry.assert_called_once_with()

    @patch("src.interfaces.api.dependencies.health_deps.get_service_registry")
    def test_propagates_service_registry_exceptions(self, mock_get_registry: MagicMock) -> None:
        """Propagates exceptions from get_service_registry."""
        mock_get_registry.side_effect = RuntimeError("Service registry not initialized")

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            get_service_registry_dependency()

    def test_function_has_correct_return_type_annotation(self) -> None:
        """Function has correct return type annotation."""
        hints = get_type_hints(get_service_registry_dependency)
        assert hints["return"] == ServiceRegistry

    def test_function_has_no_parameters(self) -> None:
        """Function takes no parameters."""
        sig = inspect.signature(get_service_registry_dependency)
        assert len(sig.parameters) == 0

    def test_function_is_synchronous(self) -> None:
        """Function is synchronous (not async)."""
        assert not inspect.iscoroutinefunction(get_service_registry_dependency)


class TestGetHealthChecker:
    """Test health checker dependency."""

    def test_function_has_registry_dependency_parameter(self) -> None:
        """Function has service registry dependency parameter."""
        sig = inspect.signature(get_health_checker)

        assert "registry" in sig.parameters
        param = sig.parameters["registry"]

        # Check parameter has default value from Depends
        assert param.default is not None
        assert hasattr(param.default, "dependency")  # Depends object has dependency attribute

    def test_registry_parameter_uses_correct_dependency(self) -> None:
        """Registry parameter uses get_service_registry_dependency."""
        sig = inspect.signature(get_health_checker)
        registry_param = sig.parameters["registry"]

        depends_obj = registry_param.default
        assert hasattr(depends_obj, "dependency")  # Depends object has dependency attribute
        assert depends_obj.dependency == get_service_registry_dependency

    def test_function_has_correct_return_type_annotation(self) -> None:
        """Function has correct return type annotation."""
        # Can't resolve forward reference in test context, so check annotation directly
        sig = inspect.signature(get_health_checker)
        assert sig.return_annotation == "HealthChecker"

    def test_function_is_synchronous(self) -> None:
        """Function is synchronous (not async)."""
        assert not inspect.iscoroutinefunction(get_health_checker)

    def test_returns_health_checker_from_registry(self) -> None:
        """Returns health checker from service registry."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_health_checker = MagicMock()
        mock_registry.get_health_checker.return_value = mock_health_checker

        result = get_health_checker(registry=mock_registry)

        assert result is mock_health_checker
        mock_registry.get_health_checker.assert_called_once()

    def test_calls_registry_get_health_checker_method(self) -> None:
        """Calls registry get_health_checker method."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_health_checker = MagicMock()
        mock_registry.get_health_checker.return_value = mock_health_checker

        get_health_checker(registry=mock_registry)

        mock_registry.get_health_checker.assert_called_once_with()

    def test_propagates_registry_exceptions(self) -> None:
        """Propagates exceptions from registry get_health_checker."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_registry.get_health_checker.side_effect = RuntimeError("Health checker not configured")

        with pytest.raises(RuntimeError, match="Health checker not configured"):
            get_health_checker(registry=mock_registry)

    def test_dependency_chain_integration(self) -> None:
        """Tests dependency chain integration conceptually."""
        # This tests that the dependency parameter has the right structure
        # for FastAPI to inject get_service_registry_dependency() -> get_health_checker()
        sig = inspect.signature(get_health_checker)
        registry_param = sig.parameters["registry"]

        # Verify the dependency chain setup
        assert registry_param.annotation == ServiceRegistry
        assert hasattr(registry_param.default, "dependency")  # Depends object
        assert registry_param.default.dependency == get_service_registry_dependency

    def test_type_checking_import_structure(self) -> None:
        """Verifies TYPE_CHECKING import structure is correct."""
        # This is a code structure test to ensure the TYPE_CHECKING import works
        import src.interfaces.api.dependencies.health_deps as health_deps_module

        # Should have TYPE_CHECKING import
        assert hasattr(health_deps_module, "TYPE_CHECKING")

        # The function should exist and be callable
        assert callable(health_deps_module.get_health_checker)


class TestHealthDependenciesIntegration:
    """Test integration scenarios for health dependencies."""

    @patch("src.interfaces.api.dependencies.health_deps.get_service_registry")
    def test_full_dependency_chain_mock(self, mock_get_registry: MagicMock) -> None:
        """Tests full dependency chain with mocks."""
        # Setup mock chain
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_health_checker = MagicMock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_health_checker.return_value = mock_health_checker

        # Test registry dependency
        registry = get_service_registry_dependency()
        assert registry is mock_registry

        # Test health checker dependency using the registry
        health_checker = get_health_checker(registry=registry)
        assert health_checker is mock_health_checker

        # Verify call chain
        mock_get_registry.assert_called_once()
        mock_registry.get_health_checker.assert_called_once()

    def test_dependency_function_signatures_compatible(self) -> None:
        """Verifies dependency function signatures are compatible."""
        # Test that get_service_registry_dependency output matches get_health_checker input
        health_checker_sig = inspect.signature(get_health_checker)

        # Registry dependency returns ServiceRegistry
        registry_hints = get_type_hints(get_service_registry_dependency)
        assert registry_hints["return"] == ServiceRegistry

        # Health checker dependency accepts ServiceRegistry
        health_checker_params = health_checker_sig.parameters
        assert health_checker_params["registry"].annotation == ServiceRegistry

    def test_fastapi_dependency_structure(self) -> None:
        """Verifies FastAPI dependency structure is correct."""
        sig = inspect.signature(get_health_checker)
        registry_param = sig.parameters["registry"]

        # Should use FastAPI Depends with correct dependency
        assert hasattr(registry_param.default, "dependency")  # Depends object
        assert registry_param.default.dependency == get_service_registry_dependency

        # Should have correct type annotation for dependency injection
        assert registry_param.annotation == ServiceRegistry
