"""Unit tests for LangGraph graph builder."""

from unittest.mock import AsyncMock, patch

import pytest

from valerie.graph.builder import (
    build_graph,
    comparison_node,
    compliance_node,
    evaluation_node,
    fallback_node,
    get_compiled_graph,
    guardrails_node,
    hitl_node,
    intent_classifier_node,
    memory_context_node,
    process_expertise_node,
    response_generation_node,
    risk_assessment_node,
    route_after_compliance,
    route_after_guardrails,
    route_after_hitl,
    route_after_intent,
    route_after_search,
    supplier_search_node,
)
from valerie.models import ChatState, Intent


class TestGraphBuilder:
    """Tests for graph building."""

    def test_build_graph_creates_graph(self):
        """Test that build_graph creates a valid graph."""
        graph = build_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        """Test that graph contains all expected nodes."""
        graph = build_graph()
        expected_nodes = [
            "guardrails",
            "intent_classifier",
            "supplier_search",
            "compliance",
            "comparison",
            "process_expertise",
            "risk_assessment",
            "memory_context",
            "hitl",
            "response_generation",
            "fallback",
            "evaluation",
        ]
        for node in expected_nodes:
            assert node in graph.nodes, f"Missing node: {node}"

    def test_graph_compiles(self):
        """Test that graph compiles without errors."""
        graph = build_graph()
        compiled = graph.compile()
        assert compiled is not None


class TestRoutingFunctions:
    """Tests for routing logic."""

    def test_route_after_guardrails_passed(self):
        """Test routing when guardrails pass."""
        state = ChatState(guardrails_passed=True)
        result = route_after_guardrails(state)
        assert result == "intent_classifier"

    def test_route_after_guardrails_failed(self):
        """Test routing when guardrails fail."""
        state = ChatState(guardrails_passed=False)
        result = route_after_guardrails(state)
        assert result == "error_response"

    def test_route_supplier_search_intent(self):
        """Test routing for supplier search intent."""
        state = ChatState(intent=Intent.SUPPLIER_SEARCH)
        result = route_after_intent(state)
        assert result == "supplier_search"

    def test_route_comparison_intent(self):
        """Test routing for comparison intent."""
        state = ChatState(intent=Intent.SUPPLIER_COMPARISON)
        result = route_after_intent(state)
        assert result == "supplier_search"

    def test_route_risk_assessment_intent(self):
        """Test routing for risk assessment intent."""
        state = ChatState(intent=Intent.RISK_ASSESSMENT)
        result = route_after_intent(state)
        assert result == "supplier_search"

    def test_route_technical_question_intent(self):
        """Test routing for technical question intent."""
        state = ChatState(intent=Intent.TECHNICAL_QUESTION)
        result = route_after_intent(state)
        assert result == "process_expertise"

    def test_route_clarification_intent(self):
        """Test routing for clarification intent."""
        state = ChatState(intent=Intent.CLARIFICATION)
        result = route_after_intent(state)
        assert result == "memory_context"

    def test_route_greeting_intent(self):
        """Test routing for greeting intent."""
        state = ChatState(intent=Intent.GREETING)
        result = route_after_intent(state)
        assert result == "response_generation"

    def test_route_unknown_intent(self):
        """Test routing for unknown intent."""
        state = ChatState(intent=Intent.UNKNOWN)
        result = route_after_intent(state)
        assert result == "response_generation"

    def test_route_after_search_with_results(self, sample_suppliers):
        """Test routing after search with results."""
        state = ChatState()
        state.suppliers = sample_suppliers
        result = route_after_search(state)
        assert result == "compliance"

    def test_route_after_search_no_results(self):
        """Test routing after search with no results."""
        state = ChatState()
        state.suppliers = []
        result = route_after_search(state)
        assert result == "response_generation"

    def test_route_after_compliance_needs_approval(self):
        """Test routing when human approval needed."""
        state = ChatState(
            intent=Intent.SUPPLIER_SEARCH,
            requires_human_approval=True,
        )
        result = route_after_compliance(state)
        assert result == "hitl"

    def test_route_after_compliance_comparison(self):
        """Test routing to comparison after compliance."""
        state = ChatState(
            intent=Intent.SUPPLIER_COMPARISON,
            requires_human_approval=False,
        )
        result = route_after_compliance(state)
        assert result == "comparison"

    def test_route_after_compliance_risk(self):
        """Test routing to risk assessment after compliance."""
        state = ChatState(
            intent=Intent.RISK_ASSESSMENT,
            requires_human_approval=False,
        )
        result = route_after_compliance(state)
        assert result == "risk_assessment"

    def test_route_after_compliance_default(self):
        """Test default routing after compliance."""
        state = ChatState(
            intent=Intent.SUPPLIER_SEARCH,
            requires_human_approval=False,
        )
        result = route_after_compliance(state)
        assert result == "response_generation"

    def test_route_after_hitl_with_error(self):
        """Test routing after HITL with error."""
        state = ChatState(
            intent=Intent.SUPPLIER_SEARCH,
            error="User rejected",
        )
        result = route_after_hitl(state)
        assert result == "response_generation"

    def test_route_after_hitl_comparison(self):
        """Test routing after HITL to comparison."""
        state = ChatState(
            intent=Intent.SUPPLIER_COMPARISON,
            error=None,
        )
        result = route_after_hitl(state)
        assert result == "comparison"

    def test_route_after_hitl_risk_assessment(self):
        """Test routing after HITL to risk assessment."""
        state = ChatState(
            intent=Intent.RISK_ASSESSMENT,
            error=None,
        )
        result = route_after_hitl(state)
        assert result == "risk_assessment"

    def test_route_after_hitl_default(self):
        """Test default routing after HITL."""
        state = ChatState(
            intent=Intent.SUPPLIER_SEARCH,
            error=None,
        )
        result = route_after_hitl(state)
        assert result == "response_generation"


class TestGetCompiledGraph:
    """Tests for get_compiled_graph function."""

    def test_get_compiled_graph_with_checkpointer(self):
        """Test getting compiled graph with checkpointer."""
        compiled = get_compiled_graph(checkpointer=True)
        assert compiled is not None

    def test_get_compiled_graph_without_checkpointer(self):
        """Test getting compiled graph without checkpointer."""
        compiled = get_compiled_graph(checkpointer=False)
        assert compiled is not None


class TestNodeFunctions:
    """Tests for node functions."""

    @pytest.mark.asyncio
    async def test_guardrails_node(self):
        """Test guardrails node function."""
        state = ChatState()
        with patch("valerie.graph.builder._guardrails") as mock_guardrails:
            mock_guardrails.process = AsyncMock(return_value=state)
            result = await guardrails_node(state)
            mock_guardrails.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_intent_classifier_node(self):
        """Test intent classifier node function."""
        state = ChatState()
        with patch("valerie.graph.builder._intent_classifier") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await intent_classifier_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_supplier_search_node(self):
        """Test supplier search node function."""
        state = ChatState()
        with patch("valerie.graph.builder._supplier_search") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await supplier_search_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_compliance_node(self):
        """Test compliance node function."""
        state = ChatState()
        with patch("valerie.graph.builder._compliance") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await compliance_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_comparison_node(self):
        """Test comparison node function."""
        state = ChatState()
        with patch("valerie.graph.builder._comparison") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await comparison_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_process_expertise_node(self):
        """Test process expertise node function."""
        state = ChatState()
        with patch("valerie.graph.builder._process_expertise") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await process_expertise_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_risk_assessment_node(self):
        """Test risk assessment node function."""
        state = ChatState()
        with patch("valerie.graph.builder._risk_assessment") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await risk_assessment_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_memory_context_node(self):
        """Test memory context node function."""
        state = ChatState()
        with patch("valerie.graph.builder._memory_context") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await memory_context_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_hitl_node_with_approval(self):
        """Test HITL node function when approval is needed."""
        state = ChatState(requires_human_approval=True)
        with patch("valerie.graph.builder._hitl") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await hitl_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_hitl_node_no_approval(self):
        """Test HITL node function when no approval is needed."""
        state = ChatState(requires_human_approval=False)
        with patch("valerie.graph.builder._hitl") as mock_agent:
            result = await hitl_node(state)
            mock_agent.process.assert_not_called()
            assert result == state

    @pytest.mark.asyncio
    async def test_response_generation_node(self):
        """Test response generation node function."""
        state = ChatState()
        with patch("valerie.graph.builder._response_generation") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await response_generation_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_fallback_node(self):
        """Test fallback node function."""
        state = ChatState()
        with patch("valerie.graph.builder._fallback") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await fallback_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state

    @pytest.mark.asyncio
    async def test_evaluation_node(self):
        """Test evaluation node function."""
        state = ChatState()
        with patch("valerie.graph.builder._evaluation") as mock_agent:
            mock_agent.process = AsyncMock(return_value=state)
            result = await evaluation_node(state)
            mock_agent.process.assert_called_once_with(state)
            assert result == state
