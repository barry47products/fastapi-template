"""Domain repository interfaces for clean architecture."""

from .endorsement_repository import EndorsementRepository
from .provider_repository import ProviderRepository

__all__ = [
    "ProviderRepository",
    "EndorsementRepository",
]
