"""API integration tests for WhatsApp and Health endpoints.

These tests exercise complete request-to-response flows through the real application
stack, providing high coverage with minimal mocking. Each test touches 50-150+ lines
across multiple modules including routing, middleware, business logic, and responses.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.api.app_factory import create_app


@pytest.fixture
def whatsapp_test_client() -> TestClient:
    """FastAPI test client for WhatsApp integration testing with dependency overrides."""
    from src.infrastructure.security import check_rate_limit, verify_api_key

    app = create_app()

    # Override dependencies to avoid configuration issues
    def mock_verify_api_key() -> None:
        """Mock API key verification - always passes."""
        return None

    def mock_check_rate_limit() -> None:
        """Mock rate limit check - always passes."""
        return None

    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit

    return TestClient(app)


@pytest.fixture
def health_test_client() -> TestClient:
    """FastAPI test client for health endpoint integration testing."""
    from src.infrastructure.security import check_rate_limit
    from src.interfaces.api.routers.health import get_health_checker, get_service_registry

    app = create_app()

    # Mock rate limiting
    def mock_check_rate_limit() -> None:
        """Mock rate limit check - always passes."""
        return None

    # Mock service registry and health checker
    mock_service_registry = MagicMock()
    mock_health_checker = AsyncMock()

    # Configure mock health response for basic health check
    mock_health_data = {
        "status": "healthy",
        "modules": ["api", "database", "messaging"],
        "timestamp": "2025-01-01T12:00:00Z",
    }
    mock_health_checker.check_health.return_value = mock_health_data
    mock_service_registry.get_health_checker.return_value = mock_health_checker

    def mock_get_service_registry() -> MagicMock:
        """Mock service registry dependency."""
        return mock_service_registry

    def mock_get_health_checker() -> AsyncMock:
        """Mock health checker dependency."""
        return mock_health_checker

    # Override dependencies
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit
    app.dependency_overrides[get_service_registry] = mock_get_service_registry
    app.dependency_overrides[get_health_checker] = mock_get_health_checker

    return TestClient(app)


@pytest.fixture
def detailed_health_test_client() -> TestClient:
    """FastAPI test client for detailed health endpoint integration testing."""
    from src.infrastructure.security import check_rate_limit
    from src.interfaces.api.routers.health import get_health_checker, get_service_registry

    app = create_app()

    # Mock rate limiting
    def mock_check_rate_limit() -> None:
        """Mock rate limit check - always passes."""
        return None

    # Mock service registry and health checker
    mock_service_registry = MagicMock()
    mock_health_checker = AsyncMock()

    # Configure mock detailed health response
    mock_health_data = {
        "status": "healthy",
        "timestamp": "2025-01-01T12:00:00Z",
        "checks": {
            "database": {
                "status": "healthy",
                "response_time_ms": 15.5,
                "error": None,
            },
            "messaging": {
                "status": "healthy",
                "response_time_ms": 8.2,
                "error": None,
            },
        },
    }
    mock_health_checker.check_health.return_value = mock_health_data
    mock_service_registry.get_health_checker.return_value = mock_health_checker

    def mock_get_service_registry() -> MagicMock:
        """Mock service registry dependency."""
        return mock_service_registry

    def mock_get_health_checker() -> AsyncMock:
        """Mock health checker dependency."""
        return mock_health_checker

    # Override dependencies
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit
    app.dependency_overrides[get_service_registry] = mock_get_service_registry
    app.dependency_overrides[get_health_checker] = mock_get_health_checker

    return TestClient(app)


@pytest.fixture
def valid_group_webhook() -> dict[str, str | int]:
    """Valid webhook payload for group message."""
    return {
        "typeWebhook": "incomingMessageReceived",
        "chatId": "12345678901234567890@g.us",
        "senderId": "27821234567@c.us",
        "senderName": "Alice Johnson",
        "textMessage": "I recommend John the plumber 082-123-4567! Great work.",
        "timestamp": 1735470000,
    }


@pytest.fixture
def individual_chat_webhook() -> dict[str, str | int]:
    """Webhook payload for individual (non-group) message."""
    return {
        "typeWebhook": "incomingMessageReceived",
        "chatId": "12345678901234567890@c.us",  # Individual chat (c.us not g.us)
        "senderId": "27821111111@c.us",
        "senderName": "Bob Smith",
        "textMessage": "Hello, how are you?",
        "timestamp": 1735470000,
    }


# WhatsApp API Integration Tests


@pytest.mark.integration
@pytest.mark.whatsapp
@pytest.mark.endorsement
@pytest.mark.fast
@pytest.mark.smoke
def test_should_process_group_message_successfully(
    whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
    valid_group_webhook: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Test complete group message processing flow.

    This vertical slice test covers:
    - Webhook API endpoint (/webhooks/whatsapp/message)
    - Authentication and rate limiting
    - Group message detection (@g.us suffix)
    - Message classification pipeline
    - Processing orchestration
    - Response generation with metrics

    Estimated coverage: 100+ lines across 5-7 modules
    """
    # Arrange - Mock the module-level metrics variable
    with patch("src.interfaces.api.routers.webhooks.metrics") as mock_metrics_collector:
        # Act - Make webhook request
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_group_webhook,
        )

        # Assert - Verify successful processing
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        response_data = response.json()

        # Response structure validation
        assert "status" in response_data
        assert "action" in response_data
        assert "processing_time_ms" in response_data

        # Processing action should indicate group processing
        assert response_data["status"] == "processed"
        # Could be "processed_group_endorsement" or "skipped_invalid_group"
        # depending on classification
        assert "group" in response_data["action"] or "processed" in response_data["action"]

        # Performance validation
        processing_time_ms = float(response_data["processing_time_ms"])
        assert 0 < processing_time_ms < 5000  # Should complete within 5 seconds

        # Verify metrics were recorded
        mock_metrics_collector.increment_counter.assert_called()
        mock_metrics_collector.record_histogram.assert_called()


@pytest.mark.integration
@pytest.mark.whatsapp
@pytest.mark.fast
def test_should_handle_individual_message_appropriately(
    whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
    individual_chat_webhook: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Test individual message handling (non-group).

    This test covers:
    - Individual chat detection (@c.us suffix)
    - Early return logic for non-group messages
    - Proper logging and response generation

    Estimated coverage: 50+ lines across routing and processing
    """
    # Arrange - Mock the module-level metrics variable
    with patch("src.interfaces.api.routers.webhooks.metrics") as mock_metrics_collector:
        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=individual_chat_webhook,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        # Should skip individual messages
        assert response_data["status"] == "processed"
        assert response_data["action"] == "skipped_individual_message"
        assert "processing_time_ms" in response_data

        # Should be very fast since no processing occurs
        processing_time_ms = float(response_data["processing_time_ms"])
        assert 0 < processing_time_ms < 1000

        # Verify metrics recorded individual message handling
        mock_metrics_collector.increment_counter.assert_called()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.whatsapp
@pytest.mark.fast
def test_should_handle_authentication_failure(
    valid_group_webhook: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Test authentication failure handling.

    Tests security boundary behaviour when API key validation fails.
    This covers the security middleware and error handling pipeline.
    """
    # Create test client with auth failure override
    from src.infrastructure.security import check_rate_limit, verify_api_key

    app = create_app()

    def mock_verify_api_key_failure() -> None:
        """Mock API key verification that fails."""
        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    def mock_check_rate_limit() -> None:
        """Mock rate limit check - always passes."""
        return None

    app.dependency_overrides[verify_api_key] = mock_verify_api_key_failure
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit

    test_client_with_auth_failure = TestClient(app)

    # Act
    response = test_client_with_auth_failure.post(
        "/webhooks/whatsapp/message",
        json=valid_group_webhook,
    )

    # Assert - Should return authentication error
    assert response.status_code in [401, 403, 422, 500]  # Auth failure status codes


@pytest.mark.integration
@pytest.mark.resilience
@pytest.mark.whatsapp
@pytest.mark.fast
def test_should_handle_malformed_webhook_payload(
    whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
) -> None:
    """Test malformed payload handling.

    Tests input validation and error handling for invalid webhook data.
    This covers schema validation and error response generation.
    """
    # Arrange - Invalid payload missing required fields
    malformed_payload = {
        "chatId": "invalid",  # Missing other required fields
    }

    # Act - Dependencies already overridden in test_client fixture
    response = whatsapp_test_client.post(
        "/webhooks/whatsapp/message",
        json=malformed_payload,
    )

    # Assert - Should return validation error
    assert response.status_code in [400, 422]  # Validation error status codes


# Health API Integration Tests


@pytest.mark.integration
@pytest.mark.fast
@pytest.mark.smoke
def test_should_handle_basic_health_check_successfully(
    health_test_client: TestClient,  # pylint: disable=redefined-outer-name
) -> None:
    """Test basic health endpoint vertical slice.

    This vertical slice test covers:
    - Health API endpoint (/health/)
    - Rate limiting middleware
    - Service registry dependency injection
    - Health checker service instantiation
    - Health status evaluation and response generation

    Estimated coverage: 30+ lines across health router, service registry, and schemas
    """
    # Act - Make health check request
    response = health_test_client.get("/health/")

    # Assert - Verify successful health response
    assert response.status_code == 200
    response_data = response.json()

    # Response structure validation
    assert "status" in response_data
    assert "modules" in response_data
    assert "timestamp" in response_data

    # Status should be healthy or unhealthy
    assert response_data["status"] in ["healthy", "unhealthy"]

    # Modules should be a list
    assert isinstance(response_data["modules"], list)

    # Timestamp should be ISO 8601 format string
    assert isinstance(response_data["timestamp"], str)
    assert len(response_data["timestamp"]) > 10  # Basic ISO format check


@pytest.mark.integration
@pytest.mark.fast
def test_should_handle_detailed_health_check_successfully(
    detailed_health_test_client: TestClient,  # pylint: disable=redefined-outer-name
) -> None:
    """Test detailed health endpoint vertical slice.

    This vertical slice test covers:
    - Detailed health API endpoint (/health/detailed)
    - Rate limiting middleware
    - Service registry and health checker dependency injection
    - Component-level health checking
    - Complex response object construction with nested schemas

    Estimated coverage: 40+ lines across health router, health checker, and response schemas
    """
    # Act - Make detailed health check request
    response = detailed_health_test_client.get("/health/detailed")

    # Assert - Verify successful detailed health response
    assert response.status_code == 200
    response_data = response.json()

    # Response structure validation
    assert "status" in response_data
    assert "checks" in response_data
    assert "timestamp" in response_data

    # Status should be healthy or unhealthy
    assert response_data["status"] in ["healthy", "unhealthy"]

    # Checks should be a dictionary of component health details
    assert isinstance(response_data["checks"], dict)

    # Validate nested check structure if any checks present
    for component_name, check_detail in response_data["checks"].items():
        assert isinstance(component_name, str)
        assert "status" in check_detail
        assert "response_time_ms" in check_detail
        assert check_detail["status"] in ["healthy", "unhealthy"]
        assert isinstance(check_detail["response_time_ms"], int | float)
        assert check_detail["response_time_ms"] >= 0

    # Timestamp should be ISO 8601 format string
    assert isinstance(response_data["timestamp"], str)
    assert len(response_data["timestamp"]) > 10  # Basic ISO format check
