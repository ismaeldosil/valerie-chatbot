"""Supplier domain intent definitions.

These intents represent the different types of requests users can make
in the supplier management domain.
"""

from enum import Enum


class SupplierIntent(str, Enum):
    """User intent classifications for supplier domain."""

    # Core supplier operations
    SUPPLIER_SEARCH = "supplier_search"
    SUPPLIER_COMPARISON = "supplier_comparison"
    COMPLIANCE_CHECK = "compliance_check"
    RISK_ASSESSMENT = "risk_assessment"
    TECHNICAL_QUESTION = "technical_question"

    # Product and category intents
    PRODUCT_SEARCH = "product_search"        # "¿Quién vende acetona?"
    CATEGORY_BROWSE = "category_browse"       # "¿Qué categorías de químicos hay?"
    PRICE_INQUIRY = "price_inquiry"           # "¿Cuánto cuesta el item X?"
    SUPPLIER_DETAIL = "supplier_detail"       # "Dame info de Grainger"
    TOP_SUPPLIERS = "top_suppliers"           # "Top 10 suppliers por volumen"
    ITEM_COMPARISON = "item_comparison"       # "Compara precios de guantes"

    # Common intents (shared with other domains)
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "SupplierIntent":
        """Convert a string to SupplierIntent.

        Args:
            value: The intent string.

        Returns:
            The corresponding SupplierIntent.
        """
        try:
            return cls(value)
        except ValueError:
            # Try matching by name
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
            return cls.UNKNOWN

    def is_domain_specific(self) -> bool:
        """Check if this is a supplier-specific intent."""
        return self in {
            self.SUPPLIER_SEARCH,
            self.SUPPLIER_COMPARISON,
            self.COMPLIANCE_CHECK,
            self.RISK_ASSESSMENT,
            self.TECHNICAL_QUESTION,
            self.PRODUCT_SEARCH,
            self.CATEGORY_BROWSE,
            self.PRICE_INQUIRY,
            self.SUPPLIER_DETAIL,
            self.TOP_SUPPLIERS,
            self.ITEM_COMPARISON,
        }

    def requires_data_lookup(self) -> bool:
        """Check if this intent requires external data lookup."""
        return self in {
            self.SUPPLIER_SEARCH,
            self.SUPPLIER_COMPARISON,
            self.COMPLIANCE_CHECK,
            self.RISK_ASSESSMENT,
            self.PRODUCT_SEARCH,
            self.CATEGORY_BROWSE,
            self.PRICE_INQUIRY,
            self.SUPPLIER_DETAIL,
            self.TOP_SUPPLIERS,
            self.ITEM_COMPARISON,
        }

    def is_product_related(self) -> bool:
        """Check if this intent is product-related."""
        return self in {
            self.PRODUCT_SEARCH,
            self.PRICE_INQUIRY,
            self.ITEM_COMPARISON,
        }

    def is_category_related(self) -> bool:
        """Check if this intent is category-related."""
        return self in {
            self.CATEGORY_BROWSE,
        }

    def is_supplier_info(self) -> bool:
        """Check if this intent is for supplier information."""
        return self in {
            self.SUPPLIER_DETAIL,
            self.TOP_SUPPLIERS,
        }


# Example queries for each new intent
INTENT_EXAMPLES: dict[SupplierIntent, list[str]] = {
    SupplierIntent.PRODUCT_SEARCH: [
        "¿Quién vende acetona?",
        "Busco proveedores de guantes de nitrilo",
        "¿Dónde puedo comprar alcohol isopropílico?",
        "Necesito encontrar quien vende EPP",
    ],
    SupplierIntent.CATEGORY_BROWSE: [
        "¿Qué categorías de químicos hay?",
        "Muéstrame las categorías disponibles",
        "¿Qué tipos de productos de limpieza tienen?",
        "Lista de categorías de materiales",
    ],
    SupplierIntent.PRICE_INQUIRY: [
        "¿Cuánto cuesta el item X?",
        "¿Cuál es el precio de la acetona?",
        "Dame el costo de los guantes de látex",
        "Precio unitario del alcohol gel",
    ],
    SupplierIntent.SUPPLIER_DETAIL: [
        "Dame info de Grainger",
        "Información del proveedor ABC",
        "¿Qué datos tienen de Químicos del Norte?",
        "Detalles del supplier 12345",
    ],
    SupplierIntent.TOP_SUPPLIERS: [
        "Top 10 suppliers por volumen",
        "¿Cuáles son los mejores proveedores?",
        "Ranking de proveedores por ventas",
        "Los 5 proveedores más grandes",
    ],
    SupplierIntent.ITEM_COMPARISON: [
        "Compara precios de guantes",
        "Diferencia entre acetona de proveedor A y B",
        "¿Qué proveedor tiene mejor precio en EPP?",
        "Comparativa de costos de alcohol",
    ],
}
