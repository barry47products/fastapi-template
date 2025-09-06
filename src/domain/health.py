"""
Domain layer health checks for application monitoring.

This module provides sample health checks that validate domain functionality.
Replace these with health checks specific to your business domain.

Health checks should validate:
- Domain model creation and validation
- Business rule enforcement
- Value object functionality
- Domain service operations
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

from src.infrastructure.observability import get_logger, get_metrics_collector


async def check_sample_domain_functionality() -> bool:
    """
    Sample health check for domain functionality.

    Replace this with health checks for your actual domain models
    and business rules.

    Example checks might include:
    - Creating domain entities with valid data
    - Validating business rules
    - Testing value object constraints
    - Verifying domain service operations
    """
    # Simulate some domain validation work
    await asyncio.sleep(0.01)

    try:
        # Example: Test that we can create and validate timestamps
        current_time = datetime.now(UTC)
        if not isinstance(current_time, datetime):
            return False

        # Example: Test basic data validation
        sample_data = {"name": "test", "value": 42}
        name_value = sample_data.get("name")
        numeric_value = sample_data.get("value", 0)

        # Ensure we have proper types for comparison
        if not name_value or not isinstance(numeric_value, int | float):
            return False

        return numeric_value >= 0

    except Exception:
        return False


async def check_value_object_validation() -> bool:
    """
    Sample health check for value object functionality.

    Replace this with checks for your actual value objects.
    """
    await asyncio.sleep(0.01)

    try:
        # Example value object validation
        # In a real application, you might check Email, Money, Address, etc.

        # Sample validation logic
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        test_email = "test@example.com"

        return bool(re.match(email_pattern, test_email))

    except Exception:
        return False


def _validate_user_age(age: int) -> bool:
    """Helper function for user age validation business rule."""
    return 13 <= age <= 120


async def check_business_rules() -> bool:
    """
    Sample health check for business rule validation.

    Replace this with checks for your actual business rules.
    """
    await asyncio.sleep(0.01)

    try:
        # Test valid ages
        if not _validate_user_age(25) or not _validate_user_age(65):
            return False

        # Test invalid ages
        return not (_validate_user_age(5) or _validate_user_age(150))

    except Exception:
        return False


async def check_domain_layer_health() -> dict[str, Any]:
    """
    Comprehensive health check for the domain layer.

    This function runs all domain health checks and returns a summary.
    Add your own domain-specific health checks here.
    """
    logger = get_logger(__name__)
    metrics = get_metrics_collector()

    # Define health checks - replace with your domain-specific checks
    checks = {
        "sample_domain_functionality": check_sample_domain_functionality,
        "value_object_validation": check_value_object_validation,
        "business_rules": check_business_rules,
    }

    results = {}
    all_healthy = True

    try:
        # Run all health checks
        for check_name, check_func in checks.items():
            result = await check_func()
            results[check_name] = result

            if not result:
                all_healthy = False
                logger.warning("Domain health check failed", check=check_name)
                metrics.increment_counter(
                    "domain_health_check_failures_total",
                    {"check": check_name},
                )
            else:
                metrics.increment_counter(
                    "domain_health_check_successes_total",
                    {"check": check_name},
                )

        # Log overall status
        if all_healthy:
            logger.debug("All domain health checks passed")
            metrics.increment_counter(
                "domain_layer_health_checks_total",
                {"status": "healthy"},
            )
        else:
            logger.warning("Some domain health checks failed")
            metrics.increment_counter(
                "domain_layer_health_checks_total",
                {"status": "unhealthy"},
            )

        return {
            "healthy": all_healthy,
            "checks": results,
        }

    except Exception as e:
        logger.error("Domain health check error", error=str(e))
        metrics.increment_counter(
            "domain_layer_health_checks_total",
            {"status": "error"},
        )
        return {
            "healthy": False,
            "error": str(e),
            "checks": results,
        }
