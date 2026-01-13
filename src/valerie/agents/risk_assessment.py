"""Risk Assessment agent - evaluates supplier risks."""

from datetime import datetime

from ..models import ChatState, RiskScore
from .base import BaseAgent


class RiskAssessmentAgent(BaseAgent):
    """Assesses supplier risks across multiple dimensions."""

    name = "risk_assessment"

    def get_system_prompt(self) -> str:
        return """You are a Risk Assessment Agent for supplier evaluation.

Evaluate risks across these categories:
1. **Compliance Risk** (25%): Certification gaps, audit findings
2. **Financial Risk** (20%): Financial stability, credit rating
3. **Capacity Risk** (15%): Production capacity, lead times
4. **Geographic Risk** (15%): Location, natural disasters, political
5. **Quality Risk** (15%): Quality rates, customer complaints
6. **Dependency Risk** (10%): Single source, tier-2 dependencies

Risk Score Scale:
- 0.0-0.2: Low risk (Green)
- 0.2-0.4: Moderate risk (Yellow)
- 0.4-0.6: Elevated risk (Orange)
- 0.6-0.8: High risk (Red)
- 0.8-1.0: Critical risk (Black)

For each risk, provide:
- Score (0-1)
- Key factors
- Mitigation recommendations
- Alerts for critical issues"""

    async def process(self, state: ChatState) -> ChatState:
        """Assess risks for suppliers in state."""
        start_time = datetime.now()

        risk_results = []

        for supplier in state.suppliers:
            risk = self._assess_supplier_risk(supplier, state)
            risk_results.append(risk)

        state.risk_results = risk_results

        # Check for high-risk suppliers requiring human review
        high_risk_count = sum(1 for r in risk_results if r.overall_score > 0.6)
        if high_risk_count > 0:
            state.requires_human_approval = True

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data={
                "assessed_count": len(risk_results),
                "high_risk_count": high_risk_count,
                "average_risk": (
                    sum(r.overall_score for r in risk_results) / len(risk_results)
                    if risk_results
                    else 0
                ),
            },
            start_time=start_time,
        )

        return state

    def _assess_supplier_risk(self, supplier, state: ChatState) -> RiskScore:
        """Assess risk for a single supplier."""
        categories = {}
        mitigations = []
        alerts = []

        # Compliance Risk
        compliance = next(
            (c for c in state.compliance_results if c.supplier_id == supplier.id),
            None,
        )
        if compliance:
            if not compliance.is_compliant:
                categories["compliance"] = 0.7
                mitigations.append("Address missing certifications before engagement")
                alerts.append(f"Missing certs: {compliance.certifications_missing}")
            elif compliance.certifications_expiring:
                categories["compliance"] = 0.4
                mitigations.append("Monitor certification renewal dates")
            else:
                categories["compliance"] = 0.1
        else:
            categories["compliance"] = 0.5

        # Quality Risk
        quality_rate = supplier.quality_rate or 95
        if quality_rate >= 99:
            categories["quality"] = 0.1
        elif quality_rate >= 97:
            categories["quality"] = 0.2
        elif quality_rate >= 95:
            categories["quality"] = 0.35
        else:
            categories["quality"] = 0.6
            alerts.append(f"Quality rate below target: {quality_rate}%")

        # Capacity Risk (mock - would use real data)
        categories["capacity"] = 0.25

        # Geographic Risk (mock)
        categories["geographic"] = 0.2

        # Financial Risk (mock)
        categories["financial"] = 0.3

        # Dependency Risk (mock)
        categories["dependency"] = 0.2

        # Calculate weighted overall score
        weights = {
            "compliance": 0.25,
            "financial": 0.20,
            "capacity": 0.15,
            "geographic": 0.15,
            "quality": 0.15,
            "dependency": 0.10,
        }

        overall = sum(categories[k] * weights[k] for k in weights if k in categories)

        return RiskScore(
            supplier_id=supplier.id,
            overall_score=round(overall, 3),
            categories=categories,
            mitigations=mitigations,
            alerts=alerts,
        )
