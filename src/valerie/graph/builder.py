"""LangGraph graph builder for the supplier chatbot."""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..agents import (
    ComparisonAgent,
    ComplianceAgent,
    IntentClassifierAgent,
    MemoryContextAgent,
    ProcessExpertiseAgent,
    ResponseGenerationAgent,
    RiskAssessmentAgent,
    SupplierSearchAgent,
)
from ..infrastructure import (
    EvaluationAgent,
    FallbackAgent,
    GuardrailsAgent,
    HITLAgent,
    ObservabilityManager,
)
from ..models import ChatState, Intent

# Initialize agents
_intent_classifier = IntentClassifierAgent()
_supplier_search = SupplierSearchAgent()
_compliance = ComplianceAgent()
_comparison = ComparisonAgent()
_process_expertise = ProcessExpertiseAgent()
_risk_assessment = RiskAssessmentAgent()
_response_generation = ResponseGenerationAgent()
_memory_context = MemoryContextAgent()
_guardrails = GuardrailsAgent()
_hitl = HITLAgent()
_fallback = FallbackAgent()
_evaluation = EvaluationAgent()
_observability = ObservabilityManager()


# Node functions
async def guardrails_node(state: ChatState) -> ChatState:
    """Validate input through guardrails."""
    return await _guardrails.process(state)


async def intent_classifier_node(state: ChatState) -> ChatState:
    """Classify user intent and extract entities."""
    return await _intent_classifier.process(state)


async def supplier_search_node(state: ChatState) -> ChatState:
    """Search for suppliers based on criteria."""
    return await _supplier_search.process(state)


async def compliance_node(state: ChatState) -> ChatState:
    """Validate supplier compliance."""
    return await _compliance.process(state)


async def comparison_node(state: ChatState) -> ChatState:
    """Compare multiple suppliers."""
    return await _comparison.process(state)


async def process_expertise_node(state: ChatState) -> ChatState:
    """Answer technical process questions."""
    return await _process_expertise.process(state)


async def risk_assessment_node(state: ChatState) -> ChatState:
    """Assess supplier risks."""
    return await _risk_assessment.process(state)


async def memory_context_node(state: ChatState) -> ChatState:
    """Manage conversation context."""
    return await _memory_context.process(state)


async def hitl_node(state: ChatState) -> ChatState:
    """Handle human-in-the-loop approval if needed."""
    if state.requires_human_approval:
        return await _hitl.process(state)
    return state


async def response_generation_node(state: ChatState) -> ChatState:
    """Generate the final response."""
    return await _response_generation.process(state)


async def fallback_node(state: ChatState) -> ChatState:
    """Handle errors and apply fallback strategies."""
    return await _fallback.process(state)


async def evaluation_node(state: ChatState) -> ChatState:
    """Evaluate response quality."""
    return await _evaluation.process(state)


# Routing functions
def route_after_guardrails(state: ChatState) -> Literal["intent_classifier", "error_response"]:
    """Route after guardrails check."""
    if state.guardrails_passed:
        return "intent_classifier"
    return "error_response"


def route_after_intent(
    state: ChatState,
) -> Literal[
    "supplier_search",
    "process_expertise",
    "memory_context",
    "response_generation",
]:
    """Route based on classified intent."""
    intent = state.intent

    if intent in (Intent.SUPPLIER_SEARCH, Intent.SUPPLIER_COMPARISON, Intent.RISK_ASSESSMENT):
        return "supplier_search"
    elif intent == Intent.TECHNICAL_QUESTION:
        return "process_expertise"
    elif intent == Intent.CLARIFICATION:
        return "memory_context"
    else:
        # GREETING, UNKNOWN, COMPLIANCE_CHECK
        return "response_generation"


def route_after_search(
    state: ChatState,
) -> Literal["compliance", "response_generation"]:
    """Route after supplier search."""
    if state.suppliers:
        return "compliance"
    return "response_generation"


def route_after_compliance(
    state: ChatState,
) -> Literal["comparison", "risk_assessment", "hitl", "response_generation"]:
    """Route after compliance check."""
    if state.requires_human_approval:
        return "hitl"
    if state.intent == Intent.SUPPLIER_COMPARISON:
        return "comparison"
    if state.intent == Intent.RISK_ASSESSMENT:
        return "risk_assessment"
    return "response_generation"


def route_after_hitl(
    state: ChatState,
) -> Literal["response_generation", "comparison", "risk_assessment"]:
    """Route after HITL decision."""
    if state.error:
        return "response_generation"
    if state.intent == Intent.SUPPLIER_COMPARISON:
        return "comparison"
    if state.intent == Intent.RISK_ASSESSMENT:
        return "risk_assessment"
    return "response_generation"


def build_graph() -> StateGraph:
    """Build the LangGraph state graph for the chatbot."""
    # Create the graph with ChatState
    graph = StateGraph(ChatState)

    # Add nodes
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("intent_classifier", intent_classifier_node)
    graph.add_node("supplier_search", supplier_search_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("comparison", comparison_node)
    graph.add_node("process_expertise", process_expertise_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("memory_context", memory_context_node)
    graph.add_node("hitl", hitl_node)
    graph.add_node("response_generation", response_generation_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("evaluation", evaluation_node)

    # Add edges from START
    graph.add_edge(START, "guardrails")

    # Add conditional edges
    graph.add_conditional_edges(
        "guardrails",
        route_after_guardrails,
        {
            "intent_classifier": "intent_classifier",
            "error_response": "response_generation",
        },
    )

    graph.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "supplier_search": "supplier_search",
            "process_expertise": "process_expertise",
            "memory_context": "memory_context",
            "response_generation": "response_generation",
        },
    )

    graph.add_conditional_edges(
        "supplier_search",
        route_after_search,
        {
            "compliance": "compliance",
            "response_generation": "response_generation",
        },
    )

    graph.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "comparison": "comparison",
            "risk_assessment": "risk_assessment",
            "hitl": "hitl",
            "response_generation": "response_generation",
        },
    )

    graph.add_conditional_edges(
        "hitl",
        route_after_hitl,
        {
            "response_generation": "response_generation",
            "comparison": "comparison",
            "risk_assessment": "risk_assessment",
        },
    )

    # Linear edges
    graph.add_edge("comparison", "response_generation")
    graph.add_edge("risk_assessment", "response_generation")
    graph.add_edge("process_expertise", "response_generation")
    graph.add_edge("memory_context", "response_generation")
    graph.add_edge("response_generation", "fallback")
    graph.add_edge("fallback", "evaluation")
    graph.add_edge("evaluation", END)

    return graph


def get_compiled_graph(checkpointer: bool = True):
    """Get a compiled graph ready for execution."""
    graph = build_graph()

    if checkpointer:
        # Use memory saver for checkpointing (enables HITL interrupt/resume)
        memory = MemorySaver()
        return graph.compile(checkpointer=memory)

    return graph.compile()
