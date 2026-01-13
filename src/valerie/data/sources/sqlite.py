"""SQLite data source implementation."""
import asyncio
from functools import partial
from pathlib import Path
from typing import Union

from sqlalchemy import func, or_, and_, desc, text
from sqlalchemy.orm import Session, joinedload

from valerie.data.database import Database
from valerie.data.schema import Supplier, Category, SupplierItem, SupplierCategory
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


class SQLiteDataSource(BaseDataSource):
    """
    SQLite data source implementation.

    Uses SQLAlchemy for database access with the Database class from database.py.
    All methods are async-compatible by running sync SQLAlchemy code in a thread pool.
    """

    def __init__(self, db_path: Union[str, Path] = "data/valerie.db"):
        """
        Initialize SQLite data source.

        Args:
            db_path: Path to the SQLite database file.
                     Use ':memory:' for an in-memory database (useful for testing).
        """
        # Handle :memory: special case
        if str(db_path) == ":memory:":
            self._init_memory_db()
        else:
            self.db = Database(db_path)
            self.db.create_tables()

    def _init_memory_db(self):
        """Initialize an in-memory SQLite database."""
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker, scoped_session
        from sqlalchemy.pool import StaticPool
        from valerie.data.schema import Base

        # Create in-memory engine with StaticPool to ensure same connection
        # is reused across all threads (important for in-memory SQLite)
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create a minimal Database-like object for in-memory use
        class MemoryDatabase:
            def __init__(self, eng, session_maker):
                self.engine = eng
                self.SessionLocal = session_maker
                self._session = None

            def get_session(self):
                return self.SessionLocal()

            def create_tables(self):
                Base.metadata.create_all(bind=self.engine)

            def __enter__(self):
                self._session = self.get_session()
                return self._session

            def __exit__(self, exc_type, exc_val, exc_tb):
                if self._session is not None:
                    if exc_type is not None:
                        self._session.rollback()
                    self._session.close()
                    self._session = None

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

        self.db = MemoryDatabase(engine, SessionLocal)
        self.db.create_tables()

    def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, partial(func, *args, **kwargs))

    def _supplier_to_result(self, supplier: Supplier) -> SupplierResult:
        """Convert a Supplier model to SupplierResult DTO."""
        return SupplierResult(
            id=str(supplier.id),
            name=supplier.name,
            site=supplier.site,
            total_orders=supplier.total_orders or 0,
            total_amount=supplier.total_amount or 0.0,
            avg_order_value=supplier.avg_order_value or 0.0,
            first_order_date=supplier.first_order_date,
            last_order_date=supplier.last_order_date,
        )

    def _category_to_result(
        self, category: Category, supplier_count: int = 0
    ) -> CategoryResult:
        """Convert a Category model to CategoryResult DTO."""
        # Determine level based on which level fields are populated
        level = 1
        if category.level3:
            level = 3
        elif category.level2:
            level = 2

        # Determine parent
        parent = None
        if level == 3 and category.level2:
            parent = f"{category.level1}-{category.level2}"
        elif level == 2 and category.level1:
            parent = category.level1

        return CategoryResult(
            id=str(category.id),
            name=category.name,
            level=level,
            level1=category.level1,
            level2=category.level2,
            level3=category.level3,
            parent=parent,
            item_count=category.item_count or 0,
            supplier_count=supplier_count,
            total_amount=category.total_amount or 0.0,
        )

    def _item_to_product_result(
        self, item: SupplierItem, category_name: str | None, supplier_count: int = 0
    ) -> ProductResult:
        """Convert a SupplierItem model to ProductResult DTO."""
        return ProductResult(
            item_code=item.item_code or "",
            description=item.description or "",
            category=category_name or "",
            category_id=str(item.category_id) if item.category_id else None,
            uom=item.uom or "EA",
            avg_price=item.avg_price or 0.0,
            min_price=item.min_price or 0.0,
            max_price=item.max_price or 0.0,
            supplier_count=supplier_count,
        )

    def _search_suppliers_sync(
        self,
        name: str | None = None,
        category: str | None = None,
        product: str | None = None,
        limit: int = 10,
    ) -> list[SupplierResult]:
        """Synchronous implementation of supplier search."""
        with self.db as session:
            query = session.query(Supplier)

            if name:
                query = query.filter(Supplier.name.ilike(f"%{name}%"))

            if category:
                # Join through SupplierCategory to Category
                query = (
                    query.join(SupplierCategory, Supplier.id == SupplierCategory.supplier_id)
                    .join(Category, SupplierCategory.category_id == Category.id)
                    .filter(
                        or_(
                            Category.name.ilike(f"%{category}%"),
                            Category.level1.ilike(f"%{category}%"),
                            Category.level2.ilike(f"%{category}%"),
                            Category.level3.ilike(f"%{category}%"),
                        )
                    )
                )

            if product:
                # Join through SupplierItem
                if category:
                    # Already joined, need to also join items
                    query = query.join(
                        SupplierItem, Supplier.id == SupplierItem.supplier_id
                    ).filter(
                        or_(
                            SupplierItem.item_code.ilike(f"%{product}%"),
                            SupplierItem.description.ilike(f"%{product}%"),
                        )
                    )
                else:
                    query = query.join(
                        SupplierItem, Supplier.id == SupplierItem.supplier_id
                    ).filter(
                        or_(
                            SupplierItem.item_code.ilike(f"%{product}%"),
                            SupplierItem.description.ilike(f"%{product}%"),
                        )
                    )

            # Deduplicate and order by total_amount descending
            query = (
                query.distinct()
                .order_by(desc(Supplier.total_amount))
                .limit(limit)
            )

            suppliers = query.all()
            return [self._supplier_to_result(s) for s in suppliers]

    async def search_suppliers(
        self,
        name: str | None = None,
        category: str | None = None,
        product: str | None = None,
        limit: int = 10,
    ) -> list[SupplierResult]:
        """Search suppliers by various criteria."""
        return await self._run_sync(
            self._search_suppliers_sync, name, category, product, limit
        )

    def _get_supplier_detail_sync(self, supplier_id: str) -> SupplierDetail | None:
        """Synchronous implementation of get_supplier_detail."""
        with self.db as session:
            # Try to find by ID first, then by name
            supplier = None
            try:
                supplier_int_id = int(supplier_id)
                supplier = session.query(Supplier).filter(
                    Supplier.id == supplier_int_id
                ).first()
            except ValueError:
                pass

            if not supplier:
                supplier = session.query(Supplier).filter(
                    Supplier.name.ilike(f"%{supplier_id}%")
                ).first()

            if not supplier:
                return None

            # Get top categories for this supplier
            top_categories_data = (
                session.query(Category, SupplierCategory.item_count, SupplierCategory.total_amount)
                .join(SupplierCategory, Category.id == SupplierCategory.category_id)
                .filter(SupplierCategory.supplier_id == supplier.id)
                .order_by(desc(SupplierCategory.total_amount))
                .limit(5)
                .all()
            )

            top_categories = []
            for cat, item_count, total_amount in top_categories_data:
                cat_result = self._category_to_result(cat)
                cat_result.item_count = item_count or 0
                cat_result.total_amount = total_amount or 0.0
                top_categories.append(cat_result)

            # Get top items for this supplier
            top_items_data = (
                session.query(SupplierItem, Category.name)
                .outerjoin(Category, SupplierItem.category_id == Category.id)
                .filter(SupplierItem.supplier_id == supplier.id)
                .order_by(desc(SupplierItem.total_ordered_amount))
                .limit(5)
                .all()
            )

            top_items = [
                self._item_to_product_result(item, cat_name, supplier_count=1)
                for item, cat_name in top_items_data
            ]

            # Calculate rank by volume
            rank_query = (
                session.query(func.count(Supplier.id) + 1)
                .filter(Supplier.total_amount > supplier.total_amount)
                .scalar()
            )
            rank_by_volume = rank_query or 1

            # Calculate market share
            total_market = session.query(func.sum(Supplier.total_amount)).scalar() or 0.0
            market_share = (
                (supplier.total_amount / total_market * 100) if total_market > 0 else 0.0
            )

            return SupplierDetail(
                id=str(supplier.id),
                name=supplier.name,
                site=supplier.site,
                total_orders=supplier.total_orders or 0,
                total_amount=supplier.total_amount or 0.0,
                avg_order_value=supplier.avg_order_value or 0.0,
                first_order_date=supplier.first_order_date,
                last_order_date=supplier.last_order_date,
                top_categories=top_categories,
                top_items=top_items,
                rank_by_volume=rank_by_volume,
                market_share=round(market_share, 2),
            )

    async def get_supplier_detail(self, supplier_id: str) -> SupplierDetail | None:
        """Get detailed information about a specific supplier."""
        return await self._run_sync(self._get_supplier_detail_sync, supplier_id)

    def _search_products_sync(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductResult]:
        """Synchronous implementation of product search."""
        with self.db as session:
            # Subquery to count suppliers per item
            supplier_count_subq = (
                session.query(
                    SupplierItem.item_code,
                    func.count(SupplierItem.supplier_id.distinct()).label("supplier_count"),
                )
                .group_by(SupplierItem.item_code)
                .subquery()
            )

            # Aggregate product data across all suppliers
            base_query = (
                session.query(
                    SupplierItem.item_code,
                    SupplierItem.description,
                    SupplierItem.uom,
                    Category.id.label("category_id"),
                    Category.name.label("category_name"),
                    func.avg(SupplierItem.avg_price).label("avg_price"),
                    func.min(SupplierItem.min_price).label("min_price"),
                    func.max(SupplierItem.max_price).label("max_price"),
                    supplier_count_subq.c.supplier_count,
                )
                .outerjoin(Category, SupplierItem.category_id == Category.id)
                .outerjoin(
                    supplier_count_subq,
                    SupplierItem.item_code == supplier_count_subq.c.item_code,
                )
                .filter(
                    or_(
                        SupplierItem.item_code.ilike(f"%{query}%"),
                        SupplierItem.description.ilike(f"%{query}%"),
                    )
                )
            )

            if category:
                base_query = base_query.filter(
                    or_(
                        Category.name.ilike(f"%{category}%"),
                        Category.level1.ilike(f"%{category}%"),
                        Category.level2.ilike(f"%{category}%"),
                        Category.level3.ilike(f"%{category}%"),
                    )
                )

            # Group by item_code to get unique products
            results = (
                base_query.group_by(
                    SupplierItem.item_code,
                    SupplierItem.description,
                    SupplierItem.uom,
                    Category.id,
                    Category.name,
                    supplier_count_subq.c.supplier_count,
                )
                .limit(limit)
                .all()
            )

            return [
                ProductResult(
                    item_code=row.item_code or "",
                    description=row.description or "",
                    category=row.category_name or "",
                    category_id=str(row.category_id) if row.category_id else None,
                    uom=row.uom or "EA",
                    avg_price=row.avg_price or 0.0,
                    min_price=row.min_price or 0.0,
                    max_price=row.max_price or 0.0,
                    supplier_count=row.supplier_count or 0,
                )
                for row in results
            ]

    async def search_products(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[ProductResult]:
        """Search for products/items."""
        return await self._run_sync(self._search_products_sync, query, category, limit)

    def _get_product_suppliers_sync(self, item_code: str) -> ProductWithSuppliers | None:
        """Synchronous implementation of get_product_suppliers."""
        with self.db as session:
            # Get all supplier items for this item code
            items_data = (
                session.query(SupplierItem, Supplier, Category.name)
                .join(Supplier, SupplierItem.supplier_id == Supplier.id)
                .outerjoin(Category, SupplierItem.category_id == Category.id)
                .filter(SupplierItem.item_code == item_code)
                .all()
            )

            if not items_data:
                return None

            # Use the first item for product info
            first_item, _, category_name = items_data[0]

            suppliers = [
                SupplierPricingResult(
                    supplier_id=str(supplier.id),
                    supplier_name=supplier.name,
                    avg_price=item.avg_price or 0.0,
                    min_price=item.min_price or 0.0,
                    max_price=item.max_price or 0.0,
                    order_count=item.order_count or 0,
                    total_ordered_qty=item.total_ordered_qty or 0.0,
                    last_order_date=item.last_order_date,
                )
                for item, supplier, _ in items_data
            ]

            # Sort suppliers by avg_price ascending
            suppliers.sort(key=lambda s: s.avg_price)

            return ProductWithSuppliers(
                item_code=first_item.item_code or "",
                description=first_item.description or "",
                category=category_name or "",
                uom=first_item.uom or "EA",
                suppliers=suppliers,
            )

    async def get_product_suppliers(self, item_code: str) -> ProductWithSuppliers | None:
        """Get a product with all its suppliers and pricing."""
        return await self._run_sync(self._get_product_suppliers_sync, item_code)

    def _get_categories_sync(
        self, parent: str | None = None, level: int | None = None
    ) -> list[CategoryResult]:
        """Synchronous implementation of get_categories."""
        with self.db as session:
            # Subquery for supplier count per category
            supplier_count_subq = (
                session.query(
                    SupplierCategory.category_id,
                    func.count(SupplierCategory.supplier_id.distinct()).label(
                        "supplier_count"
                    ),
                )
                .group_by(SupplierCategory.category_id)
                .subquery()
            )

            query = session.query(
                Category, supplier_count_subq.c.supplier_count
            ).outerjoin(
                supplier_count_subq, Category.id == supplier_count_subq.c.category_id
            )

            if level is not None:
                # Filter by level
                if level == 1:
                    query = query.filter(
                        and_(
                            Category.level1.isnot(None),
                            or_(Category.level2.is_(None), Category.level2 == ""),
                        )
                    )
                elif level == 2:
                    query = query.filter(
                        and_(
                            Category.level2.isnot(None),
                            Category.level2 != "",
                            or_(Category.level3.is_(None), Category.level3 == ""),
                        )
                    )
                elif level == 3:
                    query = query.filter(
                        and_(Category.level3.isnot(None), Category.level3 != "")
                    )

            if parent:
                # Filter by parent category
                parent_lower = parent.lower()
                # Check if parent matches level1 or level1-level2 pattern
                if "-" in parent:
                    parts = parent.split("-", 1)
                    query = query.filter(
                        and_(
                            Category.level1.ilike(f"%{parts[0]}%"),
                            Category.level2.ilike(f"%{parts[1]}%"),
                        )
                    )
                else:
                    query = query.filter(Category.level1.ilike(f"%{parent}%"))

            results = query.order_by(Category.name).all()

            return [
                self._category_to_result(cat, supplier_count or 0)
                for cat, supplier_count in results
            ]

    async def get_categories(
        self, parent: str | None = None, level: int | None = None
    ) -> list[CategoryResult]:
        """Get product categories."""
        return await self._run_sync(self._get_categories_sync, parent, level)

    def _get_top_suppliers_sync(
        self, by: str = "amount", limit: int = 10
    ) -> list[SupplierRankingResult]:
        """Synchronous implementation of get_top_suppliers."""
        with self.db as session:
            if by == "amount":
                order_col = desc(Supplier.total_amount)
                metric_name = "total_amount"
            elif by == "orders":
                order_col = desc(Supplier.total_orders)
                metric_name = "total_orders"
            elif by == "items":
                # Count distinct items per supplier
                item_count_subq = (
                    session.query(
                        SupplierItem.supplier_id,
                        func.count(SupplierItem.id).label("item_count"),
                    )
                    .group_by(SupplierItem.supplier_id)
                    .subquery()
                )

                results = (
                    session.query(Supplier, item_count_subq.c.item_count)
                    .outerjoin(
                        item_count_subq, Supplier.id == item_count_subq.c.supplier_id
                    )
                    .order_by(desc(item_count_subq.c.item_count))
                    .limit(limit)
                    .all()
                )

                return [
                    SupplierRankingResult(
                        rank=i + 1,
                        supplier_id=str(supplier.id),
                        supplier_name=supplier.name,
                        metric_value=float(item_count or 0),
                        metric_name="item_count",
                    )
                    for i, (supplier, item_count) in enumerate(results)
                ]
            else:
                # Default to amount
                order_col = desc(Supplier.total_amount)
                metric_name = "total_amount"

            suppliers = (
                session.query(Supplier).order_by(order_col).limit(limit).all()
            )

            return [
                SupplierRankingResult(
                    rank=i + 1,
                    supplier_id=str(s.id),
                    supplier_name=s.name,
                    metric_value=(
                        s.total_amount if metric_name == "total_amount" else float(s.total_orders)
                    ),
                    metric_name=metric_name,
                )
                for i, s in enumerate(suppliers)
            ]

    async def get_top_suppliers(
        self, by: str = "amount", limit: int = 10
    ) -> list[SupplierRankingResult]:
        """Get top suppliers by a metric."""
        return await self._run_sync(self._get_top_suppliers_sync, by, limit)

    def _compare_suppliers_sync(self, supplier_ids: list[str]) -> ComparisonResult:
        """Synchronous implementation of compare_suppliers."""
        with self.db as session:
            suppliers_detail = []

            for sid in supplier_ids:
                # Use the sync detail method logic inline to avoid nested context managers
                supplier = None
                try:
                    supplier_int_id = int(sid)
                    supplier = session.query(Supplier).filter(
                        Supplier.id == supplier_int_id
                    ).first()
                except ValueError:
                    pass

                if not supplier:
                    supplier = session.query(Supplier).filter(
                        Supplier.name.ilike(f"%{sid}%")
                    ).first()

                if supplier:
                    # Get top categories for this supplier
                    top_categories_data = (
                        session.query(
                            Category,
                            SupplierCategory.item_count,
                            SupplierCategory.total_amount,
                        )
                        .join(SupplierCategory, Category.id == SupplierCategory.category_id)
                        .filter(SupplierCategory.supplier_id == supplier.id)
                        .order_by(desc(SupplierCategory.total_amount))
                        .limit(5)
                        .all()
                    )

                    top_categories = []
                    for cat, item_count, total_amount in top_categories_data:
                        cat_result = self._category_to_result(cat)
                        cat_result.item_count = item_count or 0
                        cat_result.total_amount = total_amount or 0.0
                        top_categories.append(cat_result)

                    # Get top items for this supplier
                    top_items_data = (
                        session.query(SupplierItem, Category.name)
                        .outerjoin(Category, SupplierItem.category_id == Category.id)
                        .filter(SupplierItem.supplier_id == supplier.id)
                        .order_by(desc(SupplierItem.total_ordered_amount))
                        .limit(5)
                        .all()
                    )

                    top_items = [
                        self._item_to_product_result(item, cat_name, supplier_count=1)
                        for item, cat_name in top_items_data
                    ]

                    # Calculate rank by volume
                    rank_by_volume = (
                        session.query(func.count(Supplier.id) + 1)
                        .filter(Supplier.total_amount > supplier.total_amount)
                        .scalar()
                    ) or 1

                    # Calculate market share
                    total_market = (
                        session.query(func.sum(Supplier.total_amount)).scalar() or 0.0
                    )
                    market_share = (
                        (supplier.total_amount / total_market * 100)
                        if total_market > 0
                        else 0.0
                    )

                    detail = SupplierDetail(
                        id=str(supplier.id),
                        name=supplier.name,
                        site=supplier.site,
                        total_orders=supplier.total_orders or 0,
                        total_amount=supplier.total_amount or 0.0,
                        avg_order_value=supplier.avg_order_value or 0.0,
                        first_order_date=supplier.first_order_date,
                        last_order_date=supplier.last_order_date,
                        top_categories=top_categories,
                        top_items=top_items,
                        rank_by_volume=rank_by_volume,
                        market_share=round(market_share, 2),
                    )
                    suppliers_detail.append(detail)

            # Build metrics comparison
            metrics = {
                "total_amount": {s.name: s.total_amount for s in suppliers_detail},
                "total_orders": {s.name: float(s.total_orders) for s in suppliers_detail},
                "avg_order_value": {s.name: s.avg_order_value for s in suppliers_detail},
                "market_share": {s.name: s.market_share for s in suppliers_detail},
            }

            # Find common categories
            if suppliers_detail:
                category_sets = []
                for detail in suppliers_detail:
                    cat_names = {c.name for c in detail.top_categories}
                    category_sets.append(cat_names)

                common_categories = list(set.intersection(*category_sets)) if category_sets else []
            else:
                common_categories = []

            # Generate recommendations
            recommendations = []
            if suppliers_detail:
                # Find highest volume supplier
                by_volume = sorted(suppliers_detail, key=lambda s: s.total_amount, reverse=True)
                if by_volume:
                    recommendations.append(
                        f"{by_volume[0].name} has the highest total spend (${by_volume[0].total_amount:,.2f})"
                    )

                # Find supplier with most orders
                by_orders = sorted(suppliers_detail, key=lambda s: s.total_orders, reverse=True)
                if by_orders and len(suppliers_detail) > 1:
                    recommendations.append(
                        f"{by_orders[0].name} has the most orders ({by_orders[0].total_orders})"
                    )

                # Find best avg order value
                by_avg = sorted(suppliers_detail, key=lambda s: s.avg_order_value, reverse=True)
                if by_avg and len(suppliers_detail) > 1:
                    recommendations.append(
                        f"{by_avg[0].name} has the highest average order value (${by_avg[0].avg_order_value:,.2f})"
                    )

            return ComparisonResult(
                suppliers=suppliers_detail,
                metrics=metrics,
                common_categories=common_categories,
                recommendations=recommendations,
            )

    async def compare_suppliers(self, supplier_ids: list[str]) -> ComparisonResult:
        """Compare multiple suppliers."""
        return await self._run_sync(self._compare_suppliers_sync, supplier_ids)

    def _get_category_suppliers_sync(
        self, category: str, limit: int = 20
    ) -> list[SupplierResult]:
        """Synchronous implementation of get_category_suppliers."""
        with self.db as session:
            query = (
                session.query(Supplier)
                .join(SupplierCategory, Supplier.id == SupplierCategory.supplier_id)
                .join(Category, SupplierCategory.category_id == Category.id)
                .filter(
                    or_(
                        Category.name.ilike(f"%{category}%"),
                        Category.level1.ilike(f"%{category}%"),
                        Category.level2.ilike(f"%{category}%"),
                        Category.level3.ilike(f"%{category}%"),
                    )
                )
                .order_by(desc(SupplierCategory.total_amount))
                .distinct()
                .limit(limit)
            )

            suppliers = query.all()
            return [self._supplier_to_result(s) for s in suppliers]

    async def get_category_suppliers(
        self, category: str, limit: int = 20
    ) -> list[SupplierResult]:
        """Get all suppliers for a specific category."""
        return await self._run_sync(self._get_category_suppliers_sync, category, limit)

    def _health_check_sync(self) -> bool:
        """Synchronous implementation of health_check."""
        try:
            with self.db as session:
                # Simple query to verify connectivity
                session.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    async def health_check(self) -> bool:
        """Check if the data source is available."""
        return await self._run_sync(self._health_check_sync)
