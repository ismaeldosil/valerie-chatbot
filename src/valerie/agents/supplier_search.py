"""Supplier Search agent - searches for suppliers based on criteria."""

import logging
from datetime import datetime

from ..data.factory import get_default_data_source
from ..data.interfaces import ISupplierDataSource, SupplierDetail, SupplierResult
from ..models import ChatState, Supplier
from .base import BaseAgent

logger = logging.getLogger(__name__)


class SupplierSearchAgent(BaseAgent):
    """Searches for suppliers based on extracted criteria."""

    name = "supplier_search"

    def __init__(self, *args, data_source: ISupplierDataSource | None = None, **kwargs):
        """Initialize the agent with optional data source injection.

        Args:
            data_source: Optional data source for dependency injection (testing).
                        If not provided, uses the default data source.
        """
        super().__init__(*args, **kwargs)
        self._data_source = data_source

    @property
    def data_source(self) -> ISupplierDataSource:
        """Get the data source instance (lazy initialization)."""
        if self._data_source is None:
            self._data_source = get_default_data_source()
        return self._data_source

    def get_system_prompt(self) -> str:
        return """You are a Supplier Search Agent for an aerospace supplier recommendation system.

Your role is to:
1. Search for suppliers matching the given criteria
2. Rank results by relevance using these factors:
   - Certification match (40%)
   - Capability match (30%)
   - Quality metrics (15%)
   - On-time delivery (10%)
   - Geographic preference (5%)

3. Handle cases with no exact matches by:
   - Suggesting related capabilities
   - Relaxing non-critical criteria
   - Offering partial matches with explanations

Always verify ITAR clearance for defense-related queries."""

    async def process(self, state: ChatState) -> ChatState:
        """Search for suppliers based on criteria in state."""
        start_time = datetime.now()

        # Extract search criteria from entities
        criteria = {
            "processes": state.entities.get("processes", []),
            "certifications": state.entities.get("certifications", []),
            "materials": state.entities.get("materials", []),
            "oem_approvals": state.entities.get("oem_approvals", []),
            "location": state.entities.get("location"),
        }

        state.search_criteria = criteria

        try:
            # Search suppliers using the data source
            suppliers = await self._search_suppliers(criteria)
            state.suppliers = suppliers

            # Build output data
            output_data = {
                "criteria": criteria,
                "results_count": len(suppliers),
                "supplier_ids": [s.id for s in suppliers],
            }

            # Add helpful message if no results found
            if not suppliers:
                output_data["message"] = "No suppliers found matching the specified criteria."
                logger.info(f"No suppliers found for criteria: {criteria}")

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data=output_data,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Error searching suppliers: {e}", exc_info=True)
            state.suppliers = []
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=f"Failed to search suppliers: {str(e)}",
                data={"criteria": criteria},
                start_time=start_time,
            )

        return state

    async def _search_suppliers(self, criteria: dict) -> list[Supplier]:
        """Search for suppliers using the data source.

        Args:
            criteria: Search criteria including processes, certifications, etc.

        Returns:
            List of Supplier models matching the criteria.
        """
        # Determine search parameters from criteria
        name_query = criteria.get("location")  # Location can be part of name search
        category = None
        product = None

        # If materials are specified, use them as product search
        materials = criteria.get("materials", [])
        if materials:
            product = materials[0]  # Search by first material

        # If processes are specified, use them as category search
        processes = criteria.get("processes", [])
        if processes:
            category = processes[0]  # Search by first process

        # Search using the data source
        supplier_results = await self.data_source.search_suppliers(
            name=name_query,
            category=category,
            product=product,
            limit=20,  # Get more results for filtering
        )

        # Convert SupplierResult to Supplier model
        suppliers = []
        for result in supplier_results:
            # Get detailed info for each supplier if available
            detail = await self.data_source.get_supplier_detail(result.id)

            if detail:
                supplier = self._convert_detail_to_supplier(detail)
            else:
                supplier = self._convert_result_to_supplier(result)

            suppliers.append(supplier)

        # Apply additional filtering based on criteria
        suppliers = self._filter_suppliers(suppliers, criteria)

        return suppliers

    def _convert_result_to_supplier(self, result: SupplierResult) -> Supplier:
        """Convert a SupplierResult DTO to a Supplier model.

        Args:
            result: SupplierResult from data source

        Returns:
            Supplier model instance
        """
        return Supplier(
            id=result.id,
            name=result.name,
            location=result.site,
            capabilities=[],  # Basic result doesn't have capabilities
            quality_rate=None,
            on_time_delivery=None,
            risk_score=None,
        )

    def _convert_detail_to_supplier(self, detail: SupplierDetail) -> Supplier:
        """Convert a SupplierDetail DTO to a Supplier model.

        Args:
            detail: SupplierDetail from data source

        Returns:
            Supplier model instance with full details
        """
        # Extract category names as capabilities
        capabilities = [cat.name for cat in detail.top_categories]

        return Supplier(
            id=detail.id,
            name=detail.name,
            location=detail.site,
            capabilities=capabilities,
            quality_rate=None,  # Not available in current data model
            on_time_delivery=None,  # Not available in current data model
            risk_score=None,  # Not available in current data model
        )

    def _filter_suppliers(
        self, suppliers: list[Supplier], criteria: dict
    ) -> list[Supplier]:
        """Apply additional filtering based on criteria.

        Args:
            suppliers: List of suppliers to filter
            criteria: Search criteria

        Returns:
            Filtered list of suppliers
        """
        filtered = suppliers

        # Filter by processes/capabilities
        required_processes = set(criteria.get("processes", []))
        if required_processes:
            filtered = [
                s for s in filtered
                if required_processes.intersection(set(s.capabilities))
            ]

        # Filter by location if specified
        location = criteria.get("location")
        if location and filtered:
            location_lower = location.lower()
            location_filtered = [
                s for s in filtered
                if s.location and location_lower in s.location.lower()
            ]
            # Only apply location filter if it returns results
            if location_filtered:
                filtered = location_filtered

        return filtered
