"""Provider matching logic for deduplication and similarity scoring."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TypedDict

import Levenshtein
from pydantic import BaseModel, ConfigDict

from src.domain.models import Provider
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import ProviderValidationError


class MatchData(TypedDict):
    """Type for match data dictionary."""

    provider: Provider | None
    confidence: float
    match_type: str
    similarity: float


class MatchResult(TypedDict):
    """Type for match result dictionary."""

    confidence: float
    match_type: str
    similarity: float


@dataclass
class ProviderMatchResult:
    """Result of provider matching operation."""

    is_match: bool
    confidence: float
    matched_provider: Provider | None
    match_type: str
    similarity_score: float


class ProviderMatcher(BaseModel):
    """Provider matching service for deduplication and similarity scoring."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data: dict[str, object]) -> None:
        """Initialize provider matcher with observability."""
        super().__init__(**data)
        self._logger = get_logger(__name__)
        self._metrics = get_metrics_collector()

    def find_best_match(
        self,
        mention: str,
        existing_providers: list[Provider],
    ) -> ProviderMatchResult:
        """Find the best matching provider for a given mention.

        Args:
            mention: Provider mention to match against
            existing_providers: List of existing providers to match against

        Returns:
            ProviderMatchResult with match details

        Raises:
            ProviderValidationError: If mention is empty or invalid
        """
        mention = self._validate_and_prepare_mention(mention)

        if not existing_providers:
            return self._create_no_match_result()

        best_match_data = self._find_best_provider_match(mention, existing_providers)

        if best_match_data["confidence"] < 0.4:
            # Record unhandled pattern for monitoring
            self._record_unhandled_pattern(mention, existing_providers)
            return self._create_no_match_result()

        return self._create_successful_match_result(best_match_data)

    def _validate_and_prepare_mention(self, mention: str) -> str:
        """Validate and prepare mention for matching."""
        if not mention or not mention.strip():
            raise ProviderValidationError("Provider mention cannot be empty")

        mention = mention.strip()

        # Log matching attempt
        self._logger.info("Starting provider matching", mention_length=len(mention))

        # Record matching metrics
        self._metrics.increment_counter(
            "provider_matching_attempts_total",
            {"type": "find_best_match"},
        )

        return mention

    def _find_best_provider_match(
        self,
        mention: str,
        existing_providers: list[Provider],
    ) -> MatchData:
        """Find the best matching provider from the list."""
        best_match_data: MatchData = {
            "provider": None,
            "confidence": 0.0,
            "match_type": "no_match",
            "similarity": 0.0,
        }

        for provider in existing_providers:
            match_result = self._evaluate_provider_match(mention, provider)
            if match_result and match_result["confidence"] > best_match_data["confidence"]:
                best_match_data = {
                    "provider": provider,
                    "confidence": match_result["confidence"],
                    "match_type": match_result["match_type"],
                    "similarity": match_result["similarity"],
                }

        return best_match_data

    def _evaluate_provider_match(
        self,
        mention: str,
        provider: Provider,
    ) -> MatchResult | None:
        """Evaluate all matching strategies for a single provider."""
        # Strategy 1: Exact name match
        if mention.lower() == provider.name.lower():
            return {
                "confidence": 1.0,
                "match_type": "exact_name",
                "similarity": 1.0,
            }

        # Strategy 2: Enhanced fuzzy name matching
        fuzzy_result = self._fuzzy_name_match(mention, provider)
        if fuzzy_result:
            return fuzzy_result

        # Strategy 3: Phone number matching
        phone_match = self._match_phone_number(mention, provider)
        if phone_match:
            return phone_match

        # Strategy 4: Tag-based matching
        tag_match = self._match_tags(mention, provider)
        if tag_match:
            return {
                "confidence": tag_match["confidence"],
                "match_type": "tag_based",
                "similarity": tag_match["similarity"],
            }

        # Strategy 5: Enhanced semantic tag matching
        semantic_match = self._enhanced_semantic_tag_match(mention, provider)
        if semantic_match:
            return semantic_match

        return None

    def _create_successful_match_result(
        self,
        match_data: MatchData,
    ) -> ProviderMatchResult:
        """Create a successful match result with logging and metrics."""
        # Log successful match
        provider = match_data["provider"]
        if provider is not None:
            self._logger.info(
                "Provider match found",
                matched_provider_id=str(provider.id),
                confidence=match_data["confidence"],
                match_type=match_data["match_type"],
            )

        # Record success metrics
        self._metrics.increment_counter(
            "provider_matches_total",
            {"match_type": match_data["match_type"]},
        )

        return ProviderMatchResult(
            is_match=True,
            confidence=match_data["confidence"],
            matched_provider=match_data["provider"],
            match_type=match_data["match_type"],
            similarity_score=match_data["similarity"],
        )

    def _match_phone_number(
        self,
        mention: str,
        provider: Provider,
    ) -> MatchResult | None:
        """Match provider by phone number."""
        phone_matches = self._extract_phone_patterns(mention)
        if not phone_matches:
            return None

        provider_phone_str = str(provider.phone)

        for phone_mention in phone_matches:
            match_result = self._compare_phone_numbers(
                phone_mention,
                provider_phone_str,
            )
            if match_result:
                return match_result

        return None

    def _extract_phone_patterns(self, mention: str) -> list[str]:
        """Extract phone-like patterns from mention."""
        phone_pattern = r"(\+?[\d\s\-\(\)]{10,})"
        return re.findall(phone_pattern, mention)

    def _compare_phone_numbers(
        self,
        phone_mention: str,
        provider_phone_str: str,
    ) -> MatchResult | None:
        """Compare two phone numbers with exact and fuzzy matching."""
        clean_mention = re.sub(r"[\s\-\(\)\+]", "", phone_mention)
        clean_provider = re.sub(r"[\s\-\(\)\+]", "", provider_phone_str)

        # Exact match
        if clean_mention == clean_provider:
            return {
                "confidence": 0.95,
                "match_type": "phone_exact",
                "similarity": 1.0,
            }

        # Fuzzy match strategies
        if len(clean_mention) >= 10 and len(clean_provider) >= 10:
            return self._try_fuzzy_phone_match(clean_mention, clean_provider)

        return None

    def _try_fuzzy_phone_match(
        self,
        clean_mention: str,
        clean_provider: str,
    ) -> MatchResult | None:
        """Try fuzzy phone matching strategies."""
        # Strategy 1: Last 10 digits match
        if clean_mention.endswith(clean_provider[-10:]):
            return {
                "confidence": 0.9,
                "match_type": "phone_fuzzy",
                "similarity": 0.95,
            }

        # Strategy 2: Local to international conversion
        if self._is_local_to_international_match(clean_mention, clean_provider):
            return {
                "confidence": 0.9,
                "match_type": "phone_fuzzy",
                "similarity": 0.95,
            }

        return None

    def _is_local_to_international_match(
        self,
        clean_mention: str,
        clean_provider: str,
    ) -> bool:
        """Check if mention is local format matching international format."""
        if not (clean_mention.startswith("0") and clean_provider.startswith("27")):
            return False

        mention_without_zero = clean_mention[1:]  # Remove leading 0
        provider_without_country = clean_provider[2:]  # Remove "27"
        return mention_without_zero == provider_without_country

    def _match_tags(
        self,
        mention: str,
        provider: Provider,
    ) -> MatchResult | None:
        """Match provider by tags similarity."""
        if not provider.tags:
            return None

        mention_lower = mention.lower()
        tag_matches = self._count_tag_matches(mention_lower, provider.tags)
        total_tags = self._count_total_tags(provider.tags)

        if total_tags == 0:
            return None

        similarity = tag_matches / total_tags
        confidence = similarity * 0.7  # Tag matching is less confident than name/phone

        if confidence >= 0.4:
            return {
                "confidence": confidence,
                "match_type": "tag_based",
                "similarity": similarity,
            }

        return None

    def _count_tag_matches(
        self,
        mention_lower: str,
        tags: dict[str, list[str] | str],
    ) -> int:
        """Count how many tags match the mention."""
        matches = 0

        for category, tag_values in tags.items():
            # Check category match
            if category.lower() in mention_lower:
                matches += 1

            # Check individual tag values
            if isinstance(tag_values, list):
                matches += sum(
                    1
                    for tag_value in tag_values
                    if isinstance(tag_value, str) and tag_value.lower() in mention_lower
                )

        return matches

    def _count_total_tags(self, tags: dict[str, list[str] | str]) -> int:
        """Count total number of tags and tag values."""
        total = len(tags)  # Count categories

        for tag_values in tags.values():
            if isinstance(tag_values, list):
                total += len(tag_values)

        return total

    def _get_confidence_bucket(self, confidence: float) -> str:
        """Categorize confidence score for metrics."""
        if confidence >= 0.9:
            return "high"
        if confidence >= 0.7:
            return "medium"
        if confidence >= 0.5:
            return "low"
        return "very_low"

    def _fuzzy_name_match(
        self,
        mention: str,
        provider: Provider,
    ) -> MatchResult | None:
        """Enhanced fuzzy name matching with multiple algorithms."""
        try:
            mention_lower = mention.lower()
            provider_name_lower = provider.name.lower()

            # Strategy 1: Simple containment check
            if mention_lower in provider_name_lower or provider_name_lower in mention_lower:
                similarity = SequenceMatcher(None, mention_lower, provider_name_lower).ratio()
                return {
                    "confidence": similarity * 0.9,
                    "match_type": "partial_name",
                    "similarity": similarity,
                }

            # Strategy 2: Levenshtein distance for close matches
            max_len = max(len(mention_lower), len(provider_name_lower))
            if max_len > 0:
                levenshtein_distance: int = Levenshtein.distance(mention_lower, provider_name_lower)
                levenshtein_similarity = 1 - (levenshtein_distance / max_len)

                if levenshtein_similarity >= 0.7:
                    return {
                        "confidence": levenshtein_similarity * 0.85,
                        "match_type": "fuzzy_name",
                        "similarity": levenshtein_similarity,
                    }

            # Strategy 3: Word-based matching for business names
            word_similarity = self._calculate_word_similarity(mention_lower, provider_name_lower)
            if word_similarity >= 0.6:
                return {
                    "confidence": word_similarity * 0.8,
                    "match_type": "word_similarity",
                    "similarity": word_similarity,
                }

            return None

        except Exception as e:
            self._logger.error(
                "Fuzzy name matching failed",
                mention_length=len(mention),
                provider_name=provider.name[:30],  # Truncate for privacy
                error=str(e),
            )
            self._metrics.increment_counter(
                "provider_matching_errors_total",
                {"error_type": "fuzzy_name_match", "algorithm": "levenshtein"},
            )
            return None

    def _calculate_word_similarity(self, mention: str, provider_name: str) -> float:
        """Calculate similarity based on common words between mention and provider name."""
        mention_words = set(mention.split())
        provider_words = set(provider_name.split())

        if not mention_words or not provider_words:
            return 0.0

        common_words = mention_words.intersection(provider_words)
        total_unique_words = len(mention_words.union(provider_words))

        if total_unique_words == 0:
            return 0.0

        return len(common_words) / total_unique_words

    def _enhanced_semantic_tag_match(
        self,
        mention: str,
        provider: Provider,
    ) -> MatchResult | None:
        """Enhanced semantic tag matching with fuzzy string matching."""
        try:
            if not provider.tags:
                return None

            mention_lower = mention.lower()
            best_match_score = self._get_best_tag_match_score(mention_lower, provider.tags)

            if best_match_score >= 0.6:
                # Tag matching is less confident than name/phone
                confidence = best_match_score * 0.7

                # Record semantic matching success
                self._metrics.increment_counter(
                    "provider_semantic_matches_total",
                    {"confidence_bucket": self._get_confidence_bucket(confidence)},
                )

                return {
                    "confidence": confidence,
                    "match_type": "semantic_tag",
                    "similarity": best_match_score,
                }

            return None

        except Exception as e:
            self._logger.error(
                "Semantic tag matching failed",
                mention_length=len(mention),
                tag_count=len(provider.tags) if provider.tags else 0,
                error=str(e),
            )
            self._metrics.increment_counter(
                "provider_matching_errors_total",
                {"error_type": "semantic_tag_match"},
            )
            return None

    def _get_best_tag_match_score(
        self,
        mention_lower: str,
        tags: dict[str, list[str] | str],
    ) -> float:
        """Get the best match score across all tags."""
        best_score = 0.0

        for category, tag_values in tags.items():
            # Check category match
            category_score = self._fuzzy_match_score(mention_lower, category.lower())
            if category_score > 0.6:
                best_score = max(best_score, category_score)

            # Check tag values
            best_score = max(best_score, self._check_tag_values_match(mention_lower, tag_values))

        return best_score

    def _check_tag_values_match(self, mention_lower: str, tag_values: list[str] | str) -> float:
        """Check match score for tag values."""
        best_score = 0.0

        if isinstance(tag_values, list):
            for tag_value in tag_values:
                if isinstance(tag_value, str):
                    score = self._fuzzy_match_score(mention_lower, tag_value.lower())
                    if score > 0.6:
                        best_score = max(best_score, score)
        elif isinstance(tag_values, str):
            score = self._fuzzy_match_score(mention_lower, tag_values.lower())
            if score > 0.6:
                best_score = max(best_score, score)

        return best_score

    def _fuzzy_match_score(self, mention: str, target: str) -> float:
        """Calculate fuzzy match score using multiple algorithms."""
        try:
            # Check direct containment first (highest score)
            containment_score = self._calculate_containment_score(mention, target)
            if containment_score > 0:
                return containment_score

            # Check word overlap
            word_overlap_score = self._calculate_word_overlap_score(mention, target)
            if word_overlap_score > 0:
                return word_overlap_score

            # Check Levenshtein similarity for short strings
            levenshtein_score = self._calculate_levenshtein_score(mention, target)
            if levenshtein_score > 0:
                return levenshtein_score

            return 0.0

        except Exception as e:
            self._logger.debug(
                "Fuzzy match score calculation failed",
                mention_length=len(mention) if mention else 0,
                target_length=len(target) if target else 0,
                error=str(e),
            )
            return 0.0

    def _calculate_containment_score(self, mention: str, target: str) -> float:
        """Calculate score based on direct containment."""
        if target in mention or mention in target:
            return 0.9
        return 0.0

    def _calculate_word_overlap_score(self, mention: str, target: str) -> float:
        """Calculate score based on word overlap."""
        mention_words = set(mention.split())
        target_words = set(target.split())

        if not mention_words or not target_words:
            return 0.0

        word_overlap = len(mention_words.intersection(target_words))
        total_words = len(mention_words.union(target_words))

        if total_words > 0 and word_overlap > 0:
            word_score = word_overlap / total_words
            if word_score >= 0.3:
                return word_score * 0.8

        return 0.0

    def _calculate_levenshtein_score(self, mention: str, target: str) -> float:
        """Calculate score based on Levenshtein distance for short strings."""
        if len(target) > 20:  # Only for reasonably short strings
            return 0.0

        max_len = max(len(mention), len(target))
        if max_len == 0:
            return 0.0

        distance: int = Levenshtein.distance(mention, target)
        similarity = 1 - (distance / max_len)

        if similarity >= 0.7:
            return similarity * 0.7

        return 0.0

    def _record_unhandled_pattern(
        self,
        mention: str,
        existing_providers: list[Provider],
    ) -> None:
        """Record unhandled pattern for monitoring and analysis."""
        self._logger.warning(
            "Unhandled provider pattern detected",
            mention=mention[:50],  # Truncate for privacy
            mention_length=len(mention),
            provider_count=len(existing_providers),
            provider_categories=[p.category for p in existing_providers[:3]],  # Sample
        )

        self._metrics.increment_counter(
            "provider_matching_unhandled_patterns_total",
            {"mention_length_bucket": self._get_length_bucket(len(mention))},
        )

    def _get_length_bucket(self, length: int) -> str:
        """Categorize mention length for metrics."""
        if length <= 10:
            return "short"
        if length <= 30:
            return "medium"
        if length <= 50:
            return "long"
        return "very_long"

    def _create_no_match_result(self) -> ProviderMatchResult:
        """Create a no-match result."""
        return ProviderMatchResult(
            is_match=False,
            confidence=0.0,
            matched_provider=None,
            match_type="no_match",
            similarity_score=0.0,
        )
