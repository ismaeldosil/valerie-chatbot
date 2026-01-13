"""Human-in-the-Loop agent - handles human approval workflows."""

from datetime import datetime
from typing import Any

from langgraph.types import interrupt

from ..agents.base import BaseAgent
from ..models import ChatState, HITLRequest


class HITLAgent(BaseAgent):
    """Manages human-in-the-loop approval workflows using LangGraph interrupt()."""

    name = "hitl"

    # Triggers that require human approval
    APPROVAL_TRIGGERS = {
        "itar_decision": "ITAR-related decisions require human approval",
        "high_risk_supplier": "High-risk supplier engagement needs review",
        "low_confidence": "Low confidence classification needs validation",
        "debarment_check": "Potential debarment requires verification",
        "large_contract": "Large contract value exceeds auto-approval limit",
    }

    def get_system_prompt(self) -> str:
        return """You are a Human-in-the-Loop Agent managing approval workflows.

Triggers for human approval:
1. ITAR decisions - Always require human sign-off
2. High-risk suppliers (score > 0.7)
3. Low confidence classifications (< 0.6)
4. Debarment or suspension concerns
5. Contract values above threshold

Use LangGraph interrupt() pattern to pause and await human decision.
Resume with human_decision in state after approval."""

    async def process(self, state: ChatState) -> ChatState:
        """Check if human approval is needed and handle interrupt."""
        start_time = datetime.now()

        # If we already have a decision, process it
        if state.hitl_decision:
            return self._process_decision(state, start_time)

        # Check if we need to trigger HITL
        if not state.requires_human_approval:
            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={"approval_needed": False},
                start_time=start_time,
            )
            return state

        # Determine the trigger reason
        trigger, reason = self._determine_trigger(state)

        # Create HITL request
        request = HITLRequest(
            request_type=trigger,
            priority=self._calculate_priority(state),
            context=self._build_context(state),
            decision_options=self._get_decision_options(trigger),
            timeout_ms=self.settings.hitl_timeout_ms,
        )

        state.hitl_request = request

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data={
                "approval_needed": True,
                "trigger": trigger,
                "reason": reason,
            },
            start_time=start_time,
        )

        # Use LangGraph interrupt() to pause execution
        # This will pause the graph and wait for human input
        decision = interrupt(
            {
                "type": trigger,
                "reason": reason,
                "context": request.context,
                "options": request.decision_options,
            }
        )

        # When resumed, decision will be populated
        state.hitl_decision = decision
        return self._process_decision(state, start_time)

    def _determine_trigger(self, state: ChatState) -> tuple[str, str]:
        """Determine why human approval is needed."""
        if state.itar_flagged:
            return "itar_decision", self.APPROVAL_TRIGGERS["itar_decision"]

        if state.risk_results:
            high_risk = any(r.overall_score > 0.7 for r in state.risk_results)
            if high_risk:
                return "high_risk_supplier", self.APPROVAL_TRIGGERS["high_risk_supplier"]

        if state.confidence < self.settings.low_confidence_threshold:
            return "low_confidence", self.APPROVAL_TRIGGERS["low_confidence"]

        return "manual_review", "Manual review requested"

    def _calculate_priority(self, state: ChatState) -> str:
        """Calculate priority level for the request."""
        if state.itar_flagged:
            return "critical"
        if state.risk_results and any(r.overall_score > 0.8 for r in state.risk_results):
            return "urgent"
        if state.risk_results and any(r.overall_score > 0.6 for r in state.risk_results):
            return "high"
        return "normal"

    def _build_context(self, state: ChatState) -> dict[str, Any]:
        """Build context for human reviewer."""
        return {
            "intent": state.intent.value,
            "confidence": state.confidence,
            "suppliers": [s.name for s in state.suppliers[:5]],
            "itar_flagged": state.itar_flagged,
            "risk_scores": {r.supplier_id: r.overall_score for r in state.risk_results}
            if state.risk_results
            else {},
            "entities": state.entities,
        }

    def _get_decision_options(self, trigger: str) -> list[dict[str, Any]]:
        """Get decision options based on trigger type."""
        base_options = [
            {"id": "approve", "label": "Approve", "action": "continue"},
            {"id": "reject", "label": "Reject", "action": "stop"},
            {"id": "modify", "label": "Modify & Continue", "action": "modify"},
        ]

        if trigger == "itar_decision":
            base_options.insert(
                1,
                {
                    "id": "escalate",
                    "label": "Escalate to Compliance",
                    "action": "escalate",
                },
            )

        return base_options

    def _process_decision(self, state: ChatState, start_time: datetime) -> ChatState:
        """Process the human decision."""
        decision = state.hitl_decision or {}
        action = decision.get("action", "reject")

        if action == "approve":
            state.requires_human_approval = False
        elif action == "reject":
            state.error = "Request rejected by human reviewer"
        elif action == "modify":
            # Apply modifications from decision
            modifications = decision.get("modifications", {})
            state.entities.update(modifications.get("entities", {}))
            state.requires_human_approval = False

        state.agent_outputs[self.name] = self.create_output(
            success=action != "reject",
            data={"decision": action, "processed": True},
            start_time=start_time,
        )

        return state
