"""WhatsApp integration infrastructure."""

from src.infrastructure.service_registry import get_service_registry
from src.infrastructure.whatsapp.green_api_client import GreenAPIClient

__all__ = [
    "GreenAPIClient",
    "get_green_api_client",
]


def get_green_api_client() -> GreenAPIClient:
    """
    Get GREEN-API client from service registry.

    Returns:
        Configured GREEN-API client instance

    Raises:
        ServiceNotConfiguredException: If client not registered
    """
    service_registry = get_service_registry()
    return service_registry.get_green_api_client()
