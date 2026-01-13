"""Evaluation agent - assesses response quality using LLM-as-Judge."""

import json
from datetime import datetime

from ..agents.base import BaseAgent
from ..models import ChatState


class EvaluationAgent(BaseAgent):
    """LLM-as-Judge for evaluating response quality."""

    name = "evaluation"

    # Evaluation dimensions with weights
    DIMENSIONS = {
        "relevance": 0.25,
        "accuracy": 0.25,
        "completeness": 0.20,
        "clarity": 0.15,
        "actionability": 0.10,
        "safety": 0.05,
    }

    def get_system_prompt(self) -> str:
        return """You are an Evaluation Agent using LLM-as-Judge methodology.

Evaluate responses across these dimensions (0-100 scale):

1. **Relevance** (25%): Does the response address the user's query?
2. **Accuracy** (25%): Is the information factually correct?
3. **Completeness** (20%): Are all aspects of the query addressed?
4. **Clarity** (15%): Is the response clear and well-structured?
5. **Actionability** (10%): Can the user take action based on this?
6. **Safety** (5%): Is the response appropriate and safe?

Output JSON format:
{
    "scores": {
        "relevance": 85,
        "accuracy": 90,
        "completeness": 80,
        "clarity": 85,
        "actionability": 75,
        "safety": 100
    },
    "overall": 85.5,
    "feedback": {
        "strengths": ["...", "..."],
        "improvements": ["...", "..."]
    }
}"""

    async def process(self, state: ChatState) -> ChatState:
        """Evaluate the final response quality."""
        start_time = datetime.now()

        # Only evaluate if we have a final response
        if not state.final_response:
            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={"skipped": True, "reason": "No response to evaluate"},
                start_time=start_time,
            )
            return state

        # Check if we should sample this request
        import random

        if random.random() > self.settings.evaluation_sample_rate:
            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={"skipped": True, "reason": "Not sampled"},
                start_time=start_time,
            )
            return state

        try:
            evaluation = await self._evaluate_response(state)
            state.evaluation_score = evaluation.get("overall", 0)
            state.evaluation_feedback = evaluation.get("feedback", {})

            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data=evaluation,
                start_time=start_time,
            )
        except Exception as e:
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=f"Evaluation failed: {str(e)}",
                start_time=start_time,
            )

        return state

    async def _evaluate_response(self, state: ChatState) -> dict:
        """Evaluate the response using LLM-as-Judge."""
        # Get the original query
        query = ""
        for msg in state.messages:
            if hasattr(msg, "type") and msg.type == "human":
                query = str(msg.content)
                break

        prompt = f"""Evaluate the following chatbot response.

User Query: {query}

Intent: {state.intent.value}

Response:
{state.final_response}

Additional Context:
- Suppliers found: {len(state.suppliers)}
- Compliance checks: {len(state.compliance_results)}
- Risk assessments: {len(state.risk_results)}
- ITAR flagged: {state.itar_flagged}

Evaluate and provide scores (0-100) for each dimension.
Respond with JSON only."""

        response = await self.invoke_llm(prompt)

        # Parse the evaluation
        try:
            # Try to extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                evaluation = json.loads(response[start:end])
            else:
                evaluation = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to default scores
            evaluation = self._default_evaluation()

        # Calculate weighted overall score if not provided
        if "overall" not in evaluation:
            scores = evaluation.get("scores", {})
            overall = sum(scores.get(dim, 50) * weight for dim, weight in self.DIMENSIONS.items())
            evaluation["overall"] = round(overall, 1)

        return evaluation

    def _default_evaluation(self) -> dict:
        """Return default evaluation when LLM fails."""
        return {
            "scores": {dim: 50 for dim in self.DIMENSIONS},
            "overall": 50.0,
            "feedback": {
                "strengths": ["Unable to evaluate"],
                "improvements": ["Evaluation service unavailable"],
            },
        }
