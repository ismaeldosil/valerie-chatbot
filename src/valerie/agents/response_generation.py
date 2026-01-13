"""Response Generation agent - formats final responses."""

from datetime import datetime
from typing import Any

from ..domains.supplier.state import (
    PriceComparison,
    ProductResult,
    SupplierDetailResult,
    SupplierPricing,
    SupplierRanking,
)
from ..models import ChatState, Intent
from .base import BaseAgent


class ResponseGenerationAgent(BaseAgent):
    """Generates formatted responses for the user."""

    name = "response_generation"

    def get_system_prompt(self) -> str:
        return """You are a Response Generation Agent for an aerospace supplier system.

Your role is to:
1. Synthesize information from all agents into a clear response
2. Format appropriately based on response type:
   - Text: Conversational, helpful responses
   - Table: Structured data with clear columns
   - Comparison: Side-by-side with recommendations
   - Error: Clear explanation with next steps

Guidelines:
- Be concise but comprehensive
- Use bullet points for lists
- Highlight key recommendations
- Include relevant metrics
- Warn about risks or compliance issues
- Suggest next steps when appropriate

Tone: Professional, helpful, aerospace industry appropriate."""

    async def process(self, state: ChatState) -> ChatState:
        """Generate the final response based on state."""
        start_time = datetime.now()

        # Get supplier domain data
        supplier_data = state.domain_data.get("supplier", {})

        # Determine response type based on available data
        if state.error:
            state.response_type = "error"
            state.final_response = self._generate_error_response(state)
        elif supplier_data.get("price_comparison"):
            state.response_type = "table"
            state.final_response = self._generate_price_comparison_response(state)
        elif supplier_data.get("supplier_detail"):
            state.response_type = "text"
            state.final_response = self._generate_supplier_detail_response(state)
        elif supplier_data.get("top_suppliers_result"):
            state.response_type = "table"
            state.final_response = self._generate_top_suppliers_response(state)
        elif supplier_data.get("category_results"):
            state.response_type = "text"
            state.final_response = self._generate_category_browse_response(state)
        elif supplier_data.get("product_search_results"):
            state.response_type = "table"
            state.final_response = self._generate_product_search_response(state)
        elif state.comparison_data:
            state.response_type = "comparison"
            state.final_response = self._generate_comparison_response(state)
        elif state.suppliers:
            state.response_type = "table"
            state.final_response = self._generate_supplier_response(state)
        elif state.technical_answer:
            state.response_type = "text"
            state.final_response = state.technical_answer
        else:
            state.response_type = "text"
            state.final_response = self._generate_generic_response(state)

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data={
                "response_type": state.response_type,
                "response_length": len(state.final_response or ""),
            },
            start_time=start_time,
        )

        return state

    def _generate_supplier_response(self, state: ChatState) -> str:
        """Generate response for supplier search results."""
        if not state.suppliers:
            return (
                "No suppliers found matching your criteria. "
                "Would you like to adjust your search parameters?"
            )

        lines = [f"Found {len(state.suppliers)} supplier(s) matching your criteria:\n"]

        for i, supplier in enumerate(state.suppliers, 1):
            lines.append(f"**{i}. {supplier.name}**")
            lines.append(f"   - Location: {supplier.location or 'N/A'}")
            lines.append(f"   - Capabilities: {', '.join(supplier.capabilities)}")
            lines.append(f"   - Quality Rate: {supplier.quality_rate or 'N/A'}%")
            lines.append(f"   - On-Time Delivery: {supplier.on_time_delivery or 'N/A'}%")

            # Add compliance info
            compliance = next(
                (c for c in state.compliance_results if c.supplier_id == supplier.id),
                None,
            )
            if compliance:
                status = "Compliant" if compliance.is_compliant else "Non-compliant"
                lines.append(f"   - Compliance: {status}")
                if compliance.certifications_missing:
                    lines.append(f"   - Missing: {', '.join(compliance.certifications_missing)}")

            # Add risk info
            risk = next(
                (r for r in state.risk_results if r.supplier_id == supplier.id),
                None,
            )
            if risk:
                risk_level = self._risk_level(risk.overall_score)
                lines.append(f"   - Risk Level: {risk_level}")

            lines.append("")

        if state.requires_human_approval:
            lines.append("Note: This query requires human review before proceeding.")

        return "\n".join(lines)

    def _generate_comparison_response(self, state: ChatState) -> str:
        """Generate response for supplier comparison."""
        if not state.comparison_data:
            return "Unable to generate comparison. Please try again."

        data = state.comparison_data
        lines = ["**Supplier Comparison**\n"]

        for supplier in data.get("suppliers", []):
            lines.append(f"**{supplier['name']}**")
            scores = supplier.get("scores", {})
            lines.append(f"  - Quality: {scores.get('quality', 'N/A')}")
            lines.append(f"  - Delivery: {scores.get('delivery', 'N/A')}")
            lines.append(f"  - Risk Score: {scores.get('risk', 'N/A')}")

            if supplier.get("strengths"):
                lines.append(f"  - Strengths: {', '.join(supplier['strengths'])}")
            if supplier.get("weaknesses"):
                lines.append(f"  - Weaknesses: {', '.join(supplier['weaknesses'])}")
            lines.append("")

        rec = data.get("recommendation", {})
        if rec.get("supplier_name"):
            lines.append(f"**Recommendation:** {rec['supplier_name']}")
            lines.append(f"Rationale: {rec.get('rationale', 'Best overall score')}")

        return "\n".join(lines)

    def _generate_error_response(self, state: ChatState) -> str:
        """Generate error response."""
        return (
            f"I encountered an issue: {state.error}\n\n"
            "Please try rephrasing your request or contact support."
        )

    def _generate_generic_response(self, state: ChatState) -> str:
        """Generate generic response based on intent."""
        if state.intent == Intent.GREETING:
            return (
                "Hello! I'm the Valerie Supplier Assistant. I can help you find "
                "aerospace suppliers, check compliance, compare options, or answer "
                "technical questions. What would you like to know?"
            )

        if state.intent == Intent.UNKNOWN:
            return (
                "I'm not sure I understood your request. I can help with:\n"
                "- Finding suppliers with specific capabilities\n"
                "- Checking supplier certifications and compliance\n"
                "- Comparing multiple suppliers\n"
                "- Answering technical questions about aerospace processes\n\n"
                "Could you please clarify what you're looking for?"
            )

        return "I'm here to help with your supplier needs. What would you like to know?"

    def _risk_level(self, score: float) -> str:
        """Convert risk score to text level."""
        if score < 0.2:
            return "Low"
        elif score < 0.4:
            return "Moderate"
        elif score < 0.6:
            return "Elevated"
        elif score < 0.8:
            return "High"
        else:
            return "Critical"

    def _format_currency(self, amount: float) -> str:
        """Format a number as currency ($1,234.56)."""
        if amount == 0:
            return "N/A"
        return f"${amount:,.2f}"

    def _get_supplier_data(self, state: ChatState) -> dict[str, Any]:
        """Get supplier domain data from state."""
        return state.domain_data.get("supplier", {})

    def _parse_product_results(
        self, raw_results: list[dict[str, Any]]
    ) -> list[ProductResult]:
        """Parse raw product result dicts into ProductResult objects."""
        results = []
        for item in raw_results:
            suppliers = [
                SupplierPricing(**s) if isinstance(s, dict) else s
                for s in item.get("suppliers", [])
            ]
            results.append(
                ProductResult(
                    item_code=item.get("item_code", ""),
                    description=item.get("description", ""),
                    category=item.get("category", ""),
                    uom=item.get("uom", "EA"),
                    suppliers=suppliers,
                )
            )
        return results

    def _generate_product_search_response(self, state: ChatState) -> str:
        """Generate response for product search results.

        Formats product results with suppliers and prices in a readable format.
        """
        supplier_data = self._get_supplier_data(state)
        raw_results = supplier_data.get("product_search_results", [])

        if not raw_results:
            return (
                "No products found matching your search criteria. "
                "Try broadening your search or using different keywords."
            )

        products = self._parse_product_results(raw_results)
        lines = [f"Found {len(products)} product(s) matching your search:\n"]

        for i, product in enumerate(products, 1):
            lines.append(f"**{i}. {product.item_code}** - {product.description}")
            lines.append(f"   Category: {product.category}")
            lines.append(f"   Unit: {product.uom}")

            if product.suppliers:
                lines.append(f"   Suppliers ({len(product.suppliers)}):")

                # Sort suppliers by price
                sorted_suppliers = sorted(
                    product.suppliers,
                    key=lambda s: s.avg_price if s.avg_price > 0 else float("inf"),
                )

                for supplier in sorted_suppliers[:5]:  # Show top 5 suppliers
                    price_info = self._format_currency(supplier.avg_price)
                    if supplier.min_price > 0 and supplier.max_price > 0:
                        price_range = (
                            f" (range: {self._format_currency(supplier.min_price)} - "
                            f"{self._format_currency(supplier.max_price)})"
                        )
                    else:
                        price_range = ""
                    order_info = (
                        f" | {supplier.order_count} orders"
                        if supplier.order_count > 0
                        else ""
                    )
                    lines.append(
                        f"      - {supplier.supplier_name}: {price_info}{price_range}{order_info}"
                    )

                if len(product.suppliers) > 5:
                    lines.append(
                        f"      ... and {len(product.suppliers) - 5} more suppliers"
                    )

                # Add recommendation
                if sorted_suppliers and sorted_suppliers[0].avg_price > 0:
                    lines.append(
                        f"   Best price: {sorted_suppliers[0].supplier_name} "
                        f"at {self._format_currency(sorted_suppliers[0].avg_price)}"
                    )
            else:
                lines.append("   No supplier pricing available")

            lines.append("")

        lines.append(
            "Would you like more details on any specific product or supplier?"
        )
        return "\n".join(lines)

    def _generate_category_browse_response(self, state: ChatState) -> str:
        """Generate response for category browsing results.

        Shows category hierarchy in a clear, navigable format.
        """
        supplier_data = self._get_supplier_data(state)
        raw_result = supplier_data.get("category_results", {})

        if not raw_result:
            return (
                "No category information available. "
                "Please try a different category or browse from the top level."
            )

        # Parse the category results
        if isinstance(raw_result, dict):
            current_level = raw_result.get("current_level", 1)
            parent_category = raw_result.get("parent_category")
            raw_categories = raw_result.get("categories", [])
        else:
            current_level = raw_result.current_level
            parent_category = raw_result.parent_category
            raw_categories = [
                c.model_dump() if hasattr(c, "model_dump") else c
                for c in raw_result.categories
            ]

        if not raw_categories:
            return (
                "No subcategories found at this level. "
                "This may be the most detailed category level available."
            )

        # Build hierarchy indicator
        level_names = {1: "Top-Level", 2: "Mid-Level", 3: "Detailed"}
        level_name = level_names.get(current_level, f"Level {current_level}")

        lines = []
        if parent_category:
            lines.append(f"**Browsing: {parent_category}** ({level_name} Categories)\n")
        else:
            lines.append(f"**{level_name} Categories**\n")

        # Create category table
        lines.append("| Category | Items | Suppliers | Total Spend |")
        lines.append("|----------|------:|----------:|------------:|")

        for cat_data in raw_categories:
            if isinstance(cat_data, dict):
                name = cat_data.get("name", "Unknown")
                item_count = cat_data.get("item_count", 0)
                supplier_count = cat_data.get("supplier_count", 0)
                total_amount = cat_data.get("total_amount", 0.0)
            else:
                name = cat_data.name
                item_count = cat_data.item_count
                supplier_count = cat_data.supplier_count
                total_amount = cat_data.total_amount

            lines.append(
                f"| {name} | {item_count:,} | {supplier_count:,} | "
                f"{self._format_currency(total_amount)} |"
            )

        lines.append("")

        # Add navigation hints
        if current_level < 3:
            lines.append(
                "You can drill down into any category for more details. "
                "Just ask about a specific category name."
            )
        else:
            lines.append(
                "This is the most detailed category level. "
                "You can search for products within these categories."
            )

        return "\n".join(lines)

    def _generate_supplier_detail_response(self, state: ChatState) -> str:
        """Generate comprehensive supplier information response.

        Shows detailed supplier profile including orders, categories, and items.
        """
        supplier_data = self._get_supplier_data(state)
        raw_detail = supplier_data.get("supplier_detail", {})

        if not raw_detail:
            return (
                "No supplier details available. "
                "Please provide a supplier name to look up."
            )

        # Parse supplier detail
        if isinstance(raw_detail, dict):
            detail = SupplierDetailResult(**raw_detail)
        else:
            detail = raw_detail

        lines = [f"**Supplier Profile: {detail.name}**\n"]

        if detail.site:
            lines.append(f"Site: {detail.site}\n")

        # Order statistics
        lines.append("**Order Summary**")
        lines.append(f"- Total Orders: {detail.total_orders:,}")
        lines.append(f"- Total Spend: {self._format_currency(detail.total_amount)}")
        lines.append(
            f"- Average Order Value: {self._format_currency(detail.avg_order_value)}"
        )

        if detail.first_order_date:
            lines.append(
                f"- First Order: {detail.first_order_date.strftime('%Y-%m-%d')}"
            )
        if detail.last_order_date:
            lines.append(
                f"- Last Order: {detail.last_order_date.strftime('%Y-%m-%d')}"
            )

        # Market position
        if detail.rank_by_volume:
            lines.append(f"\n**Market Position**")
            lines.append(f"- Rank by Volume: #{detail.rank_by_volume}")
            if detail.market_share > 0:
                lines.append(f"- Market Share: {detail.market_share:.1f}%")

        # Top categories
        if detail.top_categories:
            lines.append(f"\n**Top Categories**")
            for cat in detail.top_categories[:5]:
                if isinstance(cat, dict):
                    cat_name = cat.get("name", "Unknown")
                    cat_amount = cat.get("total_amount", 0.0)
                else:
                    cat_name = cat.name
                    cat_amount = cat.total_amount
                lines.append(f"- {cat_name}: {self._format_currency(cat_amount)}")

        # Top items
        if detail.top_items:
            lines.append(f"\n**Most Purchased Items**")
            for item in detail.top_items[:5]:
                if isinstance(item, dict):
                    item_code = item.get("item_code", "")
                    item_desc = item.get("description", "")
                else:
                    item_code = item.item_code
                    item_desc = item.description
                lines.append(f"- {item_code}: {item_desc}")

        lines.append(
            "\nWould you like to compare this supplier with others or see their pricing?"
        )
        return "\n".join(lines)

    def _generate_top_suppliers_response(self, state: ChatState) -> str:
        """Generate supplier ranking table response.

        Shows suppliers ranked by the specified metric.
        """
        supplier_data = self._get_supplier_data(state)
        raw_rankings = supplier_data.get("top_suppliers_result", [])

        if not raw_rankings:
            return (
                "No supplier rankings available. "
                "Please specify what you'd like to rank suppliers by "
                "(e.g., total spend, order count)."
            )

        # Parse rankings
        rankings = []
        for item in raw_rankings:
            if isinstance(item, dict):
                rankings.append(SupplierRanking(**item))
            else:
                rankings.append(item)

        # Get metric name from first ranking
        metric_name = rankings[0].metric_name if rankings else "value"
        metric_display = {
            "total_amount": "Total Spend",
            "order_count": "Orders",
            "item_count": "Unique Items",
        }.get(metric_name, metric_name.replace("_", " ").title())

        lines = [f"**Top Suppliers by {metric_display}**\n"]

        # Create ranking table
        lines.append(f"| Rank | Supplier | {metric_display} |")
        lines.append("|-----:|----------|----------------:|")

        for ranking in rankings:
            # Format metric value appropriately
            if metric_name == "total_amount":
                value_str = self._format_currency(ranking.metric_value)
            elif metric_name in ("order_count", "item_count"):
                value_str = f"{int(ranking.metric_value):,}"
            else:
                value_str = f"{ranking.metric_value:,.2f}"

            lines.append(f"| {ranking.rank} | {ranking.supplier_name} | {value_str} |")

        lines.append("")

        # Add insights
        if len(rankings) >= 2:
            top = rankings[0]
            if metric_name == "total_amount":
                total_top = sum(r.metric_value for r in rankings)
                if total_top > 0:
                    top_share = (top.metric_value / total_top) * 100
                    lines.append(
                        f"**{top.supplier_name}** leads with "
                        f"{top_share:.1f}% of the total among top suppliers."
                    )

        lines.append(
            "\nWould you like detailed information on any of these suppliers?"
        )
        return "\n".join(lines)

    def _generate_price_comparison_response(self, state: ChatState) -> str:
        """Generate price comparison across suppliers response.

        Shows side-by-side pricing comparison for items.
        """
        supplier_data = self._get_supplier_data(state)
        raw_comparisons = supplier_data.get("price_comparison", [])

        if not raw_comparisons:
            return (
                "No price comparison data available. "
                "Please specify which items you'd like to compare prices for."
            )

        # Parse comparisons
        comparisons = []
        for item in raw_comparisons:
            if isinstance(item, dict):
                suppliers = [
                    SupplierPricing(**s) if isinstance(s, dict) else s
                    for s in item.get("suppliers", [])
                ]
                comparisons.append(
                    PriceComparison(
                        item_code=item.get("item_code", ""),
                        item_description=item.get("item_description", ""),
                        suppliers=suppliers,
                        lowest_price_supplier=item.get("lowest_price_supplier"),
                        price_range=tuple(item.get("price_range", (0.0, 0.0))),
                    )
                )
            else:
                comparisons.append(item)

        lines = ["**Price Comparison**\n"]

        for comparison in comparisons:
            lines.append(
                f"**{comparison.item_code}** - {comparison.item_description}\n"
            )

            if not comparison.suppliers:
                lines.append("No supplier pricing available for this item.\n")
                continue

            # Create price table
            lines.append("| Supplier | Avg Price | Min | Max | Orders |")
            lines.append("|----------|----------:|----:|----:|-------:|")

            # Sort suppliers by average price
            sorted_suppliers = sorted(
                comparison.suppliers,
                key=lambda s: s.avg_price if s.avg_price > 0 else float("inf"),
            )

            for supplier in sorted_suppliers:
                avg_price = self._format_currency(supplier.avg_price)
                min_price = self._format_currency(supplier.min_price)
                max_price = self._format_currency(supplier.max_price)
                orders = f"{supplier.order_count:,}" if supplier.order_count > 0 else "-"

                # Mark the best price
                marker = " *" if supplier.avg_price == sorted_suppliers[0].avg_price else ""
                lines.append(
                    f"| {supplier.supplier_name}{marker} | {avg_price} | "
                    f"{min_price} | {max_price} | {orders} |"
                )

            lines.append("")

            # Add recommendation
            if comparison.lowest_price_supplier:
                lines.append(
                    f"**Recommended:** {comparison.lowest_price_supplier} "
                    f"offers the best price."
                )

            # Price range insight
            if comparison.price_range[0] > 0 and comparison.price_range[1] > 0:
                low, high = comparison.price_range
                if high > low:
                    savings = ((high - low) / high) * 100
                    lines.append(
                        f"Price range: {self._format_currency(low)} - "
                        f"{self._format_currency(high)} "
                        f"(potential savings: {savings:.1f}%)"
                    )

            lines.append("")

        lines.append("* Best price")
        lines.append(
            "\nWould you like more details on any supplier or help with procurement?"
        )
        return "\n".join(lines)
