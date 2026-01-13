"""Supplier domain state extension.

This module defines the supplier-specific state that extends CoreState.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from ...core.domain.base import DomainStateExtension


class Certification(BaseModel):
    """Certification information for a supplier."""

    type: str  # nadcap, as9100, itar, iso
    scope: str | None = None
    expiry_date: datetime | None = None
    status: str = "active"  # active, expired, pending
    auditor: str | None = None


class Supplier(BaseModel):
    """Supplier data model."""

    id: str
    name: str
    location: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    oem_approvals: list[str] = Field(default_factory=list)
    quality_rate: float | None = None  # 0-100
    on_time_delivery: float | None = None  # 0-100
    risk_score: float | None = None  # 0-1
    contact_email: str | None = None
    contact_phone: str | None = None


class ComplianceInfo(BaseModel):
    """Compliance validation result."""

    supplier_id: str
    is_compliant: bool
    certifications_valid: list[str] = Field(default_factory=list)
    certifications_missing: list[str] = Field(default_factory=list)
    certifications_expiring: list[str] = Field(default_factory=list)
    itar_cleared: bool | None = None
    notes: str | None = None


class RiskScore(BaseModel):
    """Risk assessment result."""

    supplier_id: str
    overall_score: float  # 0-1, higher = more risky
    categories: dict[str, float] = Field(default_factory=dict)
    # Categories: compliance, financial, capacity, geographic, quality, dependency
    mitigations: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class SupplierPricing(BaseModel):
    """Pricing info for a supplier's item."""

    supplier_name: str
    avg_price: float
    min_price: float = 0.0
    max_price: float = 0.0
    order_count: int = 0
    last_order_date: datetime | None = None


class ProductResult(BaseModel):
    """Result from product search."""

    item_code: str
    description: str
    category: str
    uom: str = "EA"
    suppliers: list[SupplierPricing] = Field(default_factory=list)


class CategoryInfo(BaseModel):
    """Category information."""

    name: str
    level: int  # 1, 2, or 3
    parent: str | None = None
    item_count: int = 0
    supplier_count: int = 0
    total_amount: float = 0.0


class CategoryBrowseResult(BaseModel):
    """Result from category browsing."""

    current_level: int
    categories: list[CategoryInfo] = Field(default_factory=list)
    parent_category: str | None = None


class SupplierRanking(BaseModel):
    """Supplier ranking entry."""

    rank: int
    supplier_name: str
    supplier_id: str | None = None
    metric_value: float
    metric_name: str  # "total_amount", "order_count", "item_count"


class SupplierDetailResult(BaseModel):
    """Detailed supplier information."""

    name: str
    site: str | None = None
    total_orders: int = 0
    total_amount: float = 0.0
    avg_order_value: float = 0.0
    first_order_date: datetime | None = None
    last_order_date: datetime | None = None
    top_categories: list[CategoryInfo] = Field(default_factory=list)
    top_items: list[ProductResult] = Field(default_factory=list)
    rank_by_volume: int | None = None
    market_share: float = 0.0


class PriceComparison(BaseModel):
    """Price comparison across suppliers."""

    item_code: str
    item_description: str
    suppliers: list[SupplierPricing] = Field(default_factory=list)
    lowest_price_supplier: str | None = None
    price_range: tuple[float, float] = (0.0, 0.0)


class SupplierStateExtension(DomainStateExtension):
    """Supplier-specific state extension.

    This state is stored in CoreState.domain_data["supplier"].
    """

    # Search criteria
    search_criteria: dict[str, object] = Field(default_factory=dict)

    # Results
    suppliers: list[Supplier] = Field(default_factory=list)
    compliance_results: list[ComplianceInfo] = Field(default_factory=list)
    risk_results: list[RiskScore] = Field(default_factory=list)
    comparison_data: dict[str, object] = Field(default_factory=dict)
    technical_answer: str | None = None

    # ITAR-specific flags
    itar_flagged: bool = False

    # Product and category search results
    product_search_results: list[ProductResult] = Field(default_factory=list)
    category_results: CategoryBrowseResult | None = None

    # Supplier detail and ranking results
    supplier_detail: SupplierDetailResult | None = None
    top_suppliers_result: list[SupplierRanking] = Field(default_factory=list)

    # Price comparison results
    price_comparison: list[PriceComparison] = Field(default_factory=list)
