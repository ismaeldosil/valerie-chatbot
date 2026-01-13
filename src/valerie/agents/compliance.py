"""Compliance Validation agent - validates supplier certifications."""

from datetime import datetime

from ..models import ChatState, ComplianceInfo
from .base import BaseAgent


class ComplianceAgent(BaseAgent):
    """Validates supplier certifications and compliance status."""

    name = "compliance"

    def get_system_prompt(self) -> str:
        return """You are a Compliance Validation Agent for aerospace suppliers.

Your responsibilities:
1. Validate supplier certifications:
   - Nadcap (NDT, Heat Treat, Welding, Coatings, etc.)
   - AS9100 (Quality Management)
   - AS9120 (Distribution)
   - ITAR (Defense articles)
   - ISO certifications

2. Check certification status:
   - Active: Valid and current
   - Expiring: Within 90 days of expiration
   - Expired: Past expiration date
   - Pending: Under review

3. Verify scope matching:
   - Ensure certification scope covers required processes
   - Flag scope gaps

4. ITAR Handling:
   - Flag all ITAR-related queries for human review
   - Verify ITAR registration status
   - Check for debarment or suspension

Critical: Any ITAR decisions require human approval (HITL)."""

    async def process(self, state: ChatState) -> ChatState:
        """Validate compliance for suppliers in state."""
        start_time = datetime.now()

        required_certs = state.entities.get("certifications", [])
        compliance_results = []

        for supplier in state.suppliers:
            result = self._validate_supplier(supplier, required_certs)
            compliance_results.append(result)

            # Check for ITAR flag
            if "itar" in required_certs or any(c.type == "itar" for c in supplier.certifications):
                state.itar_flagged = True
                state.requires_human_approval = True

        state.compliance_results = compliance_results

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data={
                "validated_count": len(compliance_results),
                "itar_flagged": state.itar_flagged,
                "compliant_count": sum(1 for r in compliance_results if r.is_compliant),
            },
            start_time=start_time,
        )

        return state

    def _validate_supplier(self, supplier, required_certs: list[str]) -> ComplianceInfo:
        """Validate a single supplier's compliance."""
        # Mock validation - real implementation would check external sources
        supplier_cert_types = {c.type for c in supplier.certifications}
        required_set = set(required_certs)

        valid = list(supplier_cert_types.intersection(required_set))
        missing = list(required_set - supplier_cert_types)

        # Check for expiring (mock - would check actual dates)
        expiring = []
        for cert in supplier.certifications:
            if cert.status == "expiring":
                expiring.append(cert.type)

        is_compliant = len(missing) == 0 and len(expiring) == 0

        return ComplianceInfo(
            supplier_id=supplier.id,
            is_compliant=is_compliant,
            certifications_valid=valid,
            certifications_missing=missing,
            certifications_expiring=expiring,
            itar_cleared="itar" in supplier_cert_types,
        )
