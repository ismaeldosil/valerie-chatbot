"""Supplier Comparison agent - compares multiple suppliers."""

from datetime import datetime

from ..models import ChatState
from .base import BaseAgent


class ComparisonAgent(BaseAgent):
    """Compares multiple suppliers across various dimensions."""

    name = "comparison"

    def get_system_prompt(self) -> str:
        return """You are a Supplier Comparison Agent for aerospace suppliers.

Your role is to compare suppliers across these dimensions:
1. Certifications & Compliance (25%)
2. Quality Metrics (20%)
3. On-Time Delivery (15%)
4. Technical Capabilities (20%)
5. Risk Score (15%)
6. Cost Competitiveness (5%)

Provide:
- Side-by-side comparison data
- Strengths and weaknesses for each
- Clear recommendation with rationale
- Trade-off analysis for difficult choices

Format data for visualization (radar charts, tables)."""

    async def process(self, state: ChatState) -> ChatState:
        """Compare suppliers in state."""
        start_time = datetime.now()

        if len(state.suppliers) < 2:
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error="Need at least 2 suppliers to compare",
                start_time=start_time,
            )
            return state

        comparison_data = self._build_comparison(state)
        state.comparison_data = comparison_data

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data=comparison_data,
            start_time=start_time,
        )

        return state

    def _build_comparison(self, state: ChatState) -> dict:
        """Build comparison data structure."""
        suppliers_data = []

        for supplier in state.suppliers:
            # Find compliance info for this supplier
            compliance = next(
                (c for c in state.compliance_results if c.supplier_id == supplier.id),
                None,
            )

            supplier_scores = {
                "id": supplier.id,
                "name": supplier.name,
                "scores": {
                    "quality": supplier.quality_rate or 0,
                    "delivery": supplier.on_time_delivery or 0,
                    "risk": (1 - (supplier.risk_score or 0)) * 100,  # Invert for display
                    "compliance": 100 if (compliance and compliance.is_compliant) else 50,
                    "capabilities": len(supplier.capabilities) * 20,  # Simple score
                },
                "strengths": [],
                "weaknesses": [],
            }

            # Identify strengths and weaknesses
            if (supplier.quality_rate or 0) >= 98:
                supplier_scores["strengths"].append("Excellent quality rate")
            elif (supplier.quality_rate or 0) < 95:
                supplier_scores["weaknesses"].append("Quality below target")

            if (supplier.on_time_delivery or 0) >= 96:
                supplier_scores["strengths"].append("Strong delivery performance")
            elif (supplier.on_time_delivery or 0) < 90:
                supplier_scores["weaknesses"].append("Delivery concerns")

            if (supplier.risk_score or 0) <= 0.15:
                supplier_scores["strengths"].append("Low risk profile")
            elif (supplier.risk_score or 0) > 0.5:
                supplier_scores["weaknesses"].append("Elevated risk level")

            suppliers_data.append(supplier_scores)

        # Generate recommendation
        recommendation = self._generate_recommendation(suppliers_data)

        return {
            "suppliers": suppliers_data,
            "recommendation": recommendation,
            "dimensions": ["quality", "delivery", "risk", "compliance", "capabilities"],
        }

    def _generate_recommendation(self, suppliers_data: list) -> dict:
        """Generate a recommendation based on comparison."""
        if not suppliers_data:
            return {"supplier_id": None, "rationale": "No suppliers to compare"}

        # Simple scoring - average of all dimensions
        scored = []
        for s in suppliers_data:
            avg_score = sum(s["scores"].values()) / len(s["scores"])
            scored.append((s["id"], s["name"], avg_score))

        scored.sort(key=lambda x: x[2], reverse=True)
        winner = scored[0]

        return {
            "supplier_id": winner[0],
            "supplier_name": winner[1],
            "score": round(winner[2], 1),
            "rationale": (f"{winner[1]} scored highest overall with balanced performance."),
        }
