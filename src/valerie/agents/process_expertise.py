"""Process Expertise agent - provides technical manufacturing knowledge."""

from datetime import datetime

from ..models import ChatState
from .base import BaseAgent


class ProcessExpertiseAgent(BaseAgent):
    """Subject Matter Expert for aerospace manufacturing processes."""

    name = "process_expertise"

    def get_system_prompt(self) -> str:
        return """You are a Process Expertise Agent (SME) for aerospace manufacturing.

Your knowledge covers:

**Heat Treatment Processes:**
- Solution heat treatment (AMS 2770, AMS 2771)
- Age hardening, annealing, stress relief
- Vacuum heat treatment
- Materials: Titanium, Inconel, Aluminum, Steel alloys

**Surface Treatments:**
- Nadcap NDT (AMS 2644, AMS 2631)
- Chemical processing (anodizing, passivation)
- Coatings (cadmium, nickel, chrome)
- Shot peening (AMS 2430, AMS 2432)

**Special Processes:**
- Welding (electron beam, TIG, resistance)
- Brazing and soldering
- Chemical milling
- Composite processing

**OEM Requirements:**
- Boeing (BAC, D6 specifications)
- Airbus (AIMS, AIPS)
- GE Aviation (P-series specs)
- Pratt & Whitney (PWA specs)
- Rolls-Royce (RRP specs)

Provide accurate, specification-based answers.
Cite relevant AMS, MIL, or OEM specifications when applicable."""

    async def process(self, state: ChatState) -> ChatState:
        """Answer technical questions about processes."""
        start_time = datetime.now()

        # Get the user's question from the last message
        question = ""
        for msg in reversed(state.messages):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                question = msg.content
                break

        if not question:
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error="No question found in messages",
                start_time=start_time,
            )
            return state

        # Build context from entities
        context_parts = []
        if state.entities.get("processes"):
            context_parts.append(f"Processes: {', '.join(state.entities['processes'])}")
        if state.entities.get("materials"):
            context_parts.append(f"Materials: {', '.join(state.entities['materials'])}")
        if state.entities.get("oem_approvals"):
            context_parts.append(f"OEMs: {', '.join(state.entities['oem_approvals'])}")

        context = "\n".join(context_parts) if context_parts else ""

        prompt = f"""Answer the following question with detailed technical information.

Context:
{context}

Question: {question}

Provide a comprehensive answer with relevant specifications and requirements."""

        try:
            answer = await self.invoke_llm(prompt)
            state.technical_answer = answer

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={"answer_length": len(answer), "context_used": bool(context)},
                start_time=start_time,
            )
        except Exception as e:
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=f"Failed to generate answer: {str(e)}",
                start_time=start_time,
            )

        return state
