"""Interfaces for data sources - enables swapping between SQLite, API, Oracle, etc."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable
from pydantic import BaseModel, Field


# ============================================================================
# Data Transfer Objects (DTOs) - Shared across all data sources
# ============================================================================

class SupplierResult(BaseModel):
    """Supplier search result."""
    id: str
    name: str
    site: str | None = None
    total_orders: int = 0
    total_amount: float = 0.0
    avg_order_value: float = 0.0
    first_order_date: datetime | None = None
    last_order_date: datetime | None = None


class SupplierDetail(BaseModel):
    """Detailed supplier information."""
    id: str
    name: str
    site: str | None = None
    total_orders: int = 0
    total_amount: float = 0.0
    avg_order_value: float = 0.0
    first_order_date: datetime | None = None
    last_order_date: datetime | None = None
    top_categories: list["CategoryResult"] = Field(default_factory=list)
    top_items: list["ProductResult"] = Field(default_factory=list)
    rank_by_volume: int | None = None
    market_share: float = 0.0


class ProductResult(BaseModel):
    """Product/item search result."""
    item_code: str
    description: str
    category: str
    category_id: str | None = None
    uom: str = "EA"
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    supplier_count: int = 0


class ProductWithSuppliers(BaseModel):
    """Product with its suppliers and pricing."""
    item_code: str
    description: str
    category: str
    uom: str = "EA"
    suppliers: list["SupplierPricingResult"] = Field(default_factory=list)


class SupplierPricingResult(BaseModel):
    """Supplier pricing for a specific item."""
    supplier_id: str
    supplier_name: str
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    order_count: int = 0
    total_ordered_qty: float = 0.0
    last_order_date: datetime | None = None


class CategoryResult(BaseModel):
    """Category information."""
    id: str
    name: str
    level: int  # 1, 2, or 3
    level1: str | None = None
    level2: str | None = None
    level3: str | None = None
    parent: str | None = None
    item_count: int = 0
    supplier_count: int = 0
    total_amount: float = 0.0


class SupplierRankingResult(BaseModel):
    """Supplier ranking entry."""
    rank: int
    supplier_id: str
    supplier_name: str
    metric_value: float
    metric_name: str  # "total_amount", "order_count", "item_count"


class ComparisonResult(BaseModel):
    """Result of comparing multiple suppliers."""
    suppliers: list[SupplierDetail] = Field(default_factory=list)
    metrics: dict[str, dict[str, float]] = Field(default_factory=dict)
    # metrics = {"total_amount": {"Supplier A": 1000, "Supplier B": 2000}, ...}
    common_categories: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SearchCriteria(BaseModel):
    """Search criteria for suppliers."""
    name: str | None = None
    category: str | None = None
    product: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    limit: int = 10
    offset: int = 0


# ============================================================================
# Data Source Interface
# ============================================================================

@runtime_checkable
class ISupplierDataSource(Protocol):
    """
    Interface for supplier data sources.

    Implementations:
    - SQLiteDataSource: Local SQLite database (development/testing)
    - APIDataSource: REST API backend (production)
    - OracleFusionDataSource: Direct Oracle Fusion integration
    - MockDataSource: In-memory mock data (unit testing)
    """

    async def search_suppliers(
        self,
        name: str | None = None,
        category: str | None = None,
        product: str | None = None,
        limit: int = 10
    ) -> list[SupplierResult]:
        """
        Search suppliers by various criteria.

        Args:
            name: Partial supplier name to search
            category: Category name to filter by
            product: Product/item to search for
            limit: Maximum results to return

        Returns:
            List of matching suppliers
        """
        ...

    async def get_supplier_detail(self, supplier_id: str) -> SupplierDetail | None:
        """
        Get detailed information about a specific supplier.

        Args:
            supplier_id: Supplier ID or name

        Returns:
            Detailed supplier info or None if not found
        """
        ...

    async def search_products(
        self,
        query: str,
        category: str | None = None,
        limit: int = 20
    ) -> list[ProductResult]:
        """
        Search for products/items.

        Args:
            query: Search query (matches item code or description)
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of matching products
        """
        ...

    async def get_product_suppliers(
        self,
        item_code: str
    ) -> ProductWithSuppliers | None:
        """
        Get a product with all its suppliers and pricing.

        Args:
            item_code: Item code to look up

        Returns:
            Product with supplier pricing info
        """
        ...

    async def get_categories(
        self,
        parent: str | None = None,
        level: int | None = None
    ) -> list[CategoryResult]:
        """
        Get product categories.

        Args:
            parent: Parent category to get children of
            level: Specific level to return (1, 2, or 3)

        Returns:
            List of categories
        """
        ...

    async def get_top_suppliers(
        self,
        by: str = "amount",
        limit: int = 10
    ) -> list[SupplierRankingResult]:
        """
        Get top suppliers by a metric.

        Args:
            by: Metric to rank by ("amount", "orders", "items")
            limit: Number of suppliers to return

        Returns:
            Ranked list of suppliers
        """
        ...

    async def compare_suppliers(
        self,
        supplier_ids: list[str]
    ) -> ComparisonResult:
        """
        Compare multiple suppliers.

        Args:
            supplier_ids: List of supplier IDs or names to compare

        Returns:
            Comparison result with metrics and recommendations
        """
        ...

    async def get_category_suppliers(
        self,
        category: str,
        limit: int = 20
    ) -> list[SupplierResult]:
        """
        Get all suppliers for a specific category.

        Args:
            category: Category name
            limit: Maximum results

        Returns:
            List of suppliers in this category
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the data source is available.

        Returns:
            True if healthy, False otherwise
        """
        ...


# ============================================================================
# Abstract Base Class (for implementations that want inheritance)
# ============================================================================

class BaseDataSource(ABC):
    """
    Abstract base class for data source implementations.

    Provides common functionality and enforces the interface.
    """

    @abstractmethod
    async def search_suppliers(
        self,
        name: str | None = None,
        category: str | None = None,
        product: str | None = None,
        limit: int = 10
    ) -> list[SupplierResult]:
        """Search suppliers by criteria."""
        pass

    @abstractmethod
    async def get_supplier_detail(self, supplier_id: str) -> SupplierDetail | None:
        """Get detailed supplier information."""
        pass

    @abstractmethod
    async def search_products(
        self,
        query: str,
        category: str | None = None,
        limit: int = 20
    ) -> list[ProductResult]:
        """Search for products."""
        pass

    @abstractmethod
    async def get_product_suppliers(
        self,
        item_code: str
    ) -> ProductWithSuppliers | None:
        """Get product with suppliers."""
        pass

    @abstractmethod
    async def get_categories(
        self,
        parent: str | None = None,
        level: int | None = None
    ) -> list[CategoryResult]:
        """Get categories."""
        pass

    @abstractmethod
    async def get_top_suppliers(
        self,
        by: str = "amount",
        limit: int = 10
    ) -> list[SupplierRankingResult]:
        """Get top suppliers by metric."""
        pass

    @abstractmethod
    async def compare_suppliers(
        self,
        supplier_ids: list[str]
    ) -> ComparisonResult:
        """Compare suppliers."""
        pass

    @abstractmethod
    async def get_category_suppliers(
        self,
        category: str,
        limit: int = 20
    ) -> list[SupplierResult]:
        """Get suppliers for a category."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check data source health."""
        pass
