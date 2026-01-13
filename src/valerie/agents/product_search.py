"""Product Search agent - searches for products and their suppliers."""

import logging
import re
from datetime import datetime

from ..data.factory import get_default_data_source
from ..data.interfaces import ProductResult as DataProductResult
from ..data.interfaces import ProductWithSuppliers
from ..models import ChatState, Intent
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ProductSearchAgent(BaseAgent):
    """Searches for products and their suppliers based on user queries.

    This agent handles:
    - PRODUCT_SEARCH: Find products/items matching a query
    - PRICE_INQUIRY: Get pricing info for a specific item with supplier details
    """

    name = "product_search"

    def get_system_prompt(self) -> str:
        return """You are a Product Search Agent for a procurement recommendation system.

Your role is to:
1. Search for products/items matching user queries
2. Find suppliers that offer specific products
3. Provide pricing information across different suppliers
4. Help users compare products and prices

When searching:
- Extract the main product query from the user's message
- Identify any category filters mentioned
- Look for specific item codes if mentioned

Always present results clearly with:
- Item code and description
- Category
- Number of suppliers
- Price range (if available)"""

    async def process(self, state: ChatState) -> ChatState:
        """Search for products based on the user's query."""
        start_time = datetime.now()

        try:
            # Get the data source
            data_source = get_default_data_source()

            # Extract query from user message
            user_message = self._get_latest_user_message(state)
            query = self._extract_product_query(user_message, state)
            category = state.entities.get("category")
            limit = state.entities.get("limit", 20)

            logger.info(f"ProductSearchAgent: Searching for '{query}' in category '{category}'")

            # Determine which operation to perform based on intent
            if state.intent == Intent.PRICE_INQUIRY:
                # Price inquiry - get product with suppliers and pricing
                result = await self._handle_price_inquiry(data_source, query, state)
            else:
                # Product search - find matching products
                result = await self._handle_product_search(
                    data_source, query, category, limit, state
                )

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data=result,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"ProductSearchAgent error: {e}")
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=str(e),
                start_time=start_time,
            )

        return state

    async def _handle_product_search(
        self,
        data_source,
        query: str,
        category: str | None,
        limit: int,
        state: ChatState,
    ) -> dict:
        """Handle PRODUCT_SEARCH intent."""
        # Search for products
        products = await data_source.search_products(
            query=query,
            category=category,
            limit=limit,
        )

        # Convert to state-compatible format and store in domain data
        product_results = self._convert_products_to_state_format(products)

        # Store results in domain_data["supplier"]["product_search_results"]
        supplier_state = state.domain_data.get("supplier", {})
        supplier_state["product_search_results"] = [p.model_dump() for p in product_results]
        state.domain_data["supplier"] = supplier_state

        return {
            "query": query,
            "category": category,
            "results_count": len(products),
            "products": [self._format_product_for_display(p) for p in products],
        }

    async def _handle_price_inquiry(
        self,
        data_source,
        query: str,
        state: ChatState,
    ) -> dict:
        """Handle PRICE_INQUIRY intent - get product with suppliers and prices."""
        # First try to find by exact item code
        item_code = self._extract_item_code(query)

        if item_code:
            # Direct lookup by item code
            product_with_suppliers = await data_source.get_product_suppliers(item_code)
            if product_with_suppliers:
                return self._format_price_inquiry_result(product_with_suppliers, state)

        # If no exact match, search for products first
        products = await data_source.search_products(query=query, limit=5)

        if not products:
            return {
                "query": query,
                "found": False,
                "message": f"No se encontraron productos que coincidan con '{query}'",
            }

        # Get the first matching product's suppliers
        first_product = products[0]
        product_with_suppliers = await data_source.get_product_suppliers(first_product.item_code)

        if product_with_suppliers:
            return self._format_price_inquiry_result(product_with_suppliers, state)

        # Return basic product info without supplier details
        return {
            "query": query,
            "found": True,
            "item_code": first_product.item_code,
            "description": first_product.description,
            "category": first_product.category,
            "avg_price": first_product.avg_price,
            "supplier_count": first_product.supplier_count,
            "suppliers": [],
        }

    def _format_price_inquiry_result(
        self,
        product: ProductWithSuppliers,
        state: ChatState,
    ) -> dict:
        """Format price inquiry result with supplier pricing details."""
        # Store in domain state
        from ..domains.supplier.state import ProductResult, SupplierPricing

        supplier_pricing_list = [
            SupplierPricing(
                supplier_name=s.supplier_name,
                avg_price=s.avg_price,
                min_price=s.min_price,
                max_price=s.max_price,
                order_count=s.order_count,
                last_order_date=s.last_order_date,
            )
            for s in product.suppliers
        ]

        product_result = ProductResult(
            item_code=product.item_code,
            description=product.description,
            category=product.category,
            uom=product.uom,
            suppliers=supplier_pricing_list,
        )

        # Store in domain_data
        supplier_state = state.domain_data.get("supplier", {})
        supplier_state["product_search_results"] = [product_result.model_dump()]
        state.domain_data["supplier"] = supplier_state

        # Find lowest price supplier
        lowest_price_supplier = None
        if product.suppliers:
            lowest = min(product.suppliers, key=lambda s: s.avg_price if s.avg_price > 0 else float('inf'))
            lowest_price_supplier = lowest.supplier_name

        return {
            "query": product.item_code,
            "found": True,
            "item_code": product.item_code,
            "description": product.description,
            "category": product.category,
            "uom": product.uom,
            "supplier_count": len(product.suppliers),
            "lowest_price_supplier": lowest_price_supplier,
            "suppliers": [
                {
                    "name": s.supplier_name,
                    "avg_price": s.avg_price,
                    "min_price": s.min_price,
                    "max_price": s.max_price,
                    "order_count": s.order_count,
                    "last_order_date": s.last_order_date.isoformat() if s.last_order_date else None,
                }
                for s in product.suppliers
            ],
        }

    def _convert_products_to_state_format(
        self,
        products: list[DataProductResult],
    ) -> list:
        """Convert data source products to state format."""
        from ..domains.supplier.state import ProductResult

        return [
            ProductResult(
                item_code=p.item_code,
                description=p.description,
                category=p.category,
                uom=p.uom,
                suppliers=[],  # Basic search doesn't include supplier details
            )
            for p in products
        ]

    def _format_product_for_display(self, product: DataProductResult) -> dict:
        """Format a product for display in the response."""
        return {
            "item_code": product.item_code,
            "description": product.description,
            "category": product.category,
            "uom": product.uom,
            "avg_price": product.avg_price,
            "min_price": product.min_price,
            "max_price": product.max_price,
            "supplier_count": product.supplier_count,
        }

    def _get_latest_user_message(self, state: ChatState) -> str:
        """Extract the latest user message from state."""
        if not state.messages:
            return ""

        # Find the last human message
        for msg in reversed(state.messages):
            if hasattr(msg, "type") and msg.type == "human":
                return str(msg.content)
            elif hasattr(msg, "role") and msg.role == "user":
                return str(msg.content)
            elif isinstance(msg, dict) and msg.get("role") == "user":
                return str(msg.get("content", ""))

        return ""

    def _extract_product_query(self, user_message: str, state: ChatState) -> str:
        """Extract the product query from user message or entities."""
        # First check entities for explicit product name
        if state.entities.get("product"):
            return state.entities["product"]

        if state.entities.get("item_code"):
            return state.entities["item_code"]

        if state.entities.get("product_name"):
            return state.entities["product_name"]

        # Extract from common question patterns (Spanish and English)
        patterns = [
            r"(?:quien|quién|quienes?)\s+(?:vende|venden|tiene|tienen)\s+(.+?)(?:\?|$)",
            r"(?:busco|necesito|quiero)\s+(?:proveedores?\s+de\s+)?(.+?)(?:\?|$)",
            r"(?:donde|dónde)\s+(?:puedo\s+)?(?:comprar|conseguir)\s+(.+?)(?:\?|$)",
            r"(?:precio|precios|costo|costos)\s+(?:de[l]?\s+)?(.+?)(?:\?|$)",
            r"(?:cuanto|cuánto)\s+cuesta\s+(?:el\s+|la\s+)?(.+?)(?:\?|$)",
            r"(?:suppliers?|vendors?)\s+(?:for|of)\s+(.+?)(?:\?|$)",
            r"(?:find|search|look for)\s+(.+?)(?:\?|$)",
            r"(?:price|cost)\s+(?:of|for)\s+(.+?)(?:\?|$)",
            r"(?:who\s+sells?|who\s+has)\s+(.+?)(?:\?|$)",
        ]

        message_lower = user_message.lower()
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no pattern matches, use the whole message as query
        # (removing common question words)
        cleaned = re.sub(
            r"^(quien|quienes?|busco|necesito|donde|dónde|cuanto|cuánto|precio|costo|"
            r"find|search|look for|price|cost|suppliers?|vendors?)\s+",
            "",
            message_lower,
            flags=re.IGNORECASE,
        )
        return cleaned.strip() or user_message

    def _extract_item_code(self, query: str) -> str | None:
        """Try to extract an item code from the query."""
        # Common item code patterns (alphanumeric with dashes or underscores)
        patterns = [
            r"\b([A-Z]{2,4}[-_]?\d{4,8})\b",  # e.g., ITM-12345, ABC1234
            r"\b(\d{6,10})\b",  # Pure numeric codes
            r"\b([A-Z0-9]{8,})\b",  # Mixed alphanumeric 8+ chars
        ]

        for pattern in patterns:
            match = re.search(pattern, query.upper())
            if match:
                return match.group(1)

        return None
