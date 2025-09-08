"""Unit tests for metrics observability component."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry

from src.infrastructure.observability.metrics import (
    MetricsCollector,
    _MetricsCollectorSingleton,
    configure_metrics,
    get_metrics_collector,
)


class TestMetricsCollectorSingleton:
    """Test metrics collector singleton behavior."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _MetricsCollectorSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _MetricsCollectorSingleton._instance = None

    def test_creates_instance_when_none_exists(self) -> None:
        """Creates instance when none exists."""
        collector = _MetricsCollectorSingleton.get_instance()

        assert isinstance(collector, MetricsCollector)
        assert _MetricsCollectorSingleton._instance is collector

    def test_returns_existing_instance(self) -> None:
        """Returns existing instance if one exists."""
        first_collector = _MetricsCollectorSingleton.get_instance()
        second_collector = _MetricsCollectorSingleton.get_instance()

        assert first_collector is second_collector

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        custom_collector = MetricsCollector()

        _MetricsCollectorSingleton.set_instance(custom_collector)

        assert _MetricsCollectorSingleton._instance is custom_collector
        assert _MetricsCollectorSingleton.get_instance() is custom_collector


class TestMetricsCollector:
    """Test metrics collector behavior."""

    def test_creates_collector_with_default_registry(self) -> None:
        """Creates collector with default registry."""
        collector = MetricsCollector()

        assert collector.registry is not None
        assert collector._counters == {}
        assert collector._gauges == {}
        assert collector._histograms == {}

    def test_creates_collector_with_custom_registry(self) -> None:
        """Creates collector with custom registry."""
        custom_registry = CollectorRegistry()
        collector = MetricsCollector(registry=custom_registry)

        assert collector.registry is custom_registry

    def test_increments_counter_with_labels(self) -> None:
        """Increments counter with labels."""
        collector = MetricsCollector()
        labels = {"service": "api", "endpoint": "users"}

        collector.increment_counter("requests_total", labels)

        assert "requests_total" in collector._counters
        # Verify counter was created with correct label names
        counter = collector._counters["requests_total"]
        assert counter._name == "requests"  # Prometheus client strips _total suffix

    def test_increments_counter_without_labels(self) -> None:
        """Increments counter without labels."""
        collector = MetricsCollector()

        collector.increment_counter("simple_counter", {})

        assert "simple_counter" in collector._counters

    def test_increments_counter_with_custom_value(self) -> None:
        """Increments counter with custom value."""
        collector = MetricsCollector()

        collector.increment_counter("batch_counter", {}, value=5.0)

        assert "batch_counter" in collector._counters

    def test_records_gauge_with_labels(self) -> None:
        """Records gauge with labels."""
        collector = MetricsCollector()
        labels = {"instance": "server1", "region": "us-east"}

        collector.record_gauge("cpu_usage", 75.5, labels)

        assert "cpu_usage" in collector._gauges
        gauge = collector._gauges["cpu_usage"]
        assert gauge._name == "cpu_usage"

    def test_records_gauge_without_labels(self) -> None:
        """Records gauge without labels."""
        collector = MetricsCollector()

        collector.record_gauge("memory_usage", 1024.0, {})

        assert "memory_usage" in collector._gauges

    def test_records_histogram_with_labels(self) -> None:
        """Records histogram with labels."""
        collector = MetricsCollector()
        labels = {"method": "GET", "status": "200"}

        collector.record_histogram("request_duration", 0.150, labels)

        assert "request_duration" in collector._histograms
        histogram = collector._histograms["request_duration"]
        assert histogram._name == "request_duration"

    def test_records_histogram_without_labels(self) -> None:
        """Records histogram without labels."""
        collector = MetricsCollector()

        collector.record_histogram("processing_time", 0.025, {})

        assert "processing_time" in collector._histograms

    def test_reuses_existing_counter(self) -> None:
        """Reuses existing counter for same name."""
        collector = MetricsCollector()
        labels = {"service": "api"}

        collector.increment_counter("test_counter", labels)
        first_counter = collector._counters["test_counter"]

        collector.increment_counter("test_counter", labels)
        second_counter = collector._counters["test_counter"]

        assert first_counter is second_counter

    def test_reuses_existing_gauge(self) -> None:
        """Reuses existing gauge for same name."""
        collector = MetricsCollector()
        labels = {"instance": "server1"}

        collector.record_gauge("test_gauge", 10.0, labels)
        first_gauge = collector._gauges["test_gauge"]

        collector.record_gauge("test_gauge", 20.0, labels)
        second_gauge = collector._gauges["test_gauge"]

        assert first_gauge is second_gauge

    def test_reuses_existing_histogram(self) -> None:
        """Reuses existing histogram for same name."""
        collector = MetricsCollector()
        labels = {"endpoint": "api"}

        collector.record_histogram("test_histogram", 1.0, labels)
        first_histogram = collector._histograms["test_histogram"]

        collector.record_histogram("test_histogram", 2.0, labels)
        second_histogram = collector._histograms["test_histogram"]

        assert first_histogram is second_histogram

    def test_time_function_context_manager(self) -> None:
        """Time function context manager works correctly."""
        collector = MetricsCollector()
        labels = {"function": "test_func"}

        with collector.time_function("function_duration", labels):
            time.sleep(0.01)  # Small delay to measure

        # Should have created histogram
        assert "function_duration" in collector._histograms

    def test_time_function_records_time_on_exception(self) -> None:
        """Time function records time even when exception occurs."""
        collector = MetricsCollector()
        labels = {"function": "failing_func"}

        with (
            pytest.raises(ValueError, match="Test exception"),
            collector.time_function("exception_duration", labels),
        ):
            raise ValueError("Test exception")

        # Should still have recorded the timing
        assert "exception_duration" in collector._histograms

    def test_get_counter_value_returns_zero_for_nonexistent(self) -> None:
        """Get counter value returns zero for non-existent counter."""
        collector = MetricsCollector()

        value = collector.get_counter_value("nonexistent", {})

        assert value == 0.0

    def test_get_counter_value_returns_correct_value(self) -> None:
        """Get counter value returns correct value."""
        collector = MetricsCollector()
        labels = {"test": "value"}

        collector.increment_counter("test_counter", labels, value=5.0)

        value = collector.get_counter_value("test_counter", labels)
        assert value == 5.0

    def test_get_gauge_value_returns_zero_for_nonexistent(self) -> None:
        """Get gauge value returns zero for non-existent gauge."""
        collector = MetricsCollector()

        value = collector.get_gauge_value("nonexistent", {})

        assert value == 0.0

    def test_get_gauge_value_returns_correct_value(self) -> None:
        """Get gauge value returns correct value."""
        collector = MetricsCollector()
        labels = {"test": "gauge"}

        collector.record_gauge("test_gauge", 42.5, labels)

        value = collector.get_gauge_value("test_gauge", labels)
        assert value == 42.5

    def test_get_all_metrics_returns_empty_dict_initially(self) -> None:
        """Get all metrics returns empty dict initially."""
        collector = MetricsCollector()

        metrics = collector.get_all_metrics()

        assert metrics == {}

    def test_get_all_metrics_includes_all_metric_types(self) -> None:
        """Get all metrics includes all metric types."""
        collector = MetricsCollector()

        collector.increment_counter("test_counter", {})
        collector.record_gauge("test_gauge", 10.0, {})
        collector.record_histogram("test_histogram", 1.0, {})

        metrics = collector.get_all_metrics()

        assert "counter_test_counter" in metrics
        assert "gauge_test_gauge" in metrics
        assert "histogram_test_histogram" in metrics

        assert metrics["counter_test_counter"]["type"] == "counter"
        assert metrics["gauge_test_gauge"]["type"] == "gauge"
        assert metrics["histogram_test_histogram"]["type"] == "histogram"

    def test_handles_zero_counter_increment(self) -> None:
        """Handles zero counter increment."""
        collector = MetricsCollector()

        collector.increment_counter("zero_counter", {}, value=0.0)

        assert "zero_counter" in collector._counters

    def test_handles_negative_histogram_values(self) -> None:
        """Handles negative histogram values."""
        collector = MetricsCollector()

        # Should not raise exception - Prometheus allows negative observations
        collector.record_histogram("negative_histogram", -1.0, {})

        assert "negative_histogram" in collector._histograms

    def test_handles_large_values(self) -> None:
        """Handles large metric values."""
        collector = MetricsCollector()

        large_value = 1e6
        collector.increment_counter("large_counter", {}, value=large_value)
        collector.record_gauge("large_gauge", large_value, {})
        collector.record_histogram("large_histogram", large_value, {})

        assert "large_counter" in collector._counters
        assert "large_gauge" in collector._gauges
        assert "large_histogram" in collector._histograms

    def test_handles_empty_label_keys(self) -> None:
        """Handles empty label keys properly."""
        collector = MetricsCollector()

        # Should work with empty labels
        collector.increment_counter("no_labels_counter", {})
        collector.record_gauge("no_labels_gauge", 5.0, {})
        collector.record_histogram("no_labels_histogram", 1.5, {})

        assert "no_labels_counter" in collector._counters
        assert "no_labels_gauge" in collector._gauges
        assert "no_labels_histogram" in collector._histograms


class TestConfigureMetrics:
    """Test metrics configuration function."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _MetricsCollectorSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _MetricsCollectorSingleton._instance = None

    def test_sets_singleton_instance_for_backward_compatibility(self) -> None:
        """Sets singleton instance for backward compatibility."""
        configure_metrics(enabled=False, port=9090)

        collector = _MetricsCollectorSingleton.get_instance()
        assert isinstance(collector, MetricsCollector)

    def test_creates_new_collector_each_call(self) -> None:
        """Creates new collector each time configure is called."""
        configure_metrics(enabled=False, port=9090)
        collector1 = _MetricsCollectorSingleton.get_instance()

        configure_metrics(enabled=False, port=9090)
        collector2 = _MetricsCollectorSingleton.get_instance()

        assert collector1 is not collector2

    def test_configures_collector_without_errors(self) -> None:
        """Configures metrics collector without errors."""
        # Should not raise exception
        configure_metrics(enabled=False, port=9090)

        # Should set singleton
        collector = _MetricsCollectorSingleton.get_instance()
        assert isinstance(collector, MetricsCollector)

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        configure_metrics(enabled=False, port=9090)

        collector = _MetricsCollectorSingleton.get_instance()
        assert isinstance(collector, MetricsCollector)

    @patch("src.infrastructure.observability.metrics.start_http_server")
    def test_starts_http_server_when_enabled(self, mock_start_server: MagicMock) -> None:
        """Starts HTTP server when metrics enabled."""
        configure_metrics(enabled=True, port=8080)

        mock_start_server.assert_called_once_with(8080)

    @patch("src.infrastructure.observability.metrics.start_http_server")
    def test_does_not_start_http_server_when_disabled(self, mock_start_server: MagicMock) -> None:
        """Does not start HTTP server when metrics disabled."""
        configure_metrics(enabled=False, port=8080)

        mock_start_server.assert_not_called()

    @patch("src.infrastructure.observability.metrics.start_http_server")
    def test_uses_correct_port(self, mock_start_server: MagicMock) -> None:
        """Uses correct port for metrics server."""
        configure_metrics(enabled=True, port=9999)

        mock_start_server.assert_called_once_with(9999)


class TestGetMetricsCollector:
    """Test get metrics collector function."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _MetricsCollectorSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _MetricsCollectorSingleton._instance = None

    def test_returns_singleton_instance_when_configured(self) -> None:
        """Returns singleton instance when configured."""
        # Configure metrics first
        configure_metrics(enabled=False, port=9090)

        result = get_metrics_collector()

        assert isinstance(result, MetricsCollector)

    def test_creates_singleton_if_not_exists(self) -> None:
        """Creates singleton instance if not exists."""
        result = get_metrics_collector()

        # Should create singleton instance
        assert isinstance(result, MetricsCollector)

    def test_returns_same_singleton_instance(self) -> None:
        """Returns same singleton instance on multiple calls."""
        result1 = get_metrics_collector()
        result2 = get_metrics_collector()

        assert result1 is result2

    def test_returns_configured_instance(self) -> None:
        """Returns the configured metrics collector instance."""
        # Configure with specific instance
        configure_metrics(enabled=False, port=9090)
        configured_collector = _MetricsCollectorSingleton.get_instance()

        # Get should return the same configured instance
        result = get_metrics_collector()

        assert result is configured_collector
