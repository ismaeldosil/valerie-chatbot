"""Orchestrator agent - routes requests to appropriate agents."""

from datetime import datetime

from ..models import ChatState, Intent
from .base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """Orchestrates the flow between all agents using supervisor pattern."""

    name = "orchestrator"

    def get_system_prompt(self) -> str:
        return """You are the Orchestrator Agent for an aerospace supplier recommendation system.

Your role is to:
1. Analyze the classified intent and entities
2. Determine which agents need to be invoked
3. Coordinate the flow of information between agents
4. Ensure all relevant data is gathered before generating a response

You work with these agents:
- Intent Classifier: Classifies user intent and extracts entities
- Supplier Search: Searches for suppliers based on criteria
- Compliance Validation: Validates certifications (Nadcap, AS9100, ITAR)
- Supplier Comparison: Compares multiple suppliers
- Oracle Integration: Fetches data from Oracle Fusion Cloud
- Process Expertise: Provides technical process knowledge
- Risk Assessment: Evaluates supplier risks
- Response Generation: Formats the final response
- Memory Context: Manages conversation context

Product and Supplier Catalog agents:
- Product Search: Searches products and handles price inquiries
- Category Browse: Browses and navigates product categories
- Supplier Detail: Retrieves supplier information, rankings, and item comparisons

Infrastructure agents:
- Guardrails: Validates input safety
- HITL: Handles human-in-the-loop decisions
- Fallback: Manages error recovery
- Evaluation: Assesses response quality

Always prioritize safety and compliance. Flag ITAR-related queries for human review."""

    async def process(self, state: ChatState) -> ChatState:
        """Determine the routing based on intent."""
        start_time = datetime.now()

        # The orchestrator determines which path to take based on intent
        routing_map = {
            # Core supplier operations
            Intent.SUPPLIER_SEARCH: ["search", "compliance", "response"],
            Intent.SUPPLIER_COMPARISON: ["search", "compliance", "comparison", "response"],
            Intent.COMPLIANCE_CHECK: ["compliance", "response"],
            Intent.TECHNICAL_QUESTION: ["process_expertise", "response"],
            Intent.RISK_ASSESSMENT: ["search", "risk", "response"],
            # Product and category intents
            Intent.PRODUCT_SEARCH: ["product_search", "response"],
            Intent.CATEGORY_BROWSE: ["category_browse", "response"],
            Intent.PRICE_INQUIRY: ["product_search", "response"],
            Intent.SUPPLIER_DETAIL: ["supplier_detail", "response"],
            Intent.TOP_SUPPLIERS: ["supplier_detail", "response"],
            Intent.ITEM_COMPARISON: ["supplier_detail", "comparison", "response"],
            # Common intents
            Intent.CLARIFICATION: ["memory", "response"],
            Intent.GREETING: ["response"],
            Intent.UNKNOWN: ["clarify", "response"],
        }

        route = routing_map.get(state.intent, ["clarify", "response"])

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data={"route": route, "intent": state.intent.value},
            start_time=start_time,
        )

        return state

    def get_next_agent(self, state: ChatState) -> str | None:
        """Determine the next agent to invoke based on current state."""
        output = state.agent_outputs.get(self.name)
        if not output or not output.success:
            return "error_handler"

        route = output.data.get("route", [])
        completed = set(state.agent_outputs.keys())

        for agent in route:
            if agent not in completed:
                return agent

        return "response"
