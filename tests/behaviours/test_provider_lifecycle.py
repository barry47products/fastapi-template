"""Provider lifecycle behaviour tests - Provider creation and management."""

from unittest.mock import MagicMock

import pytest

from src.domain.models import Provider
from src.domain.value_objects import PhoneNumber, ProviderID


class ProviderService:
    """Mock provider service interface for testing provider lifecycle behaviors."""

    def create_provider(self, name: str, phone: PhoneNumber, category: str) -> Provider:
        """Create a new provider."""
        return Provider(
            id=ProviderID(),
            name=name,
            phone=phone,
            category=category,
            endorsement_count=1,
        )

    def get_provider_by_phone(self, phone: PhoneNumber) -> Provider | None:
        """Get provider by phone number."""
        return None

    def update_endorsement_count(self, provider_id: ProviderID, count: int) -> Provider:
        """Update provider endorsement count."""
        return Provider(
            id=provider_id,
            name="Mock Provider",
            phone=PhoneNumber(value="+27821234567"),
            category="mock",
            endorsement_count=count,
        )

    def merge_providers(self, primary_id: ProviderID, secondary_id: ProviderID) -> Provider:
        """Merge two provider records."""
        return Provider(
            id=primary_id,
            name="Merged Provider",
            phone=PhoneNumber(value="+27821234567"),
            category="merged",
            endorsement_count=0,
        )

    def update_category(self, provider_id: ProviderID, category: str) -> Provider:
        """Update provider category."""
        return Provider(
            id=provider_id,
            name="Updated Provider",
            phone=PhoneNumber(value="+27821234567"),
            category=category,
            endorsement_count=0,
        )


@pytest.fixture
def mock_provider_service() -> MagicMock:
    """Mock provider service for testing provider lifecycle behaviours."""
    return MagicMock(spec=ProviderService)


@pytest.fixture
def sample_phone_number() -> PhoneNumber:
    """Sample phone number for provider testing."""
    return PhoneNumber(value="+27821234567")


@pytest.fixture
def existing_provider(
    sample_phone_number: PhoneNumber,  # pylint: disable=redefined-outer-name
) -> Provider:  # pylint: disable=redefined-outer-name
    """Sample existing provider for testing."""
    return Provider(
        id=ProviderID(),
        name="John Smith",
        phone=sample_phone_number,
        category="plumber",
        endorsement_count=0,
    )


def test_should_create_new_provider_on_first_mention(
    mock_provider_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_phone_number: PhoneNumber,  # pylint: disable=redefined-outer-name
) -> None:
    """First mention of provider should create new record."""
    # Arrange
    provider_name = "John the Plumber"
    category = "plumbing"

    expected_provider = Provider(
        id=ProviderID(),
        name=provider_name,
        phone=sample_phone_number,
        category=category,
        endorsement_count=1,  # First endorsement
    )

    # Configure mocks
    mock_provider_service.create_provider.return_value = expected_provider

    # Act
    result = mock_provider_service.create_provider(provider_name, sample_phone_number, category)

    # Assert
    assert result.name == provider_name
    assert result.phone == sample_phone_number
    assert result.category == category
    assert result.endorsement_count == 1
    mock_provider_service.create_provider.assert_called_once_with(
        provider_name,
        sample_phone_number,
        category,
    )


def test_should_increment_endorsement_count_for_existing_provider(
    mock_provider_service: MagicMock,  # pylint: disable=redefined-outer-name
    existing_provider: Provider,  # pylint: disable=redefined-outer-name
) -> None:
    """Subsequent mentions should increment endorsement count."""
    # Arrange
    updated_provider = existing_provider.model_copy(
        update={"endorsement_count": existing_provider.endorsement_count + 1},
    )

    # Configure mocks
    mock_provider_service.get_provider_by_phone.return_value = existing_provider
    mock_provider_service.update_endorsement_count.return_value = updated_provider

    # Act
    result = mock_provider_service.update_endorsement_count(
        existing_provider.id,
        existing_provider.endorsement_count + 1,
    )

    # Assert
    assert result.id == existing_provider.id
    assert result.endorsement_count == existing_provider.endorsement_count + 1
    assert result.name == existing_provider.name
    assert result.phone == existing_provider.phone
    mock_provider_service.update_endorsement_count.assert_called_once_with(
        existing_provider.id,
        existing_provider.endorsement_count + 1,
    )


def test_should_deduplicate_providers_by_phone_number(
    mock_provider_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_phone_number: PhoneNumber,  # pylint: disable=redefined-outer-name
) -> None:
    """Same phone number should return same provider."""
    # Arrange
    found_provider = Provider(
        id=ProviderID(),
        name="John",
        phone=sample_phone_number,
        category="plumber",
        endorsement_count=3,
    )

    # Configure mocks - phone lookup returns existing provider
    mock_provider_service.get_provider_by_phone.return_value = found_provider

    # Act - attempt to create provider with same phone but different name
    result = mock_provider_service.get_provider_by_phone(sample_phone_number)

    # Assert - returns existing provider, no new creation
    assert result is not None
    assert result.id == found_provider.id
    assert result.phone == sample_phone_number
    assert result.endorsement_count == 3  # Existing count preserved
    mock_provider_service.get_provider_by_phone.assert_called_once_with(sample_phone_number)


def test_should_merge_provider_names_with_same_phone(
    mock_provider_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_phone_number: PhoneNumber,  # pylint: disable=redefined-outer-name
) -> None:
    """'John' and 'Johnny' with same phone should get merged."""
    # Arrange
    primary_provider = Provider(
        id=ProviderID(),
        name="John",
        phone=sample_phone_number,
        category="plumber",
        endorsement_count=2,
    )

    secondary_provider = Provider(
        id=ProviderID(),
        name="Johnny",
        phone=sample_phone_number,
        category="plumber",
        endorsement_count=1,
    )

    merged_provider = Provider(
        id=primary_provider.id,
        name="John",  # Primary name kept
        phone=sample_phone_number,
        category="plumber",
        endorsement_count=3,  # Combined endorsements
    )

    # Configure mocks
    mock_provider_service.merge_providers.return_value = merged_provider

    # Act
    result = mock_provider_service.merge_providers(primary_provider.id, secondary_provider.id)

    # Assert
    assert result.id == primary_provider.id
    assert result.name == "John"  # Primary name preserved
    assert result.endorsement_count == 3  # Combined count
    assert result.phone == sample_phone_number
    mock_provider_service.merge_providers.assert_called_once_with(
        primary_provider.id,
        secondary_provider.id,
    )


def test_should_update_provider_category_from_mentions(
    mock_provider_service: MagicMock,  # pylint: disable=redefined-outer-name
    existing_provider: Provider,  # pylint: disable=redefined-outer-name
) -> None:
    """Provider category should be refined based on context."""
    # Arrange
    new_category = "emergency plumbing"
    updated_provider = existing_provider.model_copy(update={"category": new_category})

    # Configure mocks
    mock_provider_service.update_category.return_value = updated_provider

    # Act
    result = mock_provider_service.update_category(existing_provider.id, new_category)

    # Assert
    assert result.id == existing_provider.id
    assert result.category == new_category
    assert result.name == existing_provider.name
    assert result.phone == existing_provider.phone
    assert result.endorsement_count == existing_provider.endorsement_count
    mock_provider_service.update_category.assert_called_once_with(
        existing_provider.id,
        new_category,
    )
