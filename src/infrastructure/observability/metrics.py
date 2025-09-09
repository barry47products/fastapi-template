"""Metrics collection system using Prometheus client."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server

if TYPE_CHECKING:
    from collections.abc import Generator


class _MetricsCollectorSingleton:
    """Singleton holder for the metrics collector."""

    _instance: MetricsCollector | None = None

    @classmethod
    def get_instance(cls) -> MetricsCollector:
        """Get or create the singleton metrics collector instance."""
        if cls._instance is None:
            cls._instance = MetricsCollector()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: MetricsCollector) -> None:
        """Set the singleton metrics collector instance."""
        cls._instance = instance


class MetricsCollector:
    """Prometheus-based metrics collector with semantic naming."""

    def __init__(
        self, registry: CollectorRegistry | None = None, application_name: str = "fastapi_template"
    ) -> None:
        """Initialize metrics collector.

        Args:
            registry: Prometheus registry to use, defaults to default registry
            application_name: Application name for metric namespace
        """
        self.registry = registry or CollectorRegistry()
        self.application_name = application_name
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def _get_metric_name(self, name: str) -> str:
        """Get fully qualified metric name with application namespace.

        Args:
            name: Base metric name

        Returns:
            Namespaced metric name
        """
        if name.startswith(f"{self.application_name}_"):
            return name
        return f"{self.application_name}_{name}"

    def _get_base_labels(self, labels: dict[str, str]) -> dict[str, str]:
        """Add standard labels to all metrics.

        Args:
            labels: User-provided labels

        Returns:
            Labels with standard application context
        """
        base_labels = {
            "service": self.application_name,
            "component": "api",
        }
        base_labels.update(labels)
        return base_labels

    def increment_counter(
        self,
        name: str,
        labels: dict[str, str] | None = None,
        value: float = 1.0,
    ) -> None:
        """Increment a counter metric with semantic naming.

        Args:
            name: Counter name (will be prefixed with application namespace)
            labels: Label key-value pairs (will include standard labels)
            value: Value to increment by (default 1.0)
        """
        if labels is None:
            labels = {}

        qualified_name = self._get_metric_name(name)
        enhanced_labels = self._get_base_labels(labels)

        if qualified_name not in self._counters:
            self._counters[qualified_name] = Counter(
                qualified_name,
                f"Counter metric: {name}",
                list(enhanced_labels.keys()),
                registry=self.registry,
            )

        # Always use labels since we have base labels
        self._counters[qualified_name].labels(**enhanced_labels).inc(value)

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a gauge metric value with semantic naming.

        Args:
            name: Gauge name (will be prefixed with application namespace)
            value: Value to set
            labels: Label key-value pairs (will include standard labels)
        """
        if labels is None:
            labels = {}

        qualified_name = self._get_metric_name(name)
        enhanced_labels = self._get_base_labels(labels)

        if qualified_name not in self._gauges:
            self._gauges[qualified_name] = Gauge(
                qualified_name,
                f"Gauge metric: {name}",
                list(enhanced_labels.keys()),
                registry=self.registry,
            )

        # Always use labels since we have base labels
        self._gauges[qualified_name].labels(**enhanced_labels).set(value)

    def record_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a histogram observation with semantic naming.

        Args:
            name: Histogram name (will be prefixed with application namespace)
            value: Value to observe
            labels: Label key-value pairs (will include standard labels)
        """
        if labels is None:
            labels = {}

        qualified_name = self._get_metric_name(name)
        enhanced_labels = self._get_base_labels(labels)

        if qualified_name not in self._histograms:
            self._histograms[qualified_name] = Histogram(
                qualified_name,
                f"Histogram metric: {name}",
                list(enhanced_labels.keys()),
                registry=self.registry,
            )

        # Always use labels since we have base labels
        self._histograms[qualified_name].labels(**enhanced_labels).observe(value)

    @contextmanager
    def time_function(self, name: str, labels: dict[str, str] | None = None) -> Generator[None]:
        """Context manager to time function execution with semantic naming.

        Args:
            name: Histogram name for timing (will be prefixed with application namespace)
            labels: Label key-value pairs (will include standard labels)
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram(name, duration, labels)

    def get_counter_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get counter value for testing using proper Prometheus API.

        Args:
            name: Counter name (without namespace prefix)
            labels: Label key-value pairs (without base labels)

        Returns:
            Counter value
        """
        if labels is None:
            labels = {}

        qualified_name = self._get_metric_name(name)
        enhanced_labels = self._get_base_labels(labels)

        if qualified_name not in self._counters:
            return 0.0
        # Use proper collection method instead of accessing private attributes
        for metric_family in self._counters[qualified_name].collect():
            for sample in metric_family.samples:
                if sample.labels == enhanced_labels:
                    return float(sample.value)
        return 0.0

    def get_gauge_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get gauge value for testing using proper Prometheus API.

        Args:
            name: Gauge name (without namespace prefix)
            labels: Label key-value pairs (without base labels)

        Returns:
            Gauge value
        """
        if labels is None:
            labels = {}

        qualified_name = self._get_metric_name(name)
        enhanced_labels = self._get_base_labels(labels)

        if qualified_name not in self._gauges:
            return 0.0
        # Use proper collection method instead of accessing private attributes
        for metric_family in self._gauges[qualified_name].collect():
            for sample in metric_family.samples:
                if sample.labels == enhanced_labels:
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
    # Get application name from settings
    try:
        from config.settings import get_settings

        settings = get_settings()
        app_name = settings.app_name.replace("-", "_").replace(" ", "_").lower()
    except Exception:
        app_name = "fastapi_template"

    # For backward compatibility, set the singleton instance
    collector = MetricsCollector(application_name=app_name)
    _MetricsCollectorSingleton.set_instance(collector)

    if enabled:
        start_http_server(port)


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance via singleton fallback.

    Returns:
        Metrics collector instance with application namespace
    """
    # Try to get existing instance using the public method
    try:
        return _MetricsCollectorSingleton.get_instance()
    except Exception:
        # Create new instance with application name if singleton fails
        try:
            from config.settings import get_settings

            settings = get_settings()
            app_name = settings.app_name.replace("-", "_").replace(" ", "_").lower()
        except Exception:
            app_name = "fastapi_template"

        collector = MetricsCollector(application_name=app_name)
        _MetricsCollectorSingleton.set_instance(collector)
        return collector
