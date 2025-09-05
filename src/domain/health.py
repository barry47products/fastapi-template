"""Domain layer health checks for application monitoring."""

from typing import Any

from src.application.services.nlp import ProviderMatcher
from src.domain.models import Endorsement, EndorsementType, Provider
from src.domain.value_objects import EndorsementID, GroupID, PhoneNumber, ProviderID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import MentionExtractionError, ProviderValidationError

TEST_PHONE_NUMBER = "+447911123456"


async def check_phone_number_validation() -> bool:
    """Health check for phone number validation functionality."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        PhoneNumber(value=TEST_PHONE_NUMBER)
        return True
    except Exception:
        return False


async def check_group_id_validation() -> bool:
    """Health check for group ID validation functionality."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        GroupID(value="447911123456-1234567890@g.us")
        return True
    except Exception:
        return False


async def check_provider_id_generation() -> bool:
    """Health check for provider ID auto-generation functionality."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        ProviderID()
        return True
    except Exception:
        return False


async def check_endorsement_id_generation() -> bool:
    """Health check for endorsement ID auto-generation functionality."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        EndorsementID()
        return True
    except Exception:
        return False


async def check_provider_model_creation() -> bool:
    """Health check for provider model creation and business logic."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        provider = Provider(
            name="Test Provider",
            phone=PhoneNumber(value=TEST_PHONE_NUMBER),
            category="Test",
        )
        provider.increment_endorsement_count()
        provider.add_tag_category("Test", ["value"])
        return True
    except Exception:
        return False


async def check_endorsement_model_creation() -> bool:
    """Health check for endorsement model creation and business logic."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        endorsement = Endorsement(
            provider_id=ProviderID(),
            endorser_phone=PhoneNumber(value=TEST_PHONE_NUMBER),
            group_id=GroupID(value="447911123456-1234567890@g.us"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Test endorsement",
        )
        endorsement.revoke()
        endorsement.restore()
        return True
    except Exception:
        return False


async def check_provider_matcher_functionality() -> bool:
    """Health check for provider matcher functionality."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        # Create test matcher
        matcher = ProviderMatcher()

        # Create test providers
        test_providers = [
            Provider(
                name="Test Electrician",
                phone=PhoneNumber(value=TEST_PHONE_NUMBER),
                category="Electrician",
                tags={"services": ["installation", "repair"]},
            ),
            Provider(
                name="Local Plumber",
                phone=PhoneNumber(value="+447911123457"),
                category="Plumber",
                tags={"availability": ["emergency", "24/7"]},
            ),
        ]

        # Test 1: Exact name matching
        result = matcher.find_best_match("Test Electrician", test_providers)
        if not result.is_match or result.match_type != "exact_name":
            return False

        # Test 2: Fuzzy phone matching
        result = matcher.find_best_match("+447911123456", test_providers)
        if not result.is_match or not result.match_type.startswith("phone"):
            return False

        # Test 3: Tag-based matching
        result = matcher.find_best_match("emergency 24/7 availability", test_providers)
        if not result.is_match or result.match_type != "tag_based":
            return False

        # Test 4: Validation error handling
        try:
            matcher.find_best_match("", test_providers)
            return False  # Should have raised ProviderValidationError
        except ProviderValidationError:
            pass  # Expected behaviour

        # Test 5: No match scenario
        result = matcher.find_best_match("unknown service", test_providers)
        if result.is_match:
            return False

        return True
    except Exception:
        return False


async def check_mention_extraction_functionality() -> bool:
    """Health check for mention extraction functionality."""
    import asyncio

    await asyncio.sleep(0.01)
    try:
        # Create test extractor
        from src.application.services import MentionExtractor

        extractor = MentionExtractor()

        # Test 1: Name pattern extraction
        test_message = "Contact Davies Electrical Services for help"
        mentions = extractor.extract_mentions(test_message)
        name_mentions = [m for m in mentions if m.extraction_type == "name_pattern"]
        if not name_mentions:
            return False

        # Test 2: Phone pattern extraction
        phone_message = "Call John on +27821234567 for electrical work"
        phone_mentions_list = extractor.extract_mentions(phone_message)
        phone_mentions = [m for m in phone_mentions_list if m.extraction_type == "phone_pattern"]
        if not phone_mentions:
            return False

        # Test 3: Service keyword extraction
        service_message = "Looking for a reliable electrician for repairs"
        service_mentions_list = extractor.extract_mentions(service_message)
        service_mentions = [
            m for m in service_mentions_list if m.extraction_type == "service_keyword"
        ]
        if not service_mentions:
            return False

        # Test 4: Location pattern extraction
        location_message = "Need a plumber in Cape Town area"
        location_mentions_list = extractor.extract_mentions(location_message)
        location_mentions = [
            m for m in location_mentions_list if m.extraction_type == "location_pattern"
        ]
        if not location_mentions:
            return False

        # Test 5: Error handling for empty messages
        try:
            extractor.extract_mentions("")
            return False  # Should have raised MentionExtractionError
        except MentionExtractionError:
            pass  # Expected behaviour

        # Test 6: Confidence filtering
        all_mentions = extractor.extract_mentions(test_message)
        for mention in all_mentions:
            if mention.confidence < extractor.settings.minimum_confidence_threshold:
                return False

        return True
    except Exception:
        return False


async def check_domain_layer_health() -> dict[str, Any]:
    """Comprehensive health check for the entire domain layer."""
    logger = get_logger(__name__)
    metrics = get_metrics_collector()
    checks = {
        "phone_number_validation": check_phone_number_validation,
        "group_id_validation": check_group_id_validation,
        "provider_id_generation": check_provider_id_generation,
        "endorsement_id_generation": check_endorsement_id_generation,
        "provider_model_creation": check_provider_model_creation,
        "endorsement_model_creation": check_endorsement_model_creation,
        "provider_matcher_functionality": check_provider_matcher_functionality,
        "mention_extraction_functionality": check_mention_extraction_functionality,
    }
    results = {}
    all_healthy = True
    try:
        for check_name, check_func in checks.items():
            result = await check_func()
            results[check_name] = result
            if not result:
                all_healthy = False
                logger.warning(f"Domain health check failed: {check_name}")
                metrics.increment_counter(
                    "domain_health_check_failures_total",
                    {"check": check_name},
                )
            else:
                metrics.increment_counter(
                    "domain_health_check_successes_total",
                    {"check": check_name},
                )
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
        logger.error(f"Domain health check error: {str(e)}")
        metrics.increment_counter(
            "domain_layer_health_checks_total",
            {"status": "error"},
        )
        return {
            "healthy": False,
            "error": str(e),
            "checks": results,
        }
