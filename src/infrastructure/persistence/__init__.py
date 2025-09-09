"""Persistence layer infrastructure components."""

from .repositories import InMemoryProductRepository, InMemoryUserRepository
from .repository_provider import (
    RepositoryProvider,
    configure_repository_provider,
    get_product_repository,
    get_repository_provider,
    get_user_repository,
)

__all__ = [
    "InMemoryProductRepository",
    "InMemoryUserRepository",
    "RepositoryProvider",
    "configure_repository_provider",
    "get_product_repository",
    "get_repository_provider",
    "get_user_repository",
]
