"""Group summary domain models for provider summarization."""

from datetime import datetime, UTC
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models.extracted_mention import ExtractedMention
from src.domain.models.provider import Provider
from src.domain.value_objects import GroupID


class SummaryType(str, Enum):
    """Types of summaries that can be generated."""

    COMPREHENSIVE = "comprehensive"
    TOP_RATED = "top_rated"
    RECENT_ACTIVITY = "recent_activity"
    CATEGORY_FOCUSED = "category_focused"

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value

    def is_comprehensive(self) -> bool:
        """Check if summary type is comprehensive."""
        return self == SummaryType.COMPREHENSIVE

    def requires_high_confidence(self) -> bool:
        """Check if summary type requires high confidence filtering."""
        return self == SummaryType.TOP_RATED


class ProviderSummary(BaseModel):
    """
    Immutable domain model representing an individual provider summary.

    Contains provider details, endorsement counts, recent mention history,
    and confidence metrics for inclusion in group summaries.
    """

    model_config = ConfigDict(frozen=True)

    provider: Provider = Field(description="Provider domain model")
    endorsement_count: int = Field(
        ge=0,
        description="Number of endorsements for this provider",
    )
    recent_mentions: list[ExtractedMention] = Field(
        default_factory=list,
        description="Recent mention extractions",
    )
    average_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Average confidence across all mentions",
    )
    service_categories: set[str] = Field(
        default_factory=set,
        description="Identified service categories",
    )
    last_mentioned: datetime = Field(description="Most recent mention timestamp")

    def __str__(self) -> str:
        """Return string representation of ProviderSummary."""
        return (
            f"{self.provider.name}: {self.endorsement_count} endorsements "
            f"(avg confidence: {self.average_confidence:.2f})"
        )

    def __repr__(self) -> str:
        """Return detailed string representation of ProviderSummary."""
        return (
            f"ProviderSummary(provider='{self.provider.name}', "
            f"endorsements={self.endorsement_count}, "
            f"confidence={self.average_confidence})"
        )

    def is_highly_endorsed(self, threshold: int = 3) -> bool:
        """Check if provider is highly endorsed."""
        return self.endorsement_count >= threshold

    def has_recent_activity(self, days: int = 7) -> bool:
        """Check if provider has recent activity within specified days."""
        now = datetime.now(UTC)
        time_delta = now - self.last_mentioned
        return time_delta.days <= days


class GroupSummary(BaseModel):
    """
    Immutable domain model representing a group summary of endorsed providers.

    Contains aggregated provider summaries, total counts, confidence metrics,
    and business logic for filtering and analysis.
    """

    model_config = ConfigDict(frozen=True)

    group_id: GroupID = Field(description="WhatsApp group identifier")
    generation_timestamp: datetime = Field(description="When summary was generated")
    provider_summaries: list[ProviderSummary] = Field(
        default_factory=list,
        description="Individual provider summaries",
    )
    total_providers: int = Field(
        ge=0,
        description="Total number of providers in summary",
    )
    total_endorsements: int = Field(ge=0, description="Total number of endorsements")
    summary_type: SummaryType = Field(description="Type of summary generated")
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall summary quality score",
    )

    def __str__(self) -> str:
        """Return string representation of GroupSummary."""
        return (
            f"{self.summary_type.value.title()} Summary: {self.total_providers} "
            f"providers, {self.total_endorsements} endorsements"
        )

    def __repr__(self) -> str:
        """Return detailed string representation of GroupSummary."""
        return (
            f"GroupSummary(group={self.group_id.value}, "
            f"providers={self.total_providers}, "
            f"type={self.summary_type.value})"
        )

    def __eq__(self, other: object) -> bool:
        """Compare group summaries based on group_id and generation timestamp."""
        if not isinstance(other, GroupSummary):
            return False
        return (
            self.group_id == other.group_id
            and self.generation_timestamp == other.generation_timestamp
            and self.summary_type == other.summary_type
        )

    def __hash__(self) -> int:
        """Return hash based on group_id and generation timestamp."""
        return hash((self.group_id, self.generation_timestamp, self.summary_type))

    def has_providers(self) -> bool:
        """Check if summary contains any providers."""
        return self.total_providers > 0

    def get_top_providers(self, limit: int = 10) -> list[ProviderSummary]:
        """Get top providers by endorsement count."""
        sorted_providers = sorted(
            self.provider_summaries,
            key=lambda p: p.endorsement_count,
            reverse=True,
        )
        return sorted_providers[:limit]

    def filter_by_category(self, category: str) -> list[ProviderSummary]:
        """Filter provider summaries by service category."""
        return [ps for ps in self.provider_summaries if category in ps.service_categories]

    def to_dict(self) -> dict[str, Any]:
        """Convert GroupSummary to dictionary for serialization."""
        return {
            "group_id": self.group_id.value,
            "generation_timestamp": self.generation_timestamp,
            "provider_summaries": [
                {
                    "provider_id": ps.provider.id.value,
                    "provider_name": ps.provider.name,
                    "endorsement_count": ps.endorsement_count,
                    "average_confidence": ps.average_confidence,
                    "service_categories": list(ps.service_categories),
                    "last_mentioned": ps.last_mentioned,
                }
                for ps in self.provider_summaries
            ],
            "total_providers": self.total_providers,
            "total_endorsements": self.total_endorsements,
            "summary_type": self.summary_type.value,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GroupSummary":
        """Create GroupSummary from dictionary data."""
        return cls(
            group_id=GroupID(value=data["group_id"]),
            generation_timestamp=data["generation_timestamp"],
            provider_summaries=data.get("provider_summaries", []),
            total_providers=data["total_providers"],
            total_endorsements=data["total_endorsements"],
            summary_type=SummaryType(data["summary_type"]),
            confidence_score=data["confidence_score"],
        )
