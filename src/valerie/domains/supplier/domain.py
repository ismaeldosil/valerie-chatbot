"""Supplier management domain implementation.

This module implements the BaseDomain interface for the supplier
management business domain.
"""

from enum import Enum

from ...core.domain.base import BaseDomain, DomainAgentConfig, DomainStateExtension
from .intents import SupplierIntent
from .state import SupplierStateExtension


class SupplierDomain(BaseDomain):
    """Supplier management domain.

    This domain provides functionality for:
    - Supplier search and discovery
    - Supplier comparison and evaluation
    - Compliance verification
    - Risk assessment
    - Technical supplier questions
    """

    domain_id = "supplier"
    display_name = "Supplier Management"
    description = (
        "Manage suppliers, check compliance, compare options, "
        "and get technical information about supply chain."
    )
    version = "2.0.0"

    # Domain capabilities
    supports_hitl = True
    supports_streaming = True
    requires_auth = False

    def get_intent_enum(self) -> type[Enum]:
        """Return the SupplierIntent enum."""
        return SupplierIntent

    def get_state_extension(self) -> type[DomainStateExtension]:
        """Return the SupplierStateExtension class."""
        return SupplierStateExtension

    def get_agent_configs(self) -> list[DomainAgentConfig]:
        """Return configuration for supplier domain agents."""
        return [
            DomainAgentConfig(
                agent_class="valerie.agents.intent_classifier.IntentClassifierAgent",
                name="intent_classifier",
                description="Classifies user intent for supplier queries",
                handles_intents=[],  # Handles routing, not specific intents
                priority=100,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.orchestrator.OrchestratorAgent",
                name="orchestrator",
                description="Orchestrates supplier query workflows",
                handles_intents=[],  # Handles all intents
                priority=90,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.supplier_search.SupplierSearchAgent",
                name="supplier_search",
                description="Searches for suppliers based on criteria",
                handles_intents=[SupplierIntent.SUPPLIER_SEARCH.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.comparison.ComparisonAgent",
                name="comparison",
                description="Compares multiple suppliers",
                handles_intents=[SupplierIntent.SUPPLIER_COMPARISON.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.compliance_checker.ComplianceCheckerAgent",
                name="compliance_checker",
                description="Checks supplier compliance status",
                handles_intents=[SupplierIntent.COMPLIANCE_CHECK.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.risk_assessment.RiskAssessmentAgent",
                name="risk_assessment",
                description="Assesses supplier risks",
                handles_intents=[SupplierIntent.RISK_ASSESSMENT.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.technical.TechnicalAgent",
                name="technical",
                description="Answers technical supplier questions",
                handles_intents=[SupplierIntent.TECHNICAL_QUESTION.value],
                priority=50,
            ),
            # New data-driven agents (Sprint 17)
            DomainAgentConfig(
                agent_class="valerie.agents.product_search.ProductSearchAgent",
                name="product_search",
                description="Searches for products and their suppliers",
                handles_intents=[
                    SupplierIntent.PRODUCT_SEARCH.value,
                    SupplierIntent.PRICE_INQUIRY.value,
                ],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.domains.supplier.agents.category_browse.CategoryBrowseAgent",
                name="category_browse",
                description="Browses product categories and hierarchy",
                handles_intents=[SupplierIntent.CATEGORY_BROWSE.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.supplier_detail.SupplierDetailAgent",
                name="supplier_detail",
                description="Provides detailed supplier information and rankings",
                handles_intents=[
                    SupplierIntent.SUPPLIER_DETAIL.value,
                    SupplierIntent.TOP_SUPPLIERS.value,
                    SupplierIntent.ITEM_COMPARISON.value,
                ],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.response_generation.ResponseGenerationAgent",
                name="response_generator",
                description="Generates user-friendly responses",
                priority=10,
            ),
            # Infrastructure agents (shared but configured per domain)
            DomainAgentConfig(
                agent_class="valerie.agents.guardrails.GuardrailsAgent",
                name="guardrails",
                description="Content safety and policy enforcement",
                priority=95,
            ),
            DomainAgentConfig(
                agent_class="valerie.agents.hitl.HITLAgent",
                name="hitl",
                description="Human-in-the-loop coordination",
                requires_hitl=True,
                priority=80,
            ),
        ]

    def get_keywords(self) -> list[str]:
        """Return keywords that identify the supplier domain."""
        return [
            # Core terms
            "supplier",
            "vendor",
            "procurement",
            "supply chain",
            "sourcing",
            "proveedor",
            # Compliance terms
            "compliance",
            "certification",
            "nadcap",
            "as9100",
            "itar",
            "iso",
            "audit",
            # Risk terms
            "risk",
            "assessment",
            "mitigation",
            # Process terms
            "onboarding",
            "qualification",
            "evaluation",
            # Aerospace-specific
            "oem",
            "aerospace",
            "manufacturing",
            "parts",
            "materials",
            # Product/Category terms (Sprint 17)
            "product",
            "item",
            "category",
            "price",
            "cost",
            "chemicals",
            "gloves",
            "safety",
            "controlled material",
            "non-controlled",
            "quien vende",
            "cuanto cuesta",
            "precio",
            "acetone",
            "acetona",
        ]

    def get_example_queries(self) -> list[str]:
        """Return example queries for the supplier domain."""
        return [
            # Supplier search
            "Find suppliers with NADCAP certification in California",
            "Who can manufacture titanium components?",
            "List AS9100 certified vendors",
            # Comparison
            "Compare Acme Corp and Beta Industries",
            "Which supplier has better on-time delivery?",
            # Compliance
            "Check if SupplierX is ITAR compliant",
            "Which certifications does ABC Corp have?",
            "Are there any expiring certifications?",
            # Risk
            "Assess risk for our top 5 suppliers",
            "What are the mitigation options for SupplierY?",
            # Technical
            "What materials does ZCorp specialize in?",
            "What is SupplierQ's lead time for custom parts?",
            # Product search (Sprint 17)
            "Who sells acetone?",
            "Find suppliers for nitrile gloves",
            "Which vendors carry sulfuric acid?",
            # Category browsing (Sprint 17)
            "What categories of chemicals do we have?",
            "Show me all controlled material categories",
            "List subcategories under Safety Prevention",
            # Price inquiry (Sprint 17)
            "How much does acetone cost?",
            "What's the price for item ACET-001?",
            "Compare prices for gloves across suppliers",
            # Supplier detail (Sprint 17)
            "Tell me about Grainger",
            "Show details for TC Specialties",
            "What are Grainger's top products?",
            # Top suppliers (Sprint 17)
            "Who are the top 10 suppliers by spend?",
            "Ranking of suppliers by order volume",
            "Best suppliers in chemicals category",
        ]
