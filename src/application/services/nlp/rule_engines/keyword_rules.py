"""Keyword-based rule engine for message classification."""

import re
from pathlib import Path

import yaml

from config.settings import MessageClassificationSettings
from src.infrastructure.observability.logger import get_logger
from src.infrastructure.observability.metrics import get_metrics_collector
from src.shared.exceptions import MessageClassificationError

from .base import BaseRuleEngine, RuleEngineResult


def load_yaml_config(config_path: str) -> dict[str, dict[str, float]]:
    """Load YAML configuration file."""
    try:
        with Path(config_path).open("r", encoding="utf-8") as file:
            config: dict[str, dict[str, float]] = yaml.safe_load(file)
            return config
    except FileNotFoundError as e:
        raise MessageClassificationError(
            f"Configuration file not found: {config_path}",
        ) from e
    except yaml.YAMLError as e:
        raise MessageClassificationError(
            f"Invalid YAML configuration: {config_path}",
        ) from e


class KeywordRuleEngine(BaseRuleEngine):
    """Rule engine that classifies messages based on keyword matching."""

    def __init__(self, settings: MessageClassificationSettings) -> None:
        """Initialize keyword rule engine with configuration."""
        self.settings = settings
        self._logger = get_logger(__name__)
        self._metrics = get_metrics_collector()

        config = load_yaml_config(settings.keywords_config_file)
        self.request_keywords: dict[str, float] = config.get("request_keywords", {})
        self.recommendation_keywords: dict[str, float] = config.get(
            "recommendation_keywords",
            {},
        )

    def classify(self, message: str) -> RuleEngineResult:
        """Classify message using keyword matching."""
        if not message.strip():
            return RuleEngineResult(
                confidence=0.0,
                keywords=[],
                rule_matches=[],
            )

        message_lower = message.lower()
        matched_keywords = []
        rule_matches = []
        total_confidence = 0.0

        # Check request keywords
        for keyword, weight in self.request_keywords.items():
            if self._match_keyword(keyword, message_lower):
                matched_keywords.append(keyword)
                rule_matches.append(f"keyword:{keyword}")
                total_confidence += weight

        # Check recommendation keywords
        for keyword, weight in self.recommendation_keywords.items():
            if self._match_keyword(keyword, message_lower):
                matched_keywords.append(keyword)
                rule_matches.append(f"keyword:{keyword}")
                total_confidence += weight

        # Normalize confidence to 0-1 range using sigmoid-like scaling
        final_confidence = min(total_confidence / 2.0, 1.0) if total_confidence > 0 else 0.0

        return RuleEngineResult(
            confidence=final_confidence,
            keywords=matched_keywords,
            rule_matches=rule_matches,
        )

    def _match_keyword(self, keyword: str, message: str) -> bool:
        """Match whole word keywords only."""
        pattern = rf"\b{re.escape(keyword.lower())}\b"
        return bool(re.search(pattern, message))
