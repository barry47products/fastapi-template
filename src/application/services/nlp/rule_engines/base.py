"""Base rule engine interface and result model."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field


class RuleEngineResult(BaseModel):
    """Result from a rule engine classification."""

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score",
    )
    keywords: list[str] = Field(description="Keywords that matched in the message")
    rule_matches: list[str] = Field(description="Rules that matched for debugging")

    model_config = ConfigDict(frozen=True)


class BaseRuleEngine(ABC):
    """Abstract base class for all rule engines."""

    @abstractmethod
    def classify(self, message: str) -> RuleEngineResult:
        """
        Classify a message and return confidence score with matched keywords.

        Args:
            message: The message text to classify

        Returns:
            RuleEngineResult with confidence, keywords, and rule matches
        """
