"""Category Browse agent - browses product categories hierarchically."""

import logging
from datetime import datetime
from typing import Any

from ....agents.base import BaseAgent
from ....data.factory import get_default_data_source
from ....data.interfaces import CategoryResult, SupplierResult
from ....models import ChatState
from ..state import CategoryBrowseResult, CategoryInfo, SupplierStateExtension

logger = logging.getLogger(__name__)


class CategoryBrowseAgent(BaseAgent):
    """Browses product categories hierarchically.

    This agent handles the CATEGORY_BROWSE intent and allows users to:
    - View top-level categories (level=1)
    - Drill down into subcategories
    - View suppliers for a specific category

    Example interactions:
    - "What categories are available?" -> Shows level 1 categories
    - "Show me Chemicals" -> Drills into Chemicals subcategories
    - "Who sells Acetone?" -> Shows suppliers for Acetone category
    """

    name = "category_browse"

    def get_system_prompt(self) -> str:
        return """You are a Category Browse Agent for a procurement system.

Your role is to help users navigate the product category hierarchy:

Category Hierarchy:
- Level 1: Top-level categories (e.g., Controlled Material, Equipment, Services)
- Level 2: Subcategories (e.g., Chemicals, Metals, Electronics)
- Level 3: Specific items (e.g., Acetone, Isopropyl Alcohol, Steel Plates)

Navigation Actions:
1. Show top-level categories when user asks "what categories?" or similar
2. Drill down when user mentions a specific category
3. Show suppliers when user asks "who sells X?" or at leaf categories

Response Format:
- Present categories in a clear hierarchical view
- Show breadcrumb navigation (e.g., "Controlled Material > Chemicals > Acetone")
- Include counts (items, suppliers) when available
- Offer navigation hints (drill down, go back, see suppliers)"""

    async def process(self, state: ChatState) -> ChatState:
        """Process category browse request."""
        start_time = datetime.now()

        try:
            # Get the data source
            data_source = get_default_data_source()

            # Extract category request from entities
            requested_category = state.entities.get("category")
            show_suppliers = state.entities.get("show_suppliers", False)
            parent_category = state.entities.get("parent_category")

            # Get current navigation context from state if exists
            current_context = self._get_current_context(state)

            # Determine what to show based on context
            if show_suppliers and requested_category:
                # User wants to see suppliers for a category
                result = await self._get_category_suppliers(
                    data_source, requested_category, current_context
                )
            elif requested_category:
                # User wants to drill into a specific category
                result = await self._drill_into_category(
                    data_source, requested_category, current_context
                )
            else:
                # Show top-level or current level categories
                result = await self._browse_categories(
                    data_source, parent_category, current_context
                )

            # Store results in state
            self._update_state_with_result(state, result)

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={
                    "current_level": result.current_level,
                    "categories_count": len(result.categories),
                    "parent": result.parent_category,
                    "formatted_output": self._format_category_tree(result),
                },
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Category browse error: {e}", exc_info=True)
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=str(e),
                start_time=start_time,
            )

        return state

    def _get_current_context(self, state: ChatState) -> dict[str, Any]:
        """Get the current navigation context from state."""
        # Try to get supplier extension state
        domain_data = state.entities.get("domain_data", {})
        supplier_data = domain_data.get("supplier", {})

        current_result = supplier_data.get("category_results")
        if current_result and isinstance(current_result, dict):
            return {
                "current_level": current_result.get("current_level", 1),
                "parent_category": current_result.get("parent_category"),
                "breadcrumb": current_result.get("breadcrumb", []),
            }

        return {
            "current_level": 1,
            "parent_category": None,
            "breadcrumb": [],
        }

    async def _browse_categories(
        self,
        data_source,
        parent: str | None,
        context: dict[str, Any],
    ) -> CategoryBrowseResult:
        """Browse categories at a specific level."""
        if parent:
            # Get subcategories of the parent
            categories = await data_source.get_categories(parent=parent)
            current_level = context.get("current_level", 1) + 1
        else:
            # Get top-level categories
            categories = await data_source.get_categories(level=1)
            current_level = 1

        return CategoryBrowseResult(
            current_level=current_level,
            categories=self._convert_categories(categories),
            parent_category=parent,
        )

    async def _drill_into_category(
        self,
        data_source,
        category_name: str,
        context: dict[str, Any],
    ) -> CategoryBrowseResult:
        """Drill into a specific category to see its subcategories."""
        # Get subcategories
        categories = await data_source.get_categories(parent=category_name)

        # Determine the level we're drilling into
        parent_level = context.get("current_level", 1)
        new_level = min(parent_level + 1, 3)  # Max 3 levels

        # If no subcategories, stay at current level but show this category's info
        if not categories:
            # Try to get the category itself
            all_cats = await data_source.get_categories()
            category = next(
                (c for c in all_cats if c.name.lower() == category_name.lower()),
                None
            )
            if category:
                return CategoryBrowseResult(
                    current_level=category.level,
                    categories=[self._convert_category(category)],
                    parent_category=category.parent,
                )

        return CategoryBrowseResult(
            current_level=new_level,
            categories=self._convert_categories(categories),
            parent_category=category_name,
        )

    async def _get_category_suppliers(
        self,
        data_source,
        category_name: str,
        context: dict[str, Any],
    ) -> CategoryBrowseResult:
        """Get suppliers for a specific category."""
        # Get suppliers for the category
        suppliers = await data_source.get_category_suppliers(category_name, limit=20)

        # Also get the category info
        all_cats = await data_source.get_categories()
        category = next(
            (c for c in all_cats if c.name.lower() == category_name.lower()),
            None
        )

        result = CategoryBrowseResult(
            current_level=category.level if category else 3,
            categories=[self._convert_category(category)] if category else [],
            parent_category=category.parent if category else None,
        )

        # Store suppliers info in the category
        if result.categories and suppliers:
            result.categories[0].supplier_count = len(suppliers)

        return result

    def _convert_categories(self, categories: list[CategoryResult]) -> list[CategoryInfo]:
        """Convert data source CategoryResult to state CategoryInfo."""
        return [self._convert_category(cat) for cat in categories]

    def _convert_category(self, category: CategoryResult) -> CategoryInfo:
        """Convert a single CategoryResult to CategoryInfo."""
        return CategoryInfo(
            name=category.name,
            level=category.level,
            parent=category.parent,
            item_count=category.item_count,
            supplier_count=category.supplier_count,
            total_amount=category.total_amount,
        )

    def _update_state_with_result(
        self,
        state: ChatState,
        result: CategoryBrowseResult,
    ) -> None:
        """Update the state with category browse results.

        Note: This updates the domain_data["supplier"] in a way that's
        compatible with both ChatState and CoreState patterns.
        """
        # For ChatState compatibility, store in entities for now
        # The response generator can pick this up
        state.entities["category_browse_result"] = result.model_dump()

        # Also try to update domain data if available
        if hasattr(state, "domain_data"):
            if "supplier" not in state.domain_data:
                state.domain_data["supplier"] = {}
            state.domain_data["supplier"]["category_results"] = result.model_dump()

    def _format_category_tree(self, result: CategoryBrowseResult) -> str:
        """Format the category tree for display.

        Creates a nicely formatted string representation of the category
        hierarchy for user display.
        """
        lines = []

        # Add breadcrumb if we have a parent
        if result.parent_category:
            lines.append(f"Browsing: {result.parent_category}")
            lines.append("-" * 40)

        if not result.categories:
            lines.append("No categories found.")
            return "\n".join(lines)

        # Determine if we're at a leaf level
        is_leaf_level = result.current_level >= 3

        # Format each category
        for i, cat in enumerate(result.categories, 1):
            prefix = self._get_level_prefix(cat.level)

            # Build category line
            line_parts = [f"{prefix}{i}. {cat.name}"]

            # Add stats
            stats = []
            if cat.item_count > 0:
                stats.append(f"{cat.item_count} items")
            if cat.supplier_count > 0:
                stats.append(f"{cat.supplier_count} suppliers")
            if cat.total_amount > 0:
                stats.append(f"${cat.total_amount:,.2f} total")

            if stats:
                line_parts.append(f" ({', '.join(stats)})")

            lines.append("".join(line_parts))

        # Add navigation hints
        lines.append("")
        if is_leaf_level:
            lines.append("Tip: Ask 'who sells [category]?' to see suppliers")
        else:
            lines.append("Tip: Say a category name to drill down further")

        if result.parent_category:
            lines.append("Tip: Ask 'go back' to return to parent category")

        return "\n".join(lines)

    def _get_level_prefix(self, level: int) -> str:
        """Get visual prefix based on category level."""
        if level == 1:
            return ""
        elif level == 2:
            return "  "
        else:
            return "    "

    def _build_breadcrumb(
        self,
        category: CategoryResult | None,
        current_breadcrumb: list[str],
    ) -> list[str]:
        """Build a breadcrumb trail for navigation."""
        if not category:
            return current_breadcrumb

        new_breadcrumb = list(current_breadcrumb)

        # Add parent hierarchy
        if category.level1 and category.level1 not in new_breadcrumb:
            new_breadcrumb = [category.level1]
        if category.level2 and category.level2 not in new_breadcrumb:
            if len(new_breadcrumb) < 2:
                new_breadcrumb.append(category.level2)
        if category.level3 and category.level3 not in new_breadcrumb:
            if len(new_breadcrumb) < 3:
                new_breadcrumb.append(category.level3)

        return new_breadcrumb

    def format_breadcrumb(self, breadcrumb: list[str]) -> str:
        """Format breadcrumb for display."""
        if not breadcrumb:
            return "Categories"
        return " > ".join(["Categories"] + breadcrumb)
