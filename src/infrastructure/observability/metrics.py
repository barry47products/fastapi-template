"""Metrics collection system using Prometheus client."""

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server


class _MetricsCollectorSingleton:
    """Singleton holder for the metrics collector."""

    _instance: Optional["MetricsCollector"] = None

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        """Get or create the singleton metrics collector instance."""
        if cls._instance is None:
            cls._instance = MetricsCollector()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "MetricsCollector") -> None:
        """Set the singleton metrics collector instance."""
        cls._instance = instance


class MetricsCollector:
    """Prometheus-based metrics collector."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize metrics collector.

        Args:
            registry: Prometheus registry to use, defaults to default registry
        """
        self.registry = registry or CollectorRegistry()
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def increment_counter(
        self,
        name: str,
        labels: dict[str, str],
        value: float = 1.0,
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name
            labels: Label key-value pairs
            value: Value to increment by (default 1.0)
        """
        if name not in self._counters:
            self._counters[name] = Counter(
                name,
                f"Counter metric: {name}",
                list(labels.keys()),
                registry=self.registry,
            )

        # Handle case where no labels are needed
        if labels:
            self._counters[name].labels(**labels).inc(value)
        else:
            self._counters[name].inc(value)

    def record_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Record a gauge metric value.

        Args:
            name: Gauge name
            value: Value to set
            labels: Label key-value pairs
        """
        if name not in self._gauges:
            label_names = list(labels.keys()) if labels else []
            self._gauges[name] = Gauge(
                name,
                f"Gauge metric: {name}",
                label_names,
                registry=self.registry,
            )

        if labels:
            self._gauges[name].labels(**labels).set(value)
        else:
            self._gauges[name].set(value)

    def record_histogram(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Record a histogram observation.

        Args:
            name: Histogram name
            value: Value to observe
            labels: Label key-value pairs
        """
        if name not in self._histograms:
            label_names = list(labels.keys()) if labels else []
            self._histograms[name] = Histogram(
                name,
                f"Histogram metric: {name}",
                label_names,
                registry=self.registry,
            )

        if labels:
            self._histograms[name].labels(**labels).observe(value)
        else:
            self._histograms[name].observe(value)

    @contextmanager
    def time_function(self, name: str, labels: dict[str, str]) -> Generator[None]:
        """Context manager to time function execution.

        Args:
            name: Histogram name for timing
            labels: Label key-value pairs
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram(name, duration, labels)

    def get_counter_value(self, name: str, labels: dict[str, str]) -> float:
        """Get counter value for testing using proper Prometheus API.

        Args:
            name: Counter name
            labels: Label key-value pairs

        Returns:
            Counter value
        """
        if name not in self._counters:
            return 0.0
        # Use proper collection method instead of accessing private attributes
        for metric_family in self._counters[name].collect():
            for sample in metric_family.samples:
                if sample.labels == labels:
                    return float(sample.value)
        return 0.0

    def get_gauge_value(self, name: str, labels: dict[str, str]) -> float:
        """Get gauge value for testing using proper Prometheus API.

        Args:
            name: Gauge name
            labels: Label key-value pairs

        Returns:
            Gauge value
        """
        if name not in self._gauges:
            return 0.0
        # Use proper collection method instead of accessing private attributes
        for metric_family in self._gauges[name].collect():
            for sample in metric_family.samples:
                if sample.labels == labels:
                    return float(sample.value)
        return 0.0

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics data in dictionary format.

        Returns:
            Dictionary containing all metrics data
        """
        metrics_data = {}

        # Add counter data
        for name in self._counters:
            metrics_data[f"counter_{name}"] = {"type": "counter", "name": name}

        # Add gauge data
        for name in self._gauges:
            metrics_data[f"gauge_{name}"] = {"type": "gauge", "name": name}

        # Add histogram data
        for name in self._histograms:
            metrics_data[f"histogram_{name}"] = {"type": "histogram", "name": name}

        return metrics_data


def configure_metrics(enabled: bool, port: int) -> None:
    """Configure metrics collection system.

    This function is kept for backward compatibility during initialization.
    With dependency injection, configuration is handled via get_metrics_collector().

    Args:
        enabled: Whether metrics collection is enabled
        port: Port to serve metrics on
    """
    # For backward compatibility, set the singleton instance
    collector = MetricsCollector()
    _MetricsCollectorSingleton.set_instance(collector)

    if enabled:
        start_http_server(port)


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance via singleton fallback.

    Returns:
        Metrics collector instance
    """
    # Fallback to singleton for backward compatibility during transition
    return _MetricsCollectorSingleton.get_instance()
