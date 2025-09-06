"""Unit tests for domain types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.domain.types import (
    ChangeData,
    ChangeValue,
    ConfigData,
    ConfigValue,
    HealthCheckResult,
    MessageStatus,
    Metadata,
    MetadataValue,
    NotificationData,
    ProductData,
    ServiceInfo,
    UserData,
)


class TestMetadataTypes:
    """Test metadata type aliases."""

    def test_metadata_value_accepts_valid_types(self) -> None:
        """MetadataValue accepts str, int, float, bool, and None."""
        values: list[MetadataValue] = [
            "string",
            42,
            3.14,
            True,
            False,
            None,
        ]

        # Type checker should accept all these values
        for value in values:
            assert isinstance(value, str | int | float | bool | type(None))

    def test_metadata_dict_accepts_valid_structure(self) -> None:
        """Metadata accepts dict with string keys and MetadataValue values."""
        metadata: Metadata = {
            "string_key": "value",
            "int_key": 42,
            "float_key": 3.14,
            "bool_key": True,
            "none_key": None,
        }

        assert len(metadata) == 5
        assert metadata["string_key"] == "value"
        assert metadata["int_key"] == 42
        assert metadata["float_key"] == 3.14
        assert metadata["bool_key"] is True
        assert metadata["none_key"] is None


class TestConfigTypes:
    """Test configuration type aliases."""

    def test_config_value_accepts_valid_types(self) -> None:
        """ConfigValue accepts str, int, float, bool, list[str], and dict[str, str]."""
        values: list[ConfigValue] = [
            "string",
            42,
            3.14,
            True,
            ["item1", "item2"],
            {"key": "value"},
        ]

        # Verify all values are of expected types
        assert isinstance(values[0], str)
        assert isinstance(values[1], int)
        assert isinstance(values[2], float)
        assert isinstance(values[3], bool)
        assert isinstance(values[4], list)
        assert isinstance(values[5], dict)

    def test_config_data_accepts_valid_structure(self) -> None:
        """ConfigData accepts dict with string keys and ConfigValue values."""
        config: ConfigData = {
            "app_name": "test-app",
            "port": 8000,
            "debug": True,
            "rate_limit": 100.5,
            "allowed_hosts": ["localhost", "127.0.0.1"],
            "database": {"host": "localhost", "port": "5432"},
        }

        assert len(config) == 6
        assert config["app_name"] == "test-app"
        assert config["port"] == 8000
        assert config["debug"] is True


class TestChangeTypes:
    """Test change tracking type aliases."""

    def test_change_value_accepts_valid_types(self) -> None:
        """ChangeValue accepts str, int, float, bool, datetime, and None."""
        now = datetime.now(UTC)
        values: list[ChangeValue] = [
            "string",
            42,
            3.14,
            True,
            now,
            None,
        ]

        assert isinstance(values[0], str)
        assert isinstance(values[1], int)
        assert isinstance(values[2], float)
        assert isinstance(values[3], bool)
        assert isinstance(values[4], datetime)
        assert values[5] is None

    def test_change_data_accepts_valid_structure(self) -> None:
        """ChangeData accepts dict with string keys and ChangeValue values."""
        now = datetime.now(UTC)
        changes: ChangeData = {
            "name": "new_name",
            "age": 30,
            "salary": 50000.0,
            "active": True,
            "updated_at": now,
            "deleted_at": None,
        }

        assert len(changes) == 6
        assert changes["name"] == "new_name"
        assert changes["updated_at"] == now


class TestNotificationTypes:
    """Test notification type aliases."""

    def test_notification_data_accepts_valid_types(self) -> None:
        """NotificationData accepts dict with str, int, bool values."""
        notification: NotificationData = {
            "title": "Test Notification",
            "priority": 1,
            "urgent": True,
            "retry_count": 3,
        }

        assert notification["title"] == "Test Notification"
        assert notification["priority"] == 1
        assert notification["urgent"] is True
        assert notification["retry_count"] == 3


class TestUserDataTypedDict:
    """Test UserData typed dictionary."""

    def test_user_data_structure(self) -> None:
        """UserData has correct structure and types."""
        created = datetime.now(UTC)
        updated = datetime.now(UTC)

        user: UserData = {
            "id": "user-123",
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "created_at": created,
            "updated_at": updated,
        }

        assert user["id"] == "user-123"
        assert user["name"] == "John Doe"
        assert user["email"] == "john@example.com"
        assert user["age"] == 30
        assert user["created_at"] == created
        assert user["updated_at"] == updated

    def test_user_data_required_fields(self) -> None:
        """UserData requires all specified fields."""
        # TypedDict doesn't enforce at runtime, but structure is documented
        created = datetime.now(UTC)
        updated = datetime.now(UTC)

        user: UserData = {
            "id": "123",
            "name": "Test",
            "email": "test@test.com",
            "age": 25,
            "created_at": created,
            "updated_at": updated,
        }

        # Verify all required fields are present
        required_keys = {"id", "name", "email", "age", "created_at", "updated_at"}
        assert set(user.keys()) == required_keys


class TestProductDataTypedDict:
    """Test ProductData typed dictionary."""

    def test_product_data_structure(self) -> None:
        """ProductData has correct structure and types."""
        created = datetime.now(UTC)

        product: ProductData = {
            "id": "prod-456",
            "name": "Test Product",
            "description": "A test product",
            "price": 99.99,
            "category": "Electronics",
            "created_at": created,
            "in_stock": True,
        }

        assert product["id"] == "prod-456"
        assert product["name"] == "Test Product"
        assert product["description"] == "A test product"
        assert product["price"] == 99.99
        assert product["category"] == "Electronics"
        assert product["created_at"] == created
        assert product["in_stock"] is True

    def test_product_data_required_fields(self) -> None:
        """ProductData requires all specified fields."""
        created = datetime.now(UTC)

        product: ProductData = {
            "id": "123",
            "name": "Product",
            "description": "Description",
            "price": 10.0,
            "category": "Category",
            "created_at": created,
            "in_stock": False,
        }

        # Verify all required fields are present
        required_keys = {"id", "name", "description", "price", "category", "created_at", "in_stock"}
        assert set(product.keys()) == required_keys


class TestHealthCheckResultModel:
    """Test HealthCheckResult Pydantic model."""

    def test_health_check_result_creation(self) -> None:
        """Creates HealthCheckResult with valid data."""
        result = HealthCheckResult(
            status="healthy",
            timestamp="2024-01-01T12:00:00Z",
            checks={"database": "ok", "cache": "ok"},
            details={"database": "Connection successful", "cache": "Hit rate: 95%"},
            version="1.0.0",
            uptime_seconds=3600.5,
        )

        assert result.status == "healthy"
        assert result.timestamp == "2024-01-01T12:00:00Z"
        assert result.checks == {"database": "ok", "cache": "ok"}
        assert result.details == {"database": "Connection successful", "cache": "Hit rate: 95%"}
        assert result.version == "1.0.0"
        assert result.uptime_seconds == 3600.5

    def test_health_check_result_is_frozen(self) -> None:
        """HealthCheckResult is immutable (frozen)."""
        result = HealthCheckResult(
            status="healthy",
            timestamp="2024-01-01T12:00:00Z",
            checks={},
            details={},
            version="1.0.0",
            uptime_seconds=0.0,
        )

        with pytest.raises(ValidationError):
            result.status = "unhealthy"  # type: ignore[misc]

    def test_health_check_result_field_descriptions(self) -> None:
        """HealthCheckResult has correct field descriptions."""
        fields = HealthCheckResult.model_fields

        assert fields["status"].description == "Overall health status"
        assert fields["timestamp"].description == "When the check was performed"
        assert fields["checks"].description == "Individual component status"
        assert fields["details"].description == "Additional status details"
        assert fields["version"].description == "Application version"
        assert fields["uptime_seconds"].description == "Application uptime in seconds"

    def test_health_check_result_validation(self) -> None:
        """HealthCheckResult validates field types."""
        with pytest.raises(ValidationError):
            HealthCheckResult(
                status=123,  # type: ignore[arg-type] # Should be string, not int
                timestamp="2024-01-01T12:00:00Z",
                checks={},
                details={},
                version="1.0.0",
                uptime_seconds=0.0,
            )


class TestServiceInfoModel:
    """Test ServiceInfo Pydantic model."""

    def test_service_info_creation(self) -> None:
        """Creates ServiceInfo with valid data."""
        started_at = datetime.now(UTC)

        service = ServiceInfo(
            name="test-service",
            version="2.1.0",
            environment="production",
            instance_id="inst-789",
            started_at=started_at,
        )

        assert service.name == "test-service"
        assert service.version == "2.1.0"
        assert service.environment == "production"
        assert service.instance_id == "inst-789"
        assert service.started_at == started_at

    def test_service_info_is_frozen(self) -> None:
        """ServiceInfo is immutable (frozen)."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            environment="test",
            instance_id="test-123",
            started_at=datetime.now(UTC),
        )

        with pytest.raises(ValidationError):
            service.name = "new-name"  # type: ignore[misc]

    def test_service_info_field_descriptions(self) -> None:
        """ServiceInfo has correct field descriptions."""
        fields = ServiceInfo.model_fields

        assert fields["name"].description == "Service name"
        assert fields["version"].description == "Service version"
        assert fields["environment"].description == "Deployment environment"
        assert fields["instance_id"].description == "Unique instance identifier"
        assert fields["started_at"].description == "When the service started"

    def test_service_info_datetime_validation(self) -> None:
        """ServiceInfo validates datetime fields."""
        with pytest.raises(ValidationError):
            ServiceInfo(
                name="test",
                version="1.0.0",
                environment="test",
                instance_id="123",
                started_at="not a datetime",  # type: ignore[arg-type]
            )


class TestMessageStatusModel:
    """Test MessageStatus Pydantic model."""

    def test_message_status_creation_full(self) -> None:
        """Creates MessageStatus with all fields."""
        sent_at = datetime.now(UTC)
        delivered_at = datetime.now(UTC)

        message = MessageStatus(
            message_id="msg-123",
            status="delivered",
            sent_at=sent_at,
            delivered_at=delivered_at,
            error_message=None,
            metadata={"channel": "email", "priority": 1},
        )

        assert message.message_id == "msg-123"
        assert message.status == "delivered"
        assert message.sent_at == sent_at
        assert message.delivered_at == delivered_at
        assert message.error_message is None
        assert message.metadata == {"channel": "email", "priority": 1}

    def test_message_status_creation_minimal(self) -> None:
        """Creates MessageStatus with only required fields."""
        sent_at = datetime.now(UTC)

        message = MessageStatus(
            message_id="msg-456",
            status="pending",
            sent_at=sent_at,
        )

        assert message.message_id == "msg-456"
        assert message.status == "pending"
        assert message.sent_at == sent_at
        assert message.delivered_at is None
        assert message.error_message is None
        assert message.metadata == {}

    def test_message_status_with_error(self) -> None:
        """Creates MessageStatus with error information."""
        sent_at = datetime.now(UTC)

        message = MessageStatus(
            message_id="msg-error",
            status="failed",
            sent_at=sent_at,
            error_message="Network timeout",
        )

        assert message.status == "failed"
        assert message.error_message == "Network timeout"
        assert message.delivered_at is None

    def test_message_status_is_frozen(self) -> None:
        """MessageStatus is immutable (frozen)."""
        message = MessageStatus(
            message_id="msg-123",
            status="sent",
            sent_at=datetime.now(UTC),
        )

        with pytest.raises(ValidationError):
            message.status = "delivered"  # type: ignore[misc]

    def test_message_status_field_descriptions(self) -> None:
        """MessageStatus has correct field descriptions."""
        fields = MessageStatus.model_fields

        assert fields["message_id"].description == "Unique message identifier"
        assert fields["status"].description == "Delivery status"
        assert fields["sent_at"].description == "When message was sent"
        assert fields["delivered_at"].description == "When message was delivered"
        assert fields["error_message"].description == "Error details if failed"
        assert fields["metadata"].description == "Additional metadata"

    def test_message_status_default_factory(self) -> None:
        """MessageStatus uses default factory for metadata."""
        message1 = MessageStatus(
            message_id="msg-1",
            status="sent",
            sent_at=datetime.now(UTC),
        )

        message2 = MessageStatus(
            message_id="msg-2",
            status="sent",
            sent_at=datetime.now(UTC),
        )

        # Each instance should have its own metadata dict
        assert message1.metadata is not message2.metadata
        assert message1.metadata == {}
        assert message2.metadata == {}

    def test_message_status_optional_fields(self) -> None:
        """MessageStatus handles optional fields correctly."""
        sent_at = datetime.now(UTC)
        delivered_at = datetime.now(UTC)

        # Test with all optional fields
        message = MessageStatus(
            message_id="msg-opt",
            status="delivered",
            sent_at=sent_at,
            delivered_at=delivered_at,
            error_message="All good",
            metadata={"test": "value"},
        )

        assert message.delivered_at == delivered_at
        assert message.error_message == "All good"
        assert message.metadata == {"test": "value"}


class TestTypesIntegration:
    """Test integration between different domain types."""

    def test_metadata_in_message_status(self) -> None:
        """MessageStatus correctly uses Metadata type."""
        metadata: Metadata = {
            "string_field": "value",
            "int_field": 42,
            "bool_field": True,
            "float_field": 3.14,
            "none_field": None,
        }

        message = MessageStatus(
            message_id="integration-test",
            status="sent",
            sent_at=datetime.now(UTC),
            metadata=metadata,
        )

        assert message.metadata == metadata
        assert isinstance(message.metadata["string_field"], str)
        assert isinstance(message.metadata["int_field"], int)
        assert isinstance(message.metadata["bool_field"], bool)
        assert isinstance(message.metadata["float_field"], float)
        assert message.metadata["none_field"] is None

    def test_type_compatibility(self) -> None:
        """Verifies type compatibility across domain types."""
        # Test that complex types work together
        user: UserData = {
            "id": "user-1",
            "name": "Test User",
            "email": "test@example.com",
            "age": 25,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        changes: ChangeData = {
            "name": user["name"],
            "age": user["age"],
            "updated_at": user["updated_at"],
        }

        notification: NotificationData = {
            "user_id": user["id"],
            "message": f"Welcome {user['name']}",
            "priority": 1,
        }

        assert changes["name"] == "Test User"
        assert notification["user_id"] == "user-1"

    def test_model_serialization(self) -> None:
        """Test that Pydantic models serialize correctly."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            environment="test",
            instance_id="test-123",
            started_at=datetime.now(UTC),
        )

        # Should be able to serialize to dict
        data = service.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "test-service"
        assert data["version"] == "1.0.0"

        # Should be able to serialize to JSON
        json_str = service.model_dump_json()
        assert isinstance(json_str, str)
        assert "test-service" in json_str
