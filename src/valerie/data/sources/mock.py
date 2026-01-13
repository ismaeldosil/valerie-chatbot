"""Mock data source for testing."""
from datetime import datetime, timedelta

from valerie.data.interfaces import (
    BaseDataSource,
    SupplierResult,
    SupplierDetail,
    ProductResult,
    ProductWithSuppliers,
    SupplierPricingResult,
    CategoryResult,
    SupplierRankingResult,
    ComparisonResult,
)


class MockDataSource(BaseDataSource):
    """
    Mock data source for testing purposes.

    Provides hardcoded sample data that mimics real supplier data.
    """

    def __init__(self):
        """Initialize with sample data."""
        self._suppliers = [
            SupplierResult(
                id="1",
                name="Grainger Corporate Services LLC",
                site="Main",
                total_orders=838,
                total_amount=855096.80,
                avg_order_value=1020.40,
                first_order_date=datetime(2024, 1, 15),
                last_order_date=datetime(2025, 1, 10),
            ),
            SupplierResult(
                id="2",
                name="TC Specialties Inc",
                site="HQ",
                total_orders=381,
                total_amount=4298878.00,
                avg_order_value=11283.41,
                first_order_date=datetime(2024, 2, 1),
                last_order_date=datetime(2025, 1, 8),
            ),
            SupplierResult(
                id="3",
                name="Advanced Chemical Company",
                site="West",
                total_orders=26,
                total_amount=2197925.00,
                avg_order_value=84535.58,
                first_order_date=datetime(2024, 3, 10),
                last_order_date=datetime(2025, 1, 5),
            ),
            SupplierResult(
                id="4",
                name="McMaster-Carr Supply Company",
                site="Main",
                total_orders=500,
                total_amount=750000.00,
                avg_order_value=1500.00,
                first_order_date=datetime(2024, 1, 1),
                last_order_date=datetime(2025, 1, 12),
            ),
            SupplierResult(
                id="5",
                name="Uline Inc",
                site="Shipping",
                total_orders=581,
                total_amount=691150.70,
                avg_order_value=1189.59,
                first_order_date=datetime(2024, 2, 15),
                last_order_date=datetime(2025, 1, 11),
            ),
        ]

        # Map supplier IDs to their process capabilities (for aerospace testing)
        self._supplier_capabilities = {
            "1": ["heat_treatment", "ndt", "machining"],
            "2": ["heat_treatment", "coating", "forging"],
            "3": ["chemical_processing", "heat_treatment"],
            "4": ["machining", "assembly", "ndt"],
            "5": ["packaging", "logistics"],
        }

        self._products = [
            ProductResult(
                item_code="ACET-001",
                description="Acetone, ACS Grade, 4L",
                category="Controlled Material-Chemicals-Acetone",
                uom="EA",
                avg_price=45.50,
                min_price=42.00,
                max_price=52.00,
                supplier_count=3,
            ),
            ProductResult(
                item_code="GLOVE-NIT-L",
                description="Gloves Microflex Nitril Disposable L (9)",
                category="Non-Controlled Material-Safety Prevention & Training-Gloves",
                uom="BX",
                avg_price=18.50,
                min_price=15.00,
                max_price=22.00,
                supplier_count=5,
            ),
            ProductResult(
                item_code="SULF-ACID-1G",
                description="Sulfuric Acid, Technical Grade, 1 Gallon",
                category="Controlled Material-Chemicals-Sulfuric Acid",
                uom="EA",
                avg_price=125.00,
                min_price=110.00,
                max_price=145.00,
                supplier_count=2,
            ),
            ProductResult(
                item_code="PRIMER-EP-1G",
                description="Epoxy Primer, MIL-PRF-23377, 1 Gallon",
                category="Controlled Material-Paint Inventory-Primer",
                uom="GL",
                avg_price=285.00,
                min_price=260.00,
                max_price=310.00,
                supplier_count=4,
            ),
        ]

        self._categories = [
            CategoryResult(id="1", name="Controlled Material", level=1, level1="Controlled Material", item_count=5000, supplier_count=200, total_amount=15000000.00),
            CategoryResult(id="2", name="Non-Controlled Material", level=1, level1="Non-Controlled Material", item_count=8000, supplier_count=350, total_amount=12000000.00),
            CategoryResult(id="3", name="Controlled Service", level=1, level1="Controlled Service", item_count=2000, supplier_count=100, total_amount=8000000.00),
            CategoryResult(id="4", name="Controlled Material-Chemicals", level=2, level1="Controlled Material", level2="Chemicals", parent="Controlled Material", item_count=1500, supplier_count=80, total_amount=5000000.00),
            CategoryResult(id="5", name="Controlled Material-Paint Inventory", level=2, level1="Controlled Material", level2="Paint Inventory", parent="Controlled Material", item_count=1200, supplier_count=60, total_amount=4000000.00),
            CategoryResult(id="6", name="Non-Controlled Material-Safety Prevention & Training", level=2, level1="Non-Controlled Material", level2="Safety Prevention & Training", parent="Non-Controlled Material", item_count=800, supplier_count=40, total_amount=1500000.00),
            CategoryResult(id="7", name="Controlled Material-Chemicals-Acetone", level=3, level1="Controlled Material", level2="Chemicals", level3="Acetone", parent="Controlled Material-Chemicals", item_count=50, supplier_count=5, total_amount=100000.00),
            CategoryResult(id="8", name="Controlled Material-Chemicals-Sulfuric Acid", level=3, level1="Controlled Material", level2="Chemicals", level3="Sulfuric Acid", parent="Controlled Material-Chemicals", item_count=30, supplier_count=3, total_amount=150000.00),
        ]

    async def search_suppliers(
        self,
        name: str | None = None,
        category: str | None = None,
        product: str | None = None,
        limit: int = 10
    ) -> list[SupplierResult]:
        """Search suppliers by criteria."""
        results = self._suppliers.copy()

        if name:
            name_lower = name.lower()
            results = [s for s in results if name_lower in s.name.lower()]

        if category:
            # In real impl, would filter by category
            pass

        if product:
            # In real impl, would filter by product
            pass

        return results[:limit]

    async def get_supplier_detail(self, supplier_id: str) -> SupplierDetail | None:
        """Get detailed supplier information."""
        # Find by ID or name
        supplier = None
        for s in self._suppliers:
            if s.id == supplier_id or s.name.lower() == supplier_id.lower():
                supplier = s
                break

        if not supplier:
            return None

        # Get capabilities for this supplier (used by SupplierSearchAgent for filtering)
        capabilities = self._supplier_capabilities.get(supplier.id, [])

        # Create category results from capabilities for top_categories
        capability_categories = [
            CategoryResult(
                id=f"cap-{i}",
                name=cap,
                level=1,
                level1=cap,
                item_count=100,
                supplier_count=10,
                total_amount=100000.0,
            )
            for i, cap in enumerate(capabilities[:3])
        ]

        return SupplierDetail(
            id=supplier.id,
            name=supplier.name,
            site=supplier.site,
            total_orders=supplier.total_orders,
            total_amount=supplier.total_amount,
            avg_order_value=supplier.avg_order_value,
            first_order_date=supplier.first_order_date,
            last_order_date=supplier.last_order_date,
            top_categories=capability_categories if capability_categories else self._categories[:3],
            top_items=self._products[:3],
            rank_by_volume=self._suppliers.index(supplier) + 1,
            market_share=supplier.total_amount / sum(s.total_amount for s in self._suppliers) * 100,
        )

    async def search_products(
        self,
        query: str,
        category: str | None = None,
        limit: int = 20
    ) -> list[ProductResult]:
        """Search for products."""
        query_lower = query.lower()
        results = [
            p for p in self._products
            if query_lower in p.description.lower() or query_lower in p.item_code.lower()
        ]

        if category:
            category_lower = category.lower()
            results = [p for p in results if category_lower in p.category.lower()]

        return results[:limit]

    async def get_product_suppliers(self, item_code: str) -> ProductWithSuppliers | None:
        """Get product with suppliers."""
        product = None
        for p in self._products:
            if p.item_code == item_code:
                product = p
                break

        if not product:
            return None

        # Generate mock supplier pricing
        suppliers = [
            SupplierPricingResult(
                supplier_id=s.id,
                supplier_name=s.name,
                avg_price=product.avg_price * (0.9 + 0.2 * i / len(self._suppliers)),
                min_price=product.min_price,
                max_price=product.max_price,
                order_count=10 + i * 5,
                total_ordered_qty=100 + i * 50,
                last_order_date=datetime.now() - timedelta(days=i * 7),
            )
            for i, s in enumerate(self._suppliers[:product.supplier_count])
        ]

        return ProductWithSuppliers(
            item_code=product.item_code,
            description=product.description,
            category=product.category,
            uom=product.uom,
            suppliers=suppliers,
        )

    async def get_categories(
        self,
        parent: str | None = None,
        level: int | None = None
    ) -> list[CategoryResult]:
        """Get categories."""
        results = self._categories.copy()

        if level is not None:
            results = [c for c in results if c.level == level]

        if parent:
            parent_lower = parent.lower()
            results = [c for c in results if c.parent and parent_lower in c.parent.lower()]

        return results

    async def get_top_suppliers(
        self,
        by: str = "amount",
        limit: int = 10
    ) -> list[SupplierRankingResult]:
        """Get top suppliers by metric."""
        sorted_suppliers = sorted(
            self._suppliers,
            key=lambda s: s.total_amount if by == "amount" else s.total_orders,
            reverse=True
        )

        return [
            SupplierRankingResult(
                rank=i + 1,
                supplier_id=s.id,
                supplier_name=s.name,
                metric_value=s.total_amount if by == "amount" else s.total_orders,
                metric_name=f"total_{by}",
            )
            for i, s in enumerate(sorted_suppliers[:limit])
        ]

    async def compare_suppliers(self, supplier_ids: list[str]) -> ComparisonResult:
        """Compare suppliers."""
        suppliers = []
        for sid in supplier_ids:
            detail = await self.get_supplier_detail(sid)
            if detail:
                suppliers.append(detail)

        metrics = {
            "total_amount": {s.name: s.total_amount for s in suppliers},
            "total_orders": {s.name: float(s.total_orders) for s in suppliers},
            "avg_order_value": {s.name: s.avg_order_value for s in suppliers},
        }

        return ComparisonResult(
            suppliers=suppliers,
            metrics=metrics,
            common_categories=["Chemicals", "Safety Supplies"],
            recommendations=[
                f"{suppliers[0].name} has the highest order volume" if suppliers else "",
            ],
        )

    async def get_category_suppliers(
        self,
        category: str,
        limit: int = 20
    ) -> list[SupplierResult]:
        """Get suppliers for a category."""
        # In mock, return all suppliers
        return self._suppliers[:limit]

    async def health_check(self) -> bool:
        """Check health - always healthy for mock."""
        return True
