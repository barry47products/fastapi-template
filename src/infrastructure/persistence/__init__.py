"""Persistence layer infrastructure components."""

from .repositories import InMemoryProductRepository, InMemoryUserRepository
from .repository_factory import (
    configure_repository_factory,
    get_product_repository,
    get_repository_factory,
    get_user_repository,
    RepositoryFactory,
    SampleRepositoryFactory,
)

__all__ = [
    "InMemoryProductRepository",
    "InMemoryUserRepository",
    "RepositoryFactory",
    "SampleRepositoryFactory",
    "configure_repository_factory",
    "get_product_repository",
    "get_repository_factory",
    "get_user_repository",
]
