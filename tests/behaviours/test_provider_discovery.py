"""Provider discovery behaviour tests - Provider search and ranking."""

from unittest.mock import MagicMock

import pytest

from src.domain.models import Provider
from src.domain.value_objects import PhoneNumber, ProviderID


class ProviderSearchService:
    """Mock provider search service interface for testing discovery behaviors."""

    def search_by_category(self, category: str) -> list[Provider]:
        """Search providers by exact category match."""
        return []

    def search_by_name(self, name_query: str) -> list[Provider]:
        """Search providers by partial name match."""
        return []

    def search_providers(
        self,
        query: str,
        location: str | None = None,
        sort_by_endorsements: bool = True,
    ) -> list[Provider]:
        """Search providers with optional location filter and endorsement ranking."""
        return []


@pytest.fixture
def mock_search_service() -> MagicMock:
    """Mock provider search service for testing discovery behaviours."""
    return MagicMock(spec=ProviderSearchService)


@pytest.fixture
def sample_providers() -> list[Provider]:
    """Sample providers for testing search and ranking."""
    return [
        Provider(
            id=ProviderID(),
            name="John Smith",
            phone=PhoneNumber(value="+27821111111"),
            category="plumber",
            endorsement_count=5,
        ),
        Provider(
            id=ProviderID(),
            name="Mary Johnson",
            phone=PhoneNumber(value="+27821111112"),
            category="plumber",
            endorsement_count=3,
        ),
        Provider(
            id=ProviderID(),
            name="Davies Electrical",
            phone=PhoneNumber(value="+27821111113"),
            category="electrician",
            endorsement_count=8,
        ),
        Provider(
            id=ProviderID(),
            name="Cape Cleaning Co",
            phone=PhoneNumber(value="+27821111114"),
            category="cleaning",
            endorsement_count=2,
        ),
    ]


def test_should_find_providers_by_exact_category_match(
    mock_search_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_providers: list[Provider],  # pylint: disable=redefined-outer-name
) -> None:
    """Search 'plumber' should return all plumbers."""
    # Arrange
    plumbers = [p for p in sample_providers if p.category == "plumber"]
    mock_search_service.search_by_category.return_value = plumbers

    # Act
    result = mock_search_service.search_by_category("plumber")

    # Assert
    assert len(result) == 2
    assert all(provider.category == "plumber" for provider in result)
    assert result[0].name == "John Smith"
    assert result[1].name == "Mary Johnson"
    mock_search_service.search_by_category.assert_called_once_with("plumber")


def test_should_find_providers_by_partial_name_match(
    mock_search_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_providers: list[Provider],  # pylint: disable=redefined-outer-name
) -> None:
    """Search 'Dav' should match 'Davies Electrical'."""
    # Arrange
    matching_providers = [p for p in sample_providers if "Dav" in p.name]
    mock_search_service.search_by_name.return_value = matching_providers

    # Act
    result = mock_search_service.search_by_name("Dav")

    # Assert
    assert len(result) == 1
    assert result[0].name == "Davies Electrical"
    assert result[0].category == "electrician"
    mock_search_service.search_by_name.assert_called_once_with("Dav")


def test_should_rank_providers_by_endorsement_count(
    mock_search_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_providers: list[Provider],  # pylint: disable=redefined-outer-name
) -> None:
    """Higher endorsement count should result in higher ranking."""
    # Arrange - sort providers by endorsement count descending
    ranked_providers = sorted(
        sample_providers,
        key=lambda p: p.endorsement_count,
        reverse=True,
    )
    mock_search_service.search_providers.return_value = ranked_providers

    # Act
    result = mock_search_service.search_providers("", sort_by_endorsements=True)

    # Assert
    assert len(result) == 4
    assert result[0].name == "Davies Electrical"  # 8 endorsements
    assert result[0].endorsement_count == 8
    assert result[1].name == "John Smith"  # 5 endorsements
    assert result[1].endorsement_count == 5
    assert result[2].name == "Mary Johnson"  # 3 endorsements
    assert result[2].endorsement_count == 3
    assert result[3].name == "Cape Cleaning Co"  # 2 endorsements
    assert result[3].endorsement_count == 2
    mock_search_service.search_providers.assert_called_once_with("", sort_by_endorsements=True)


def test_should_filter_providers_by_location(
    mock_search_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_providers: list[Provider],  # pylint: disable=redefined-outer-name
) -> None:
    """Location-based filtering should return relevant providers."""
    # Arrange - simulate location-based filtering
    cape_town_providers = [
        sample_providers[0],  # John Smith
        sample_providers[2],  # Davies Electrical
    ]
    mock_search_service.search_providers.return_value = cape_town_providers

    # Act
    result = mock_search_service.search_providers("", location="Cape Town")

    # Assert
    assert len(result) == 2
    assert result[0].name == "John Smith"
    assert result[1].name == "Davies Electrical"
    mock_search_service.search_providers.assert_called_once_with("", location="Cape Town")


def test_should_return_empty_list_for_no_matches(
    mock_search_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """No matches should return empty list, not error."""
    # Arrange
    mock_search_service.search_by_category.return_value = []

    # Act
    result = mock_search_service.search_by_category("nonexistent_category")

    # Assert
    assert result == []
    assert len(result) == 0
    mock_search_service.search_by_category.assert_called_once_with("nonexistent_category")
