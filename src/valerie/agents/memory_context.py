"""Memory Context agent - manages conversation context and memory."""

from datetime import datetime

from ..models import ChatState
from .base import BaseAgent


class MemoryContextAgent(BaseAgent):
    """Manages conversation context, references, and memory."""

    name = "memory_context"

    def get_system_prompt(self) -> str:
        return """You are a Memory & Context Agent for conversation management.

Your responsibilities:
1. Resolve references like "them", "that supplier", "the first one"
2. Maintain context across conversation turns
3. Track mentioned suppliers, processes, requirements
4. Handle session persistence via Redis

Reference Resolution:
- "that supplier" → last mentioned supplier
- "the first one" → first in last result list
- "them" → current supplier set
- "same requirements" → previous search criteria

Context Tracking:
- Recent suppliers discussed
- Active search criteria
- Comparison in progress
- User preferences

Decay Policy:
- Session context: 1 hour TTL
- Supplier references: 10 messages
- Search criteria: until new search"""

    async def process(self, state: ChatState) -> ChatState:
        """Update and manage conversation context."""
        start_time = datetime.now()

        # Resolve any references in the current message
        resolved_entities = self._resolve_references(state)

        # Update entities with resolved values
        if resolved_entities:
            state.entities.update(resolved_entities)

        # Track context for future reference
        context_update = self._update_context_tracking(state)

        state.agent_outputs[self.name] = self.create_output(
            success=True,
            data={
                "resolved_references": list(resolved_entities.keys()),
                "context_updates": context_update,
            },
            start_time=start_time,
        )

        return state

    def _resolve_references(self, state: ChatState) -> dict:
        """Resolve references in the current message."""
        resolved = {}

        # Get the last user message content
        message_content = ""
        for msg in reversed(state.messages):
            if hasattr(msg, "content") and hasattr(msg, "type"):
                if msg.type == "human":
                    message_content = str(msg.content).lower()
                    break

        if not message_content:
            return resolved

        # Check for supplier references
        supplier_refs = ["that supplier", "them", "this supplier", "the supplier"]
        for ref in supplier_refs:
            if ref in message_content and state.suppliers:
                resolved["referenced_supplier"] = state.suppliers[0].id
                break

        # Check for ordinal references
        ordinal_map = {
            "the first": 0,
            "the second": 1,
            "the third": 2,
            "first one": 0,
            "second one": 1,
            "third one": 2,
        }
        for phrase, idx in ordinal_map.items():
            if phrase in message_content and len(state.suppliers) > idx:
                resolved["referenced_supplier"] = state.suppliers[idx].id
                break

        # Check for criteria references
        if "same" in message_content or "previous" in message_content:
            if state.search_criteria:
                resolved["use_previous_criteria"] = True

        return resolved

    def _update_context_tracking(self, state: ChatState) -> dict:
        """Track context for future reference."""
        updates = {}

        # Track current suppliers
        if state.suppliers:
            updates["recent_suppliers"] = [s.id for s in state.suppliers[:5]]

        # Track search criteria
        if state.search_criteria:
            updates["last_search_criteria"] = state.search_criteria

        # Track intent history
        updates["last_intent"] = state.intent.value

        return updates
