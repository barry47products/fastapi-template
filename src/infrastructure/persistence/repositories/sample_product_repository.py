"""Sample in-memory implementation of Product repository for template demonstration."""

from datetime import datetime
from typing import Any

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import RepositoryException


class InMemoryProductRepository:
    """
    In-memory implementation of Product repository for template demonstration.

    This implementation demonstrates repository patterns for product-like entities
    without external dependencies. Shows filtering, searching, and CRUD patterns
    that would be common in e-commerce or catalog applications.
    """

    def __init__(self) -> None:
        """Initialize repository with in-memory storage."""
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self._storage: dict[str, dict[str, Any]] = {}

    def save(self, product_data: dict[str, Any]) -> None:
        """Save or update a product."""
        try:
            product_id = product_data.get("id")
            if not product_id:
                raise RepositoryException("Product ID is required")

            self._storage[product_id] = product_data.copy()

            self.metrics.increment_counter("product_saves_total", {})
            self.logger.info("Product saved successfully", product_id=product_id)

        except Exception as e:
            self.metrics.increment_counter("product_save_errors_total", {})
            self.logger.error(
                "Failed to save product",
                product_id=product_data.get("id"),
                error=str(e),
            )
            raise RepositoryException(f"Failed to save product: {e}") from e

    def find_by_id(self, product_id: str) -> dict[str, Any] | None:
        """Find a product by ID."""
        try:
            product_data = self._storage.get(product_id)
            if product_data is None:
                self.logger.debug("Product not found", product_id=product_id)
                return None

            self.metrics.increment_counter("product_finds_total", {})
            return product_data.copy()

        except Exception as e:
            self.metrics.increment_counter("product_find_errors_total", {})
            self.logger.error(
                "Failed to find product by ID",
                product_id=product_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find product: {e}") from e

    def find_by_category(self, category: str) -> list[dict[str, Any]]:
        """Find products by category."""
        try:
            products = []
            for product_data in self._storage.values():
                if product_data.get("category") == category:
                    products.append(product_data.copy())

            self.metrics.increment_counter("product_category_searches_total", {})
            self.logger.debug(
                "Found products by category",
                category=category,
                count=len(products),
            )
            return products

        except Exception as e:
            self.metrics.increment_counter("product_category_search_errors_total", {})
            self.logger.error(
                "Failed to find products by category",
                category=category,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find products by category: {e}") from e

    def find_by_price_range(
        self,
        min_price: float,
        max_price: float,
    ) -> list[dict[str, Any]]:
        """Find products within price range."""
        try:
            products = []
            for product_data in self._storage.values():
                price = product_data.get("price", 0)
                if min_price <= price <= max_price:
                    products.append(product_data.copy())

            self.metrics.increment_counter("product_price_searches_total", {})
            self.logger.debug(
                "Found products by price range",
                min_price=min_price,
                max_price=max_price,
                count=len(products),
            )
            return products

        except Exception as e:
            self.metrics.increment_counter("product_price_search_errors_total", {})
            self.logger.error(
                "Failed to find products by price range",
                min_price=min_price,
                max_price=max_price,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find products by price: {e}") from e

    def find_in_stock(self) -> list[dict[str, Any]]:
        """Find products that are in stock."""
        try:
            products = []
            for product_data in self._storage.values():
                if product_data.get("in_stock", False):
                    products.append(product_data.copy())

            self.metrics.increment_counter("product_stock_searches_total", {})
            self.logger.debug("Found in-stock products", count=len(products))
            return products

        except Exception as e:
            self.metrics.increment_counter("product_stock_search_errors_total", {})
            self.logger.error("Failed to find in-stock products", error=str(e))
            raise RepositoryException(f"Failed to find in-stock products: {e}") from e

    def search_by_name(self, name_pattern: str) -> list[dict[str, Any]]:
        """Search products by name pattern (case-insensitive)."""
        try:
            products = []
            pattern_lower = name_pattern.lower()

            for product_data in self._storage.values():
                name = product_data.get("name", "").lower()
                if pattern_lower in name:
                    products.append(product_data.copy())

            self.metrics.increment_counter("product_name_searches_total", {})
            self.logger.debug(
                "Found products by name pattern",
                pattern=name_pattern,
                count=len(products),
            )
            return products

        except Exception as e:
            self.metrics.increment_counter("product_name_search_errors_total", {})
            self.logger.error(
                "Failed to search products by name",
                pattern=name_pattern,
                error=str(e),
            )
            raise RepositoryException(f"Failed to search products by name: {e}") from e

    def exists(self, product_id: str) -> bool:
        """Check if a product exists."""
        try:
            exists = product_id in self._storage
            self.metrics.increment_counter("product_exists_checks_total", {})
            return exists

        except Exception as e:
            self.metrics.increment_counter("product_exists_check_errors_total", {})
            self.logger.error(
                "Failed to check product existence",
                product_id=product_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to check product existence: {e}") from e

    def delete(self, product_id: str) -> None:
        """Delete a product by ID."""
        try:
            if product_id in self._storage:
                del self._storage[product_id]
                self.metrics.increment_counter("product_deletes_total", {})
                self.logger.info("Product deleted successfully", product_id=product_id)
            else:
                raise RepositoryException(f"Product not found: {product_id}")

        except Exception as e:
            self.metrics.increment_counter("product_delete_errors_total", {})
            self.logger.error(
                "Failed to delete product",
                product_id=product_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to delete product: {e}") from e

    def count(self) -> int:
        """Get total number of products."""
        try:
            count = len(self._storage)
            self.metrics.increment_counter("product_counts_total", {})
            self.logger.debug("Product count retrieved", count=count)
            return count

        except Exception as e:
            self.metrics.increment_counter("product_count_errors_total", {})
            self.logger.error("Failed to count products", error=str(e))
            raise RepositoryException(f"Failed to count products: {e}") from e

    def count_by_category(self, category: str) -> int:
        """Get number of products in a category."""
        try:
            count = sum(
                1
                for product_data in self._storage.values()
                if product_data.get("category") == category
            )
            self.metrics.increment_counter("product_category_counts_total", {})
            self.logger.debug(
                "Product category count retrieved",
                category=category,
                count=count,
            )
            return count

        except Exception as e:
            self.metrics.increment_counter("product_category_count_errors_total", {})
            self.logger.error(
                "Failed to count products by category",
                category=category,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to count products by category: {e}",
            ) from e

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """List all products with optional limit."""
        try:
            all_data = list(self._storage.values())
            if limit:
                all_data = all_data[:limit]

            products = [data.copy() for data in all_data]
            self.metrics.increment_counter("product_list_all_total", {})
            self.logger.debug("Listed all products", count=len(products))
            return products

        except Exception as e:
            self.metrics.increment_counter("product_list_errors_total", {})
            self.logger.error("Failed to list products", error=str(e))
            raise RepositoryException(f"Failed to list products: {e}") from e