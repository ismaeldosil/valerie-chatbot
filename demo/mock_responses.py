"""Mock responses for demo without API key."""

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Load sample data
DATA_PATH = Path(__file__).parent / "data" / "sample_suppliers.json"
with open(DATA_PATH) as f:
    SAMPLE_DATA = json.load(f)


@dataclass
class AgentExecution:
    """Represents an agent's execution for the demo."""
    agent_name: str
    display_name: str
    status: str = "pending"  # pending, running, completed, error, skipped
    duration_ms: int = 0
    output: dict = field(default_factory=dict)
    icon: str = ""


class DemoEngine:
    """Simulates multi-agent execution for demo purposes."""

    AGENTS = [
        ("guardrails", "Guardrails", "shield"),
        ("intent_classifier", "Intent Classifier", "brain"),
        ("memory", "Memory & Context", "database"),
        ("supplier_search", "Supplier Search", "search"),
        ("oracle_fusion", "Oracle Fusion", "cloud"),
        ("compliance", "Compliance Validation", "check-circle"),
        ("process_expertise", "Process Expert", "book"),
        ("comparison", "Comparison", "columns"),
        ("risk_assessment", "Risk Assessment", "alert-triangle"),
        ("response_generation", "Response Generation", "message-circle"),
        ("evaluation", "Evaluation", "star"),
        ("observability", "Observability", "activity"),
    ]

    def __init__(self):
        self.executions: list[AgentExecution] = []
        self.current_scenario = None

    def reset(self):
        """Reset execution state."""
        self.executions = []
        self.current_scenario = None

    def detect_scenario(self, user_input: str) -> str:
        """Detect which demo scenario matches the input."""
        input_lower = user_input.lower()

        # Check for injection attempts
        if any(kw in input_lower for kw in ["ignore", "system:", "reveal", "<script"]):
            return "injection_blocked"

        # Check for ITAR keywords
        if any(kw in input_lower for kw in ["itar", "defense", "classified", "munitions"]):
            return "itar_hitl"

        # Check for comparison
        if any(kw in input_lower for kw in ["compare", "comparison", "versus", "vs"]):
            return "comparison"

        # Check for risk
        if any(kw in input_lower for kw in ["risk", "assess", "evaluate"]):
            return "risk_assessment"

        # Check for compliance
        if any(kw in input_lower for kw in ["compliance", "certified", "nadcap", "certification"]):
            return "compliance_check"

        # Default to search
        if any(kw in input_lower for kw in ["find", "search", "supplier", "heat", "anodiz", "plat", "coat"]):
            return "supplier_search"

        # Greeting
        if any(kw in input_lower for kw in ["hello", "hi", "hey", "help"]):
            return "greeting"

        return "general_query"

    def process_message(self, user_input: str) -> tuple[str, list[AgentExecution]]:
        """Process a message and return response + agent executions."""
        self.reset()
        scenario = self.detect_scenario(user_input)
        self.current_scenario = scenario

        # Execute scenario
        if scenario == "injection_blocked":
            return self._handle_injection()
        elif scenario == "itar_hitl":
            return self._handle_itar()
        elif scenario == "supplier_search":
            return self._handle_search(user_input)
        elif scenario == "comparison":
            return self._handle_comparison()
        elif scenario == "risk_assessment":
            return self._handle_risk()
        elif scenario == "compliance_check":
            return self._handle_compliance()
        elif scenario == "greeting":
            return self._handle_greeting()
        else:
            return self._handle_general(user_input)

    def _add_execution(self, agent_name: str, display_name: str, icon: str,
                       duration_ms: int, status: str = "completed",
                       output: dict = None) -> AgentExecution:
        """Add an agent execution to the list."""
        exec_item = AgentExecution(
            agent_name=agent_name,
            display_name=display_name,
            icon=icon,
            status=status,
            duration_ms=duration_ms,
            output=output or {}
        )
        self.executions.append(exec_item)
        return exec_item

    def _handle_injection(self) -> tuple[str, list[AgentExecution]]:
        """Handle injection attempt - blocked by guardrails."""
        self._add_execution(
            "guardrails", "Guardrails", "shield", 45,
            status="error",
            output={
                "passed": False,
                "reason": "Potential prompt injection detected",
                "action": "Request blocked"
            }
        )

        response = """I'm unable to process that request.

Your message was flagged by our security system as a potential prompt injection attempt. This is a safety measure to protect the integrity of our system.

If you believe this is an error, please rephrase your question focusing on supplier-related queries such as:
- Finding suppliers for specific processes
- Checking supplier certifications
- Comparing suppliers"""

        return response, self.executions

    def _handle_itar(self) -> tuple[str, list[AgentExecution]]:
        """Handle ITAR-related query - triggers HITL."""
        self._add_execution(
            "guardrails", "Guardrails", "shield", 52,
            output={"passed": True, "itar_flagged": True, "warnings": ["ITAR keywords detected"]}
        )
        self._add_execution(
            "intent_classifier", "Intent Classifier", "brain", 120,
            output={"intent": "supplier_search", "confidence": 0.89, "entities": {"itar": True}}
        )
        self._add_execution(
            "hitl", "Human-in-the-Loop", "user-check", 0,
            status="pending",
            output={
                "reason": "ITAR-related query requires human approval",
                "approval_required": True,
                "escalation_level": "compliance_officer"
            }
        )

        response = """This query involves ITAR-controlled information and requires human approval.

**Request Pending Approval**

Your query has been flagged as ITAR-sensitive due to keywords related to defense articles and export-controlled materials.

A Compliance Officer has been notified and will review this request. You will receive a response once the review is complete.

**Estimated Review Time:** 2-4 business hours

In the meantime, I can help with non-ITAR supplier queries."""

        return response, self.executions

    def _handle_search(self, user_input: str) -> tuple[str, list[AgentExecution]]:
        """Handle supplier search."""
        # Guardrails
        self._add_execution(
            "guardrails", "Guardrails", "shield", 38,
            output={"passed": True, "pii_detected": False, "itar_flagged": False}
        )

        # Intent classification
        detected_process = "heat_treatment"
        if "anodiz" in user_input.lower():
            detected_process = "anodizing"
        elif "plat" in user_input.lower():
            detected_process = "plating"
        elif "coat" in user_input.lower():
            detected_process = "chemical_conversion"

        self._add_execution(
            "intent_classifier", "Intent Classifier", "brain", 156,
            output={
                "intent": "supplier_search",
                "confidence": 0.94,
                "entities": {"process": detected_process}
            }
        )

        # Memory
        self._add_execution(
            "memory", "Memory & Context", "database", 23,
            output={"session_context": "new_session", "references_resolved": 0}
        )

        # Supplier search
        matching_suppliers = [
            s for s in SAMPLE_DATA["suppliers"]
            if detected_process in s["processes"]
        ][:3]

        self._add_execution(
            "supplier_search", "Supplier Search", "search", 245,
            output={
                "query": detected_process,
                "results_count": len(matching_suppliers),
                "suppliers": [s["name"] for s in matching_suppliers]
            }
        )

        # Oracle Fusion
        self._add_execution(
            "oracle_fusion", "Oracle Fusion", "cloud", 312,
            output={
                "data_source": "Oracle Fusion Cloud",
                "records_fetched": len(matching_suppliers),
                "cache_hit": False
            }
        )

        # Compliance
        self._add_execution(
            "compliance", "Compliance Validation", "check-circle", 189,
            output={
                "suppliers_validated": len(matching_suppliers),
                "all_compliant": True,
                "certifications_verified": ["Nadcap", "AS9100D"]
            }
        )

        # Process expertise
        process_info = SAMPLE_DATA["processes"].get(detected_process, {})
        self._add_execution(
            "process_expertise", "Process Expert", "book", 78,
            output={
                "process": detected_process,
                "specs_referenced": process_info.get("specs", [])[:2]
            }
        )

        # Response generation
        self._add_execution(
            "response_generation", "Response Generation", "message-circle", 234,
            output={"format": "structured_list", "includes_recommendations": True}
        )

        # Evaluation
        self._add_execution(
            "evaluation", "Evaluation", "star", 45,
            output={"quality_score": 0.92, "relevance_score": 0.95}
        )

        # Observability
        self._add_execution(
            "observability", "Observability", "activity", 12,
            output={"trace_logged": True, "metrics_recorded": True}
        )

        # Build response
        process_name = process_info.get("name", detected_process.replace("_", " ").title())
        response = f"""## Suppliers Found for {process_name}

Based on your search criteria, I found **{len(matching_suppliers)} qualified suppliers**:

"""
        for i, supplier in enumerate(matching_suppliers, 1):
            certs = ", ".join([c["name"] for c in supplier["certifications"][:2]])
            oems = ", ".join(supplier["oem_approvals"][:3])
            response += f"""### {i}. {supplier["name"]}
- **Location:** {supplier["location"]}
- **Quality Score:** {supplier["quality_score"]*100:.0f}%
- **Lead Time:** {supplier["lead_time_days"]} days
- **Certifications:** {certs}
- **OEM Approvals:** {oems}
- **Capacity:** {"Available" if supplier["capacity_available"] else "Limited"}

"""

        response += """---
**Would you like me to:**
- Compare these suppliers in detail?
- Check compliance for a specific supplier?
- Assess risk factors for any of these suppliers?"""

        return response, self.executions

    def _handle_comparison(self) -> tuple[str, list[AgentExecution]]:
        """Handle supplier comparison."""
        # Standard flow agents
        self._add_execution("guardrails", "Guardrails", "shield", 35, output={"passed": True})
        self._add_execution("intent_classifier", "Intent Classifier", "brain", 142,
                           output={"intent": "supplier_comparison", "confidence": 0.96})
        self._add_execution("memory", "Memory & Context", "database", 28,
                           output={"context_loaded": True, "previous_suppliers": 3})
        self._add_execution("supplier_search", "Supplier Search", "search", 198,
                           output={"loaded_from_context": True, "suppliers": 3})
        self._add_execution("oracle_fusion", "Oracle Fusion", "cloud", 287,
                           output={"pricing_data": True, "delivery_history": True})
        self._add_execution("compliance", "Compliance Validation", "check-circle", 156,
                           output={"all_compliant": True})

        # Comparison agent
        self._add_execution(
            "comparison", "Comparison", "columns", 345,
            output={
                "dimensions": ["quality", "price", "delivery", "capacity", "certifications"],
                "recommendation": "AeroTech Surface Solutions",
                "confidence": 0.88
            }
        )

        self._add_execution("response_generation", "Response Generation", "message-circle", 267,
                           output={"format": "comparison_table"})
        self._add_execution("evaluation", "Evaluation", "star", 38,
                           output={"quality_score": 0.94})

        suppliers = SAMPLE_DATA["suppliers"][:3]

        response = """## Supplier Comparison Analysis

| Criteria | AeroTech Solutions | PrecisionCoat | MetalTreat Aerospace |
|----------|-------------------|---------------|---------------------|
| **Quality Score** | 95% | 91% | 97% |
| **Delivery Score** | 92% | 88% | 94% |
| **Lead Time** | 5 days | 7 days | 10 days |
| **Capacity** | Available | Available | Limited |
| **Min Order** | $500 | $750 | $1,000 |

### Recommendation

Based on the analysis, **AeroTech Surface Solutions** offers the best overall value:

- **Strengths:** Excellent balance of quality (95%) and fast lead time (5 days)
- **Certifications:** Nadcap Heat Treating, AS9100D, ISO 9001:2015
- **OEM Approvals:** Boeing, Lockheed Martin, Northrop Grumman

**MetalTreat Aerospace** has the highest quality score (97%) but has limited capacity and longer lead times.

**PrecisionCoat Industries** is a good alternative for chemical processing needs with ITAR registration.

---
Would you like me to assess the risk profile for any of these suppliers?"""

        return response, self.executions

    def _handle_risk(self) -> tuple[str, list[AgentExecution]]:
        """Handle risk assessment."""
        self._add_execution("guardrails", "Guardrails", "shield", 32, output={"passed": True})
        self._add_execution("intent_classifier", "Intent Classifier", "brain", 128,
                           output={"intent": "risk_assessment", "confidence": 0.93})
        self._add_execution("memory", "Memory & Context", "database", 25,
                           output={"supplier_context": "AeroTech Surface Solutions"})
        self._add_execution("oracle_fusion", "Oracle Fusion", "cloud", 356,
                           output={"financial_data": True, "delivery_history": True, "quality_metrics": True})
        self._add_execution("compliance", "Compliance Validation", "check-circle", 167,
                           output={"certifications_valid": True, "no_debarments": True})

        # Risk assessment
        self._add_execution(
            "risk_assessment", "Risk Assessment", "alert-triangle", 423,
            output={
                "overall_risk": "LOW",
                "score": 0.18,
                "categories": {
                    "financial": 0.15,
                    "operational": 0.22,
                    "compliance": 0.08,
                    "geopolitical": 0.12,
                    "quality": 0.10
                }
            }
        )

        self._add_execution("response_generation", "Response Generation", "message-circle", 234,
                           output={"format": "risk_report"})
        self._add_execution("evaluation", "Evaluation", "star", 42,
                           output={"quality_score": 0.91})

        response = """## Risk Assessment Report

### Supplier: AeroTech Surface Solutions

**Overall Risk Level:** LOW (Score: 0.18)

| Risk Category | Score | Level | Notes |
|--------------|-------|-------|-------|
| Financial | 0.15 | Low | Stable revenue, good credit rating |
| Operational | 0.22 | Low | Adequate capacity, experienced team |
| Compliance | 0.08 | Very Low | All certifications current, no findings |
| Geopolitical | 0.12 | Low | US-based, minimal supply chain exposure |
| Quality | 0.10 | Very Low | 99.2% first-pass yield, zero escapes |

### Key Findings

**Strengths:**
- All Nadcap certifications current with >12 months validity
- No quality escapes in past 24 months
- Strong financial position with Dun & Bradstreet rating of 1A1

**Watch Items:**
- Single site operation (Phoenix, AZ)
- Key person dependency on Quality Director

### Recommendations

1. **Approved for use** - Low risk supplier suitable for critical applications
2. Consider dual-sourcing strategy for risk mitigation
3. Schedule annual on-site audit per AS9100 requirements

---
Would you like me to compare risk profiles across multiple suppliers?"""

        return response, self.executions

    def _handle_compliance(self) -> tuple[str, list[AgentExecution]]:
        """Handle compliance check."""
        self._add_execution("guardrails", "Guardrails", "shield", 34, output={"passed": True})
        self._add_execution("intent_classifier", "Intent Classifier", "brain", 135,
                           output={"intent": "compliance_check", "confidence": 0.91})
        self._add_execution("oracle_fusion", "Oracle Fusion", "cloud", 298,
                           output={"supplier_record": True, "certifications": True})

        self._add_execution(
            "compliance", "Compliance Validation", "check-circle", 456,
            output={
                "supplier": "AeroTech Surface Solutions",
                "status": "COMPLIANT",
                "certifications_checked": 3,
                "all_valid": True,
                "next_expiry": "2025-08-20"
            }
        )

        self._add_execution("response_generation", "Response Generation", "message-circle", 189,
                           output={"format": "compliance_report"})

        response = """## Compliance Verification Report

### Supplier: AeroTech Surface Solutions

**Status:** COMPLIANT

### Certification Status

| Certification | Status | Expiry Date | Days Remaining |
|--------------|--------|-------------|----------------|
| Nadcap Heat Treating | Active | 2026-03-15 | 450 |
| AS9100D Rev D | Active | 2025-08-20 | 243 |
| ISO 9001:2015 | Active | 2026-01-10 | 386 |

### OEM Approvals

| OEM | Approval Type | Status |
|-----|--------------|--------|
| Boeing | D1-4426 | Active |
| Lockheed Martin | Approved Processor List | Active |
| Northrop Grumman | QPL | Active |

### Audit History

- **Last Nadcap Audit:** 2024-09-15 - No findings
- **Last Customer Audit:** 2024-11-20 (Boeing) - 2 minor findings, closed
- **Internal Audits:** Quarterly, all compliant

### Alerts

No compliance alerts. Next certification renewal: AS9100D on 2025-08-20.

---
Would you like me to set up renewal reminders or search for alternative suppliers?"""

        return response, self.executions

    def _handle_greeting(self) -> tuple[str, list[AgentExecution]]:
        """Handle greeting."""
        self._add_execution("guardrails", "Guardrails", "shield", 28, output={"passed": True})
        self._add_execution("intent_classifier", "Intent Classifier", "brain", 89,
                           output={"intent": "greeting", "confidence": 0.98})
        self._add_execution("response_generation", "Response Generation", "message-circle", 156,
                           output={"format": "greeting"})

        response = """## Welcome to Valerie Supplier Chatbot

I'm your AI assistant for aerospace surface treatment supplier management. I can help you with:

**Supplier Discovery**
- Find qualified suppliers for specific processes
- Search by certification, location, or capability

**Compliance & Risk**
- Verify supplier certifications (Nadcap, AS9100, etc.)
- Assess supplier risk profiles
- Check OEM approval status

**Analysis & Comparison**
- Compare multiple suppliers side-by-side
- Analyze quality, delivery, and pricing metrics

**Example queries:**
- "Find heat treatment suppliers with Nadcap certification"
- "Compare my top 3 anodizing suppliers"
- "What's the risk profile for AeroTech Solutions?"

How can I help you today?"""

        return response, self.executions

    def _handle_general(self, user_input: str) -> tuple[str, list[AgentExecution]]:
        """Handle general/unknown queries."""
        self._add_execution("guardrails", "Guardrails", "shield", 31, output={"passed": True})
        self._add_execution("intent_classifier", "Intent Classifier", "brain", 167,
                           output={"intent": "unknown", "confidence": 0.45})
        self._add_execution("response_generation", "Response Generation", "message-circle", 178,
                           output={"format": "clarification"})

        response = f"""I'm not sure I understood your request: "{user_input[:50]}..."

I specialize in aerospace supplier management. Here's what I can help with:

- **Search:** "Find suppliers for [process]"
- **Compare:** "Compare suppliers for heat treatment"
- **Compliance:** "Check certifications for [supplier]"
- **Risk:** "Assess risk for [supplier]"

Could you rephrase your question using one of these formats?"""

        return response, self.executions
