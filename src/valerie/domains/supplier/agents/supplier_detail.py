"""Supplier Detail agent - provides detailed supplier information, rankings, and comparisons.

This agent handles multiple intents:
- SUPPLIER_DETAIL: Get comprehensive info about a specific supplier
- TOP_SUPPLIERS: Get ranked list of top suppliers by various metrics
- ITEM_COMPARISON: Compare suppliers for specific items/categories
"""

import logging
import re
from datetime import datetime

from ....agents.base import BaseAgent
from ....data.factory import get_default_data_source
from ....data.interfaces import (
    ComparisonResult,
    SupplierDetail,
    SupplierRankingResult,
)
from ....models import ChatState
from ..intents import SupplierIntent
from ..state import (
    CategoryInfo,
    PriceComparison,
    ProductResult,
    SupplierDetailResult,
    SupplierPricing,
    SupplierRanking,
    SupplierStateExtension,
)

logger = logging.getLogger(__name__)


class SupplierDetailAgent(BaseAgent):
    """Agent for supplier details, rankings, and comparisons.

    Handles these intents:
    - SUPPLIER_DETAIL: Get detailed information about a specific supplier
    - TOP_SUPPLIERS: Get top suppliers ranked by volume, orders, or items
    - ITEM_COMPARISON: Compare prices and suppliers for specific items
    """

    name = "supplier_detail"

    def get_system_prompt(self) -> str:
        return """You are a Supplier Detail Agent for a procurement system.

Your role is to:
1. Provide comprehensive supplier information including:
   - Order history and volumes
   - Top categories and items purchased
   - Market share and ranking
   - Contact and site information

2. Generate supplier rankings by:
   - Total spend (amount)
   - Order frequency (orders)
   - Item variety (items)

3. Compare suppliers on:
   - Pricing for specific items
   - Category coverage
   - Historical performance

Format data clearly with:
- Summary statistics at the top
- Detailed breakdowns below
- Recommendations when relevant

Always provide context like "compared to other suppliers" or "within this category"."""

    async def process(self, state: ChatState) -> ChatState:
        """Process the state based on intent."""
        start_time = datetime.now()

        # Get intent from state
        intent = state.intent
        intent_str = intent.value if hasattr(intent, "value") else str(intent)

        try:
            # Route to appropriate handler based on intent
            if intent_str == SupplierIntent.SUPPLIER_DETAIL.value:
                await self._handle_supplier_detail(state)
            elif intent_str == SupplierIntent.TOP_SUPPLIERS.value:
                await self._handle_top_suppliers(state)
            elif intent_str == SupplierIntent.ITEM_COMPARISON.value:
                await self._handle_item_comparison(state)
            else:
                # Default to supplier detail if we can extract a supplier name
                supplier_name = self._extract_supplier_name(state)
                if supplier_name:
                    await self._handle_supplier_detail(state)
                else:
                    state.agent_outputs[self.name] = self.create_output(
                        success=False,
                        error=f"Unknown intent for SupplierDetailAgent: {intent_str}",
                        start_time=start_time,
                    )
                    return state

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={"intent_handled": intent_str},
                start_time=start_time,
            )

        except Exception as e:
            logger.exception(f"Error in SupplierDetailAgent: {e}")
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=str(e),
                start_time=start_time,
            )

        return state

    async def _handle_supplier_detail(self, state: ChatState) -> None:
        """Handle SUPPLIER_DETAIL intent - get comprehensive supplier info."""
        data_source = get_default_data_source()

        # Extract supplier name/id from query or entities
        supplier_id = self._extract_supplier_id(state)

        if not supplier_id:
            # Try to extract from the user message
            supplier_id = self._extract_supplier_name(state)

        if not supplier_id:
            logger.warning("No supplier identifier found in query")
            return

        # Get supplier detail from data source
        detail = await data_source.get_supplier_detail(supplier_id)

        if detail:
            # Convert to state model and store
            supplier_state = self._get_supplier_state(state)
            supplier_state.supplier_detail = self._convert_to_state_model(detail)
            state.response_type = "detail"

            logger.info(f"Retrieved details for supplier: {detail.name}")
        else:
            logger.warning(f"Supplier not found: {supplier_id}")

    async def _handle_top_suppliers(self, state: ChatState) -> None:
        """Handle TOP_SUPPLIERS intent - get ranked list of suppliers."""
        data_source = get_default_data_source()

        # Extract ranking criteria from entities or query
        rank_by = self._extract_ranking_criteria(state)
        limit = self._extract_limit(state)

        # Get top suppliers from data source
        rankings = await data_source.get_top_suppliers(by=rank_by, limit=limit)

        if rankings:
            # Convert to state model and store
            supplier_state = self._get_supplier_state(state)
            supplier_state.top_suppliers_result = [
                self._convert_ranking_to_state(r) for r in rankings
            ]
            state.response_type = "table"

            logger.info(f"Retrieved top {len(rankings)} suppliers by {rank_by}")

    async def _handle_item_comparison(self, state: ChatState) -> None:
        """Handle ITEM_COMPARISON intent - compare suppliers for items."""
        data_source = get_default_data_source()

        # Extract supplier IDs from entities or query
        supplier_ids = self._extract_supplier_ids(state)

        if len(supplier_ids) < 2:
            # If no specific suppliers, get top suppliers for comparison
            top_suppliers = await data_source.get_top_suppliers(by="amount", limit=5)
            supplier_ids = [s.supplier_id for s in top_suppliers]

        if len(supplier_ids) >= 2:
            # Get comparison from data source
            comparison = await data_source.compare_suppliers(supplier_ids)

            if comparison:
                # Store comparison results
                supplier_state = self._get_supplier_state(state)
                supplier_state.price_comparison = self._convert_comparison_to_state(
                    comparison
                )
                state.comparison_data = {
                    "suppliers": [s.name for s in comparison.suppliers],
                    "metrics": comparison.metrics,
                    "common_categories": comparison.common_categories,
                    "recommendations": comparison.recommendations,
                }
                state.response_type = "comparison"

                logger.info(f"Compared {len(supplier_ids)} suppliers")

    def _get_supplier_state(self, state: ChatState) -> SupplierStateExtension:
        """Get or create the supplier state extension."""
        # Try to get existing domain data
        domain_data = getattr(state, "domain_data", None)
        if domain_data is None:
            # Initialize domain_data if it doesn't exist
            state.domain_data = {}
            domain_data = state.domain_data

        # Get or create supplier state extension
        if "supplier" not in domain_data:
            domain_data["supplier"] = SupplierStateExtension()

        supplier_data = domain_data["supplier"]
        if isinstance(supplier_data, dict):
            supplier_data = SupplierStateExtension(**supplier_data)
            domain_data["supplier"] = supplier_data

        return supplier_data

    def _extract_supplier_id(self, state: ChatState) -> str | None:
        """Extract supplier ID from entities."""
        entities = state.entities or {}

        # Check various entity keys
        if "supplier_id" in entities:
            return entities["supplier_id"]
        if "supplier" in entities:
            return entities["supplier"]
        if "supplier_name" in entities:
            return entities["supplier_name"]

        return None

    def _extract_supplier_name(self, state: ChatState) -> str | None:
        """Extract supplier name from user message."""
        if not state.messages:
            return None

        # Get last user message
        last_message = None
        for msg in reversed(state.messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_message = msg.content
                break
            elif hasattr(msg, "content") and not hasattr(msg, "type"):
                last_message = msg.content
                break

        if not last_message:
            return None

        # Common patterns for supplier name extraction
        patterns = [
            r"(?:info(?:rmacion)?|detalles?|datos?) (?:de|del|sobre) (?:proveedor |supplier )?(.+)",
            r"(?:supplier|proveedor) (.+)",
            r"(?:dame|give me|show) .*?(?:de|about|for) (.+)",
            r"(?:quien es|who is) (.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, last_message, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_supplier_ids(self, state: ChatState) -> list[str]:
        """Extract multiple supplier IDs for comparison."""
        entities = state.entities or {}

        # Check for explicit supplier list
        if "supplier_ids" in entities:
            return entities["supplier_ids"]
        if "suppliers" in entities:
            suppliers = entities["suppliers"]
            if isinstance(suppliers, list):
                return suppliers

        # Try to extract from comparison entities
        if "compare" in entities:
            compare_data = entities["compare"]
            if isinstance(compare_data, list):
                return compare_data

        return []

    def _extract_ranking_criteria(self, state: ChatState) -> str:
        """Extract ranking criteria from query."""
        entities = state.entities or {}

        # Check entities first
        if "rank_by" in entities:
            return entities["rank_by"]

        # Default ranking criteria keywords
        if state.messages:
            last_message = ""
            for msg in reversed(state.messages):
                if hasattr(msg, "content"):
                    last_message = str(msg.content).lower()
                    break

            if "volumen" in last_message or "volume" in last_message or "amount" in last_message:
                return "amount"
            if "ordenes" in last_message or "orders" in last_message or "pedidos" in last_message:
                return "orders"
            if "items" in last_message or "productos" in last_message:
                return "items"

        # Default to amount (total spend)
        return "amount"

    def _extract_limit(self, state: ChatState) -> int:
        """Extract limit from query."""
        entities = state.entities or {}

        if "limit" in entities:
            try:
                return int(entities["limit"])
            except (ValueError, TypeError):
                pass

        # Try to extract from message
        if state.messages:
            last_message = ""
            for msg in reversed(state.messages):
                if hasattr(msg, "content"):
                    last_message = str(msg.content)
                    break

            # Look for numbers in the message
            numbers = re.findall(r"\b(\d+)\b", last_message)
            if numbers:
                limit = int(numbers[0])
                if 1 <= limit <= 100:
                    return limit

        # Default limit
        return 10

    def _convert_to_state_model(self, detail: SupplierDetail) -> SupplierDetailResult:
        """Convert data source SupplierDetail to state SupplierDetailResult."""
        return SupplierDetailResult(
            name=detail.name,
            site=detail.site,
            total_orders=detail.total_orders,
            total_amount=detail.total_amount,
            avg_order_value=detail.avg_order_value,
            first_order_date=detail.first_order_date,
            last_order_date=detail.last_order_date,
            top_categories=[
                CategoryInfo(
                    name=cat.name,
                    level=cat.level,
                    parent=cat.parent,
                    item_count=cat.item_count,
                    supplier_count=cat.supplier_count,
                    total_amount=cat.total_amount,
                )
                for cat in detail.top_categories
            ],
            top_items=[
                ProductResult(
                    item_code=item.item_code,
                    description=item.description,
                    category=item.category,
                    uom=item.uom,
                    suppliers=[],  # Items from detail don't have supplier pricing
                )
                for item in detail.top_items
            ],
            rank_by_volume=detail.rank_by_volume,
            market_share=detail.market_share,
        )

    def _convert_ranking_to_state(self, ranking: SupplierRankingResult) -> SupplierRanking:
        """Convert data source SupplierRankingResult to state SupplierRanking."""
        return SupplierRanking(
            rank=ranking.rank,
            supplier_name=ranking.supplier_name,
            supplier_id=ranking.supplier_id,
            metric_value=ranking.metric_value,
            metric_name=ranking.metric_name,
        )

    def _convert_comparison_to_state(
        self, comparison: ComparisonResult
    ) -> list[PriceComparison]:
        """Convert data source ComparisonResult to state PriceComparison list."""
        # The comparison result contains supplier details and metrics
        # We need to create price comparisons based on the metrics

        price_comparisons = []

        # If we have item-level metrics, create PriceComparison entries
        metrics = comparison.metrics
        for metric_name, supplier_values in metrics.items():
            if metric_name.startswith("item_"):
                item_code = metric_name.replace("item_", "")
                suppliers = [
                    SupplierPricing(
                        supplier_name=name,
                        avg_price=value,
                    )
                    for name, value in supplier_values.items()
                ]

                lowest_price = min(supplier_values.values()) if supplier_values else 0
                lowest_supplier = next(
                    (name for name, val in supplier_values.items() if val == lowest_price),
                    None,
                )

                price_comparisons.append(
                    PriceComparison(
                        item_code=item_code,
                        item_description=item_code,
                        suppliers=suppliers,
                        lowest_price_supplier=lowest_supplier,
                        price_range=(
                            min(supplier_values.values()) if supplier_values else 0,
                            max(supplier_values.values()) if supplier_values else 0,
                        ),
                    )
                )

        return price_comparisons

    def format_supplier_detail(self, detail: SupplierDetailResult) -> str:
        """Format supplier detail for display."""
        lines = [
            f"## {detail.name}",
            "",
            "### Summary",
            f"- **Site**: {detail.site or 'N/A'}",
            f"- **Total Orders**: {detail.total_orders:,}",
            f"- **Total Amount**: ${detail.total_amount:,.2f}",
            f"- **Average Order Value**: ${detail.avg_order_value:,.2f}",
            "",
        ]

        if detail.first_order_date or detail.last_order_date:
            lines.append("### Order History")
            if detail.first_order_date:
                lines.append(f"- **First Order**: {detail.first_order_date.strftime('%Y-%m-%d')}")
            if detail.last_order_date:
                lines.append(f"- **Last Order**: {detail.last_order_date.strftime('%Y-%m-%d')}")
            lines.append("")

        if detail.rank_by_volume or detail.market_share:
            lines.append("### Market Position")
            if detail.rank_by_volume:
                lines.append(f"- **Rank by Volume**: #{detail.rank_by_volume}")
            if detail.market_share:
                lines.append(f"- **Market Share**: {detail.market_share:.1%}")
            lines.append("")

        if detail.top_categories:
            lines.append("### Top Categories")
            for cat in detail.top_categories[:5]:
                lines.append(f"- {cat.name}: ${cat.total_amount:,.2f}")
            lines.append("")

        if detail.top_items:
            lines.append("### Top Items")
            for item in detail.top_items[:5]:
                lines.append(f"- {item.item_code}: {item.description}")
            lines.append("")

        return "\n".join(lines)

    def format_top_suppliers(self, rankings: list[SupplierRanking]) -> str:
        """Format top suppliers ranking for display."""
        if not rankings:
            return "No suppliers found."

        metric_name = rankings[0].metric_name if rankings else "amount"
        metric_display = {
            "total_amount": "Total Spend",
            "order_count": "Order Count",
            "item_count": "Item Count",
            "amount": "Total Spend",
            "orders": "Order Count",
            "items": "Item Count",
        }.get(metric_name, metric_name)

        lines = [
            f"## Top Suppliers by {metric_display}",
            "",
            "| Rank | Supplier | {metric_display} |",
            "|------|----------|-----------------|",
        ]

        for r in rankings:
            if metric_name in ("total_amount", "amount"):
                value = f"${r.metric_value:,.2f}"
            else:
                value = f"{r.metric_value:,.0f}"
            lines.append(f"| {r.rank} | {r.supplier_name} | {value} |")

        return "\n".join(lines)
