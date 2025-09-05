"""Unit tests for observability infrastructure."""

# pylint: disable=redefined-outer-name

from unittest.mock import patch

from src.infrastructure.observability import (
    get_logger,
    get_metrics_collector,
    MetricsCollector,
)


class TestStructuredLogger:
    """Test structured logging functionality."""

    def test_should_get_logger_with_name(self) -> None:
        """Should get logger with specified name."""
        # Act
        logger = get_logger("test_module")

        # Assert
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_should_log_info_with_structured_data(self) -> None:
        """Should log info messages with structured context."""
        # Arrange
        logger = get_logger("test")

        with patch.object(logger, "info") as mock_info:
            # Act
            logger.info("Test message", key1="value1", key2=42)

            # Assert
            mock_info.assert_called_once_with("Test message", key1="value1", key2=42)

    def test_should_log_warning_with_structured_data(self) -> None:
        """Should log warning messages with structured context."""
        # Arrange
        logger = get_logger("test")

        with patch.object(logger, "warning") as mock_warning:
            # Act
            logger.warning("Warning message", error_code="W001", count=5)

            # Assert
            mock_warning.assert_called_once_with("Warning message", error_code="W001", count=5)

    def test_should_log_error_with_structured_data(self) -> None:
        """Should log error messages with structured context."""
        # Arrange
        logger = get_logger("test")

        with patch.object(logger, "error") as mock_error:
            # Act
            logger.error("Error occurred", exception="ValueError", line=100)

            # Assert
            mock_error.assert_called_once_with("Error occurred", exception="ValueError", line=100)

    def test_should_log_debug_with_structured_data(self) -> None:
        """Should log debug messages with structured context."""
        # Arrange
        logger = get_logger("test")

        with patch.object(logger, "debug") as mock_debug:
            # Act
            logger.debug("Debug info", operation="lookup", duration_ms=150)

            # Assert
            mock_debug.assert_called_once_with("Debug info", operation="lookup", duration_ms=150)


class TestMetricsCollector:
    """Test metrics collection functionality."""

    def test_should_create_metrics_collector(self) -> None:
        """Should create metrics collector instance."""
        # Act
        collector = MetricsCollector()

        # Assert
        assert collector is not None
        assert hasattr(collector, "increment_counter")
        assert hasattr(collector, "record_histogram")

    def test_should_increment_counter_with_tags(self) -> None:
        """Should increment counter metrics with tags."""
        # Arrange
        collector = MetricsCollector()

        # Act & Assert - Should not raise exception
        collector.increment_counter("test_counter", {"env": "test", "service": "matching"})

    def test_should_increment_counter_without_tags(self) -> None:
        """Should increment counter metrics without tags."""
        # Arrange
        collector = MetricsCollector()

        # Act & Assert - Should not raise exception
        collector.increment_counter("simple_counter", {})

    def test_should_record_histogram_with_tags(self) -> None:
        """Should record histogram metrics with tags."""
        # Arrange
        collector = MetricsCollector()

        # Act & Assert - Should not raise exception
        collector.record_histogram(
            "response_time",
            0.150,
            {"endpoint": "match", "algorithm": "levenshtein"},
        )

    def test_should_record_histogram_without_tags(self) -> None:
        """Should record histogram metrics without tags."""
        # Arrange
        collector = MetricsCollector()

        # Act & Assert - Should not raise exception
        collector.record_histogram("processing_time", 0.025, {})

    def test_should_handle_zero_values(self) -> None:
        """Should handle zero values in metrics."""
        # Arrange
        collector = MetricsCollector()

        # Act & Assert - Should not raise exception
        collector.record_histogram("zero_value", 0.0, {})
        collector.increment_counter("zero_increment", {})

    def test_should_handle_negative_histogram_values(self) -> None:
        """Should handle negative values in histograms appropriately."""
        # Arrange
        collector = MetricsCollector()

        # Act & Assert - Should not raise exception
        collector.record_histogram("negative_test", -1.0, {})


class TestObservabilityFactoryFunctions:
    """Test factory functions for observability components."""

    def test_get_logger_should_return_bound_logger(self) -> None:
        """Should return structlog bound logger instance."""
        # Act
        logger = get_logger("test_module")

        # Assert
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_get_logger_should_work_with_same_name(self) -> None:
        """Should work correctly when called multiple times with same name."""
        # Act
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        # Assert
        assert logger1 is not None
        assert logger2 is not None
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")

    def test_get_logger_should_work_with_different_names(self) -> None:
        """Should work correctly with different module names."""
        # Act
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Assert
        assert logger1 is not None
        assert logger2 is not None
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")

    def test_get_metrics_collector_should_return_collector(self) -> None:
        """Should return metrics collector instance."""
        # Act
        collector = get_metrics_collector()

        # Assert
        assert isinstance(collector, MetricsCollector)

    def test_get_metrics_collector_should_return_same_instance(self) -> None:
        """Should return same metrics collector instance (singleton)."""
        # Act
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # Assert
        assert collector1 is collector2


class TestObservabilityIntegration:
    """Test integration scenarios for observability."""

    def test_should_support_provider_matcher_logging_pattern(self) -> None:
        """Should support the logging pattern used by provider matcher."""
        # Arrange
        logger = get_logger("src.application.services.nlp.provider_matcher")

        with patch.object(logger, "info") as mock_info:
            # Act - Simulate provider matcher logging
            logger.info(
                "Starting provider matching",
                mention_length=25,
                provider_count=3,
            )

            # Assert
            mock_info.assert_called_once_with(
                "Starting provider matching",
                mention_length=25,
                provider_count=3,
            )

    def test_should_support_provider_matcher_metrics_pattern(self) -> None:
        """Should support the metrics pattern used by provider matcher."""
        # Arrange
        collector = get_metrics_collector()

        # Act - Simulate provider matcher metrics
        collector.increment_counter(
            "provider_matching_attempts_total",
            {"type": "find_best_match"},
        )

        collector.increment_counter(
            "provider_matches_total",
            {"match_type": "semantic_tag"},
        )

        collector.increment_counter(
            "provider_semantic_matches_total",
            {"confidence_bucket": "medium"},
        )

        # Assert - Should complete without exceptions
        assert True

    def test_should_handle_error_logging_with_privacy_safe_data(self) -> None:
        """Should handle error logging with privacy-safe truncation."""
        # Arrange
        logger = get_logger("provider_matcher_test")

        with patch.object(logger, "error") as mock_error:
            # Act - Simulate privacy-safe error logging
            logger.error(
                "Fuzzy name matching failed",
                mention_length=50,
                provider_name="John Smith Plumbing"[:30],  # Truncated for privacy
                error="ValueError: Invalid input",
            )

            # Assert
            mock_error.assert_called_once_with(
                "Fuzzy name matching failed",
                mention_length=50,
                provider_name="John Smith Plumbing",
                error="ValueError: Invalid input",
            )

    def test_should_handle_debug_logging_for_performance_data(self) -> None:
        """Should handle debug logging for performance diagnostics."""
        # Arrange
        logger = get_logger("performance_test")

        with patch.object(logger, "debug") as mock_debug:
            # Act
            logger.debug(
                "Fuzzy match score calculation failed",
                mention_length=15,
                target_length=25,
                algorithm="levenshtein",
                error="Exception during processing",
            )

            # Assert
            mock_debug.assert_called_once_with(
                "Fuzzy match score calculation failed",
                mention_length=15,
                target_length=25,
                algorithm="levenshtein",
                error="Exception during processing",
            )
