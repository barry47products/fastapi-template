"""Modular message classifier orchestrator."""

from config.settings import MessageClassificationSettings, Settings
from src.application.services.nlp.rule_engines import (
    BaseRuleEngine,
    KeywordRuleEngine,
    PatternRuleEngine,
)
from src.application.services.nlp.rule_engines.base import RuleEngineResult
from src.domain.models import ClassificationResult, MessageType
from src.infrastructure.observability.logger import get_logger
from src.infrastructure.observability.metrics import get_metrics_collector
from src.shared.exceptions import MessageClassificationError


class MessageClassifier:
    """
    Orchestrator that coordinates multiple rule engines for message classification.
    """

    def __init__(self, settings: MessageClassificationSettings | None = None) -> None:
        """Initialize message classifier with enabled rule engines."""
        self._logger = get_logger(__name__)
        self._metrics = get_metrics_collector()

        if settings is None:
            from config.settings import get_settings

            app_settings: Settings = get_settings()
            settings = app_settings.message_classification

        self.settings: MessageClassificationSettings = settings
        self.rule_engines: list[BaseRuleEngine] = []

        # Load enabled rule engines with error handling
        try:
            if self.settings.keyword_engine_enabled:
                self.rule_engines.append(KeywordRuleEngine(self.settings))
                self._logger.info("KeywordRuleEngine enabled and loaded")

            if self.settings.pattern_engine_enabled:
                self.rule_engines.append(PatternRuleEngine(self.settings))
                self._logger.info("PatternRuleEngine enabled and loaded")

            self._metrics.record_gauge(
                "message_classifier_engines_loaded",
                len(self.rule_engines),
                {},
            )

        except Exception as e:
            self._logger.error("Failed to initialize rule engines", error=str(e))
            self._metrics.increment_counter(
                "message_classifier_initialization_errors_total",
                {"error_type": "engine_loading"},
            )
            raise MessageClassificationError(
                f"Failed to initialize message classifier: {str(e)}",
            ) from e

    def classify(self, message: str) -> ClassificationResult:
        """Classify a message using all enabled rule engines."""
        if not message.strip():
            self._logger.warning("Empty message provided for classification")
            self._metrics.increment_counter(
                "message_classification_errors_total",
                {"error_type": "empty_message"},
            )
            raise MessageClassificationError("Message cannot be empty")

        # Collect results from all rule engines
        all_keywords = []
        all_rule_matches = []
        max_confidence = 0.0
        request_score = 0.0
        recommendation_score = 0.0
        successful_engines = 0
        failed_engines = 0

        for engine in self.rule_engines:
            try:
                engine_result: RuleEngineResult = engine.classify(message)
                all_keywords.extend(engine_result.keywords)
                all_rule_matches.extend(engine_result.rule_matches)
                max_confidence = max(max_confidence, engine_result.confidence)

                # Infer intent from keywords to determine request vs recommendation
                if any(
                    keyword
                    in [
                        "need",
                        "help",
                        "looking",
                        "emergency",
                        "urgent",
                        "require",
                        "want",
                    ]
                    for keyword in engine_result.keywords
                ):
                    request_score = max(request_score, engine_result.confidence)
                elif any(
                    keyword
                    in [
                        "recommend",
                        "excellent",
                        "great",
                        "amazing",
                        "fantastic",
                        "brilliant",
                    ]
                    for keyword in engine_result.keywords
                ):
                    recommendation_score = max(
                        recommendation_score,
                        engine_result.confidence,
                    )

                successful_engines += 1

            except Exception as e:
                failed_engines += 1
                engine_name = type(engine).__name__
                self._logger.error(
                    "Rule engine classification failed",
                    engine=engine_name,
                    error=str(e),
                )
                self._metrics.increment_counter(
                    "message_classification_engine_errors_total",
                    {"engine": engine_name, "error_type": "classification_failed"},
                )
                # Continue with other engines

        # Record engine success/failure metrics
        self._metrics.record_gauge(
            "message_classification_engines_successful",
            successful_engines,
            {},
        )
        self._metrics.record_gauge(
            "message_classification_engines_failed",
            failed_engines,
            {},
        )

        # Determine message type based on keyword context and confidence
        message_type = self._determine_message_type(
            request_score,
            recommendation_score,
            max_confidence,
        )

        classification_result: ClassificationResult = ClassificationResult(
            message_type=message_type,
            confidence=max_confidence,
            keywords=list(set(all_keywords)),  # Remove duplicates
            rule_matches=all_rule_matches,
        )

        # Log and collect metrics
        self._logger.info(
            "Message classified",
            message_type=classification_result.message_type.value,
            confidence=classification_result.confidence,
            keyword_count=len(classification_result.keywords),
            rule_matches_count=len(classification_result.rule_matches),
            successful_engines=successful_engines,
            failed_engines=failed_engines,
        )

        self._metrics.increment_counter(
            "message_classifications_total",
            {"type": classification_result.message_type.value},
        )

        self._metrics.record_histogram(
            "message_classification_confidence",
            classification_result.confidence,
            {"type": classification_result.message_type.value},
        )

        return classification_result

    def _determine_message_type(
        self,
        request_score: float,
        recommendation_score: float,
        overall_confidence: float,
    ) -> MessageType:
        """Determine message type based on request vs recommendation signals."""
        # Use specific intent scores first
        if (
            request_score >= self.settings.request_confidence_threshold
            and request_score > recommendation_score
        ):
            return MessageType.REQUEST
        if (
            recommendation_score >= self.settings.recommendation_confidence_threshold
            and recommendation_score > request_score
        ):
            return MessageType.RECOMMENDATION
        if overall_confidence >= self.settings.request_confidence_threshold:
            # Fallback to request if we have high confidence but no clear intent signals
            return MessageType.REQUEST

        return MessageType.UNKNOWN

    def health_check(self) -> dict[str, object]:
        """Check health status of message classifier."""
        try:
            # Test with a simple message
            test_result = self.classify("test message")

            health_status = {
                "status": "healthy",
                "engines_loaded": len(self.rule_engines),
                "engines_configured": {
                    "keyword": self.settings.keyword_engine_enabled,
                    "pattern": self.settings.pattern_engine_enabled,
                },
                "test_classification": {
                    "message_type": test_result.message_type.value,
                    "confidence": test_result.confidence,
                },
            }

            self._metrics.record_gauge("message_classifier_health_status", 1, {})
            return health_status

        except Exception as e:
            self._logger.error("Message classifier health check failed", error=str(e))
            self._metrics.record_gauge("message_classifier_health_status", 0, {})
            self._metrics.increment_counter(
                "message_classifier_health_check_failures_total",
                {"error_type": "health_check_failed"},
            )

            return {
                "status": "unhealthy",
                "error": str(e),
                "engines_loaded": len(self.rule_engines),
            }
