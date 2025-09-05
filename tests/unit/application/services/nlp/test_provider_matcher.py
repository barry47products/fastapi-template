"""Unit tests for ProviderMatcher service."""

# pylint: disable=redefined-outer-name

from datetime import datetime, UTC

import pytest

from src.application.services.nlp.provider_matcher import ProviderMatcher
from src.domain.models import Provider
from src.domain.value_objects import PhoneNumber, ProviderID
from src.shared.exceptions import ProviderValidationError


@pytest.fixture
def provider_matcher() -> ProviderMatcher:
    """Provider matcher instance for testing."""
    return ProviderMatcher()


@pytest.fixture
def sample_providers() -> list[Provider]:
    """Sample providers for testing matching scenarios."""
    return [
        Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440001"),
            name="John Smith Plumbing Services",
            phone=PhoneNumber(value="+27821234567"),
            category="plumbing",
            tags={"specialties": ["pipes", "leaks"], "verified": "true"},
            endorsement_count=5,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ),
        Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440002"),
            name="Sarah's Electrical",
            phone=PhoneNumber(value="+27823456789"),
            category="electrical",
            tags={"specialties": ["wiring", "installation"]},
            endorsement_count=3,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ),
        Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440003"),
            name="Mike's Carpentry & Woodwork",
            phone=PhoneNumber(value="+27827891234"),
            category="carpentry",
            tags={"specialties": ["furniture", "cabinets"], "area": "johannesburg"},
            endorsement_count=8,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        ),
    ]


class TestProviderMatcherExactMatching:
    """Test exact name matching functionality."""

    def test_should_match_exact_name_case_insensitive(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match exact provider name regardless of case."""
        # Act
        result = provider_matcher.find_best_match(
            "John Smith Plumbing Services",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.match_type == "exact_name"
        assert result.similarity_score == 1.0
        assert result.matched_provider is not None
        assert result.matched_provider.name == "John Smith Plumbing Services"

    def test_should_match_exact_name_with_different_case(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match exact provider name with different casing."""
        # Act
        result = provider_matcher.find_best_match(
            "SARAH'S ELECTRICAL",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.match_type == "exact_name"
        assert result.matched_provider is not None
        assert result.matched_provider.name == "Sarah's Electrical"


class TestProviderMatcherPartialMatching:
    """Test partial name matching with fuzzy string algorithms."""

    def test_should_match_partial_name_with_high_similarity(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match partial provider name with good similarity score."""
        # Act
        result = provider_matcher.find_best_match(
            "John Smith Plumbing",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type == "partial_name"
        assert result.confidence > 0.7  # Should be high confidence
        assert result.similarity_score > 0.8
        assert result.matched_provider is not None
        assert result.matched_provider.name == "John Smith Plumbing Services"

    def test_should_handle_business_name_variations(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match business name variations like abbreviated forms."""
        # Act
        result = provider_matcher.find_best_match(
            "Mike's Carpentry",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type == "partial_name"
        assert result.confidence > 0.6
        assert result.matched_provider is not None
        assert result.matched_provider.name == "Mike's Carpentry & Woodwork"

    def test_should_reject_low_similarity_matches(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should reject matches with very low similarity scores."""
        # Act
        result = provider_matcher.find_best_match(
            "Random Unrelated Business",
            sample_providers,
        )

        # Assert
        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.match_type == "no_match"


class TestProviderMatcherPhoneMatching:
    """Test phone number matching with various formats."""

    def test_should_match_exact_phone_number(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match exact phone number format."""
        # Act
        result = provider_matcher.find_best_match(
            "+27821234567",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.confidence == 0.95
        assert result.match_type == "phone_exact"
        assert result.similarity_score == 1.0
        assert result.matched_provider is not None
        assert result.matched_provider.phone.value == "+27821234567"

    def test_should_match_local_phone_format_to_international(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match local format (082...) to international (+2782...)."""
        # Act
        result = provider_matcher.find_best_match(
            "0821234567",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.confidence == 0.9
        assert result.match_type == "phone_fuzzy"
        assert result.similarity_score == 0.95
        assert result.matched_provider is not None
        assert result.matched_provider.phone.value == "+27821234567"

    def test_should_match_phone_with_formatting_differences(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match phone numbers with different formatting."""
        # Act
        result = provider_matcher.find_best_match(
            "082-123-4567",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.confidence >= 0.9
        assert result.match_type in ["phone_exact", "phone_fuzzy"]
        assert result.matched_provider is not None

    def test_should_handle_phone_in_text_context(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should extract and match phone numbers within text."""
        # Act
        result = provider_matcher.find_best_match(
            "Contact John at 082-123-4567 for plumbing",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type in ["phone_exact", "phone_fuzzy"]
        assert result.matched_provider is not None


class TestProviderMatcherTagBasedMatching:
    """Test tag-based matching functionality."""

    def test_should_match_by_specialty_tags(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match providers based on specialty tags."""
        # Act
        result = provider_matcher.find_best_match(
            "Looking for someone who does pipes and leak repairs",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type in ["tag_based", "semantic_tag"]
        assert result.confidence >= 0.4
        assert result.matched_provider is not None
        assert result.matched_provider.name == "John Smith Plumbing Services"

    def test_should_match_by_area_tags(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should match providers based on area tags."""
        # Act
        result = provider_matcher.find_best_match(
            "Need carpentry work in Johannesburg area",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type in ["tag_based", "semantic_tag"]
        assert result.matched_provider is not None
        assert result.matched_provider.name == "Mike's Carpentry & Woodwork"


class TestProviderMatcherBestMatchSelection:
    """Test best match selection across multiple strategies."""

    def test_should_prefer_exact_name_over_partial_match(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should prioritize exact name matches over partial matches."""
        # Create additional provider with similar name
        similar_provider = Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440004"),
            name="John Smith",  # Partial match
            phone=PhoneNumber(value="+27829999999"),
            category="general",
        )
        providers_with_similar = sample_providers + [similar_provider]

        # Act
        result = provider_matcher.find_best_match(
            "John Smith Plumbing Services",  # Exact match to first provider
            providers_with_similar,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type == "exact_name"
        assert result.confidence == 1.0
        assert result.matched_provider is not None
        assert result.matched_provider.name == "John Smith Plumbing Services"

    def test_should_prefer_phone_over_low_confidence_name_match(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should prioritize phone matches over low-confidence name matches."""
        # Act
        result = provider_matcher.find_best_match(
            "Random Business Name but call 082-345-6789",
            sample_providers,
        )

        # Assert
        assert result.is_match is True
        assert result.match_type in ["phone_exact", "phone_fuzzy"]
        assert result.confidence >= 0.9  # Phone matching should be high confidence
        assert result.matched_provider is not None
        assert result.matched_provider.phone.value == "+27823456789"


class TestProviderMatcherErrorHandling:
    """Test error handling and edge cases."""

    def test_should_raise_error_for_empty_mention(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should raise validation error for empty mention."""
        # Act & Assert
        with pytest.raises(ProviderValidationError, match="Provider mention cannot be empty"):
            provider_matcher.find_best_match("", sample_providers)

    def test_should_raise_error_for_whitespace_only_mention(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should raise validation error for whitespace-only mention."""
        # Act & Assert
        with pytest.raises(ProviderValidationError, match="Provider mention cannot be empty"):
            provider_matcher.find_best_match("   ", sample_providers)

    def test_should_return_no_match_for_empty_provider_list(
        self,
        provider_matcher: ProviderMatcher,
    ) -> None:
        """Should return no match when provider list is empty."""
        # Act
        result = provider_matcher.find_best_match("John Smith", [])

        # Assert
        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.match_type == "no_match"
        assert result.matched_provider is None

    def test_should_handle_providers_with_empty_tags(
        self,
        provider_matcher: ProviderMatcher,
    ) -> None:
        """Should handle providers with no tags gracefully."""
        # Arrange
        provider_no_tags = Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440005"),
            name="Simple Service",
            phone=PhoneNumber(value="+27821111111"),
            category="general",
            tags={},
        )

        # Act
        result = provider_matcher.find_best_match(
            "Simple Service",
            [provider_no_tags],
        )

        # Assert
        assert result.is_match is True
        assert result.match_type == "exact_name"
        assert result.confidence == 1.0


class TestProviderMatcherConfidenceScoring:
    """Test confidence scoring accuracy and consistency."""

    def test_confidence_scores_should_be_properly_ordered(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Confidence scores should follow expected hierarchy: exact > partial > phone > tags."""
        # Test exact match
        exact_result = provider_matcher.find_best_match(
            "John Smith Plumbing Services",
            sample_providers,
        )

        # Test partial match
        partial_result = provider_matcher.find_best_match(
            "John Smith Plumbing",
            sample_providers,
        )

        # Test phone match
        phone_result = provider_matcher.find_best_match(
            "+27821234567",
            sample_providers,
        )

        # Assert confidence hierarchy
        assert exact_result.confidence == 1.0  # Exact should be perfect
        assert partial_result.confidence > 0.7  # Partial should be high
        assert phone_result.confidence == 0.95  # Phone should be very high
        assert exact_result.confidence > partial_result.confidence

    def test_should_reject_very_low_confidence_matches(
        self,
        provider_matcher: ProviderMatcher,
        sample_providers: list[Provider],
    ) -> None:
        """Should reject matches below minimum confidence threshold."""
        # Act
        result = provider_matcher.find_best_match(
            "Completely unrelated business xyz",
            sample_providers,
        )

        # Assert
        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.match_type == "no_match"
