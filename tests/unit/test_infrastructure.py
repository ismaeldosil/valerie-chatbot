"""Tests for infrastructure modules."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from valerie.infrastructure.evaluation import EvaluationAgent
from valerie.infrastructure.hitl import HITLAgent
from valerie.infrastructure.observability import (
    ObservabilityManager,
    get_observability,
)
from valerie.models import (
    ChatState,
    Intent,
    RiskScore,
    Supplier,
)


class TestEvaluationAgent:
    """Tests for EvaluationAgent."""

    @pytest.fixture
    def agent(self):
        return EvaluationAgent()

    def test_agent_name(self, agent):
        assert agent.name == "evaluation"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Evaluation" in prompt
        assert "relevance" in prompt.lower()

    def test_dimensions(self, agent):
        assert "relevance" in agent.DIMENSIONS
        assert "accuracy" in agent.DIMENSIONS
        assert sum(agent.DIMENSIONS.values()) == 1.0

    @pytest.mark.asyncio
    async def test_process_no_response(self, agent):
        """Test processing with no response to evaluate."""
        state = ChatState()
        result = await agent.process(state)
        assert result.agent_outputs["evaluation"].success
        assert result.agent_outputs["evaluation"].data.get("skipped")

    @pytest.mark.asyncio
    async def test_process_not_sampled(self, agent):
        """Test processing when not sampled."""
        state = ChatState()
        state.final_response = "Test response"

        with patch("random.random", return_value=1.0):
            result = await agent.process(state)
            assert result.agent_outputs["evaluation"].data.get("skipped")

    @pytest.mark.asyncio
    async def test_process_successful_evaluation(self, agent):
        """Test successful evaluation."""
        state = ChatState()
        state.final_response = "Here are the suppliers..."
        state.intent = Intent.SUPPLIER_SEARCH

        mock_response = json.dumps(
            {
                "scores": {
                    "relevance": 90,
                    "accuracy": 85,
                    "completeness": 80,
                    "clarity": 88,
                    "actionability": 75,
                    "safety": 100,
                },
                "overall": 86.5,
                "feedback": {
                    "strengths": ["Good relevance"],
                    "improvements": ["More details"],
                },
            }
        )

        with (
            patch("random.random", return_value=0.0),
            patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm,
        ):
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.evaluation_score == 86.5

    @pytest.mark.asyncio
    async def test_process_llm_error(self, agent):
        """Test handling LLM error."""
        state = ChatState()
        state.final_response = "Test"
        state.intent = Intent.SUPPLIER_SEARCH

        with (
            patch("random.random", return_value=0.0),
            patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm,
        ):
            mock_llm.side_effect = Exception("LLM error")
            result = await agent.process(state)
            assert not result.agent_outputs["evaluation"].success

    @pytest.mark.asyncio
    async def test_process_invalid_json(self, agent):
        """Test handling invalid JSON response."""
        state = ChatState()
        state.final_response = "Test"
        state.intent = Intent.SUPPLIER_SEARCH

        with (
            patch("random.random", return_value=0.0),
            patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm,
        ):
            mock_llm.return_value = "not json"
            result = await agent.process(state)
            # Should use default evaluation
            assert result.evaluation_score == 50.0

    def test_default_evaluation(self, agent):
        """Test default evaluation values."""
        default = agent._default_evaluation()
        assert default["overall"] == 50.0
        assert all(v == 50 for v in default["scores"].values())


class TestHITLAgent:
    """Tests for HITLAgent."""

    @pytest.fixture
    def agent(self):
        return HITLAgent()

    def test_agent_name(self, agent):
        assert agent.name == "hitl"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Human-in-the-Loop" in prompt

    def test_approval_triggers(self, agent):
        assert "itar_decision" in agent.APPROVAL_TRIGGERS
        assert "high_risk_supplier" in agent.APPROVAL_TRIGGERS

    @pytest.mark.asyncio
    async def test_process_no_approval_needed(self, agent):
        """Test processing when no approval is needed."""
        state = ChatState()
        state.requires_human_approval = False
        result = await agent.process(state)
        assert result.agent_outputs["hitl"].success
        assert not result.agent_outputs["hitl"].data["approval_needed"]

    @pytest.mark.asyncio
    async def test_process_with_decision(self, agent):
        """Test processing with existing decision."""
        state = ChatState()
        state.hitl_decision = {"action": "approve"}
        result = await agent.process(state)
        assert not result.requires_human_approval

    @pytest.mark.asyncio
    async def test_process_reject_decision(self, agent):
        """Test processing with reject decision."""
        state = ChatState()
        state.hitl_decision = {"action": "reject"}
        result = await agent.process(state)
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_process_modify_decision(self, agent):
        """Test processing with modify decision."""
        state = ChatState()
        state.hitl_decision = {
            "action": "modify",
            "modifications": {"entities": {"new_key": "value"}},
        }
        result = await agent.process(state)
        assert not result.requires_human_approval
        assert "new_key" in result.entities

    def test_determine_trigger_itar(self, agent):
        """Test trigger determination for ITAR."""
        state = ChatState()
        state.itar_flagged = True
        trigger, reason = agent._determine_trigger(state)
        assert trigger == "itar_decision"

    def test_determine_trigger_high_risk(self, agent):
        """Test trigger determination for high risk."""
        state = ChatState()
        state.itar_flagged = False
        state.risk_results = [RiskScore(supplier_id="SUP-001", overall_score=0.8)]
        trigger, reason = agent._determine_trigger(state)
        assert trigger == "high_risk_supplier"

    def test_determine_trigger_low_confidence(self, agent):
        """Test trigger determination for low confidence."""
        state = ChatState()
        state.itar_flagged = False
        state.confidence = 0.3
        trigger, reason = agent._determine_trigger(state)
        assert trigger == "low_confidence"

    def test_calculate_priority_critical(self, agent):
        """Test critical priority calculation."""
        state = ChatState()
        state.itar_flagged = True
        priority = agent._calculate_priority(state)
        assert priority == "critical"

    def test_calculate_priority_urgent(self, agent):
        """Test urgent priority calculation."""
        state = ChatState()
        state.risk_results = [RiskScore(supplier_id="SUP-001", overall_score=0.85)]
        priority = agent._calculate_priority(state)
        assert priority == "urgent"

    def test_calculate_priority_high(self, agent):
        """Test high priority calculation."""
        state = ChatState()
        state.risk_results = [RiskScore(supplier_id="SUP-001", overall_score=0.65)]
        priority = agent._calculate_priority(state)
        assert priority == "high"

    def test_calculate_priority_normal(self, agent):
        """Test normal priority calculation."""
        state = ChatState()
        priority = agent._calculate_priority(state)
        assert priority == "normal"

    def test_build_context(self, agent):
        """Test context building."""
        state = ChatState()
        state.intent = Intent.SUPPLIER_SEARCH
        state.confidence = 0.9
        state.suppliers = [Supplier(id="SUP-001", name="Test")]
        state.itar_flagged = False
        context = agent._build_context(state)
        assert context["intent"] == "supplier_search"
        assert context["confidence"] == 0.9
        assert "Test" in context["suppliers"]

    def test_get_decision_options_normal(self, agent):
        """Test normal decision options."""
        options = agent._get_decision_options("normal")
        option_ids = [o["id"] for o in options]
        assert "approve" in option_ids
        assert "reject" in option_ids

    def test_get_decision_options_itar(self, agent):
        """Test ITAR decision options."""
        options = agent._get_decision_options("itar_decision")
        option_ids = [o["id"] for o in options]
        assert "escalate" in option_ids


class TestObservabilityManager:
    """Tests for ObservabilityManager."""

    @pytest.fixture
    def manager(self):
        from valerie.infrastructure.observability import (
            reset_observability,
        )

        reset_observability()
        return ObservabilityManager()

    def test_get_observability_singleton(self):
        """Test observability singleton."""
        from valerie.infrastructure.observability import (
            reset_observability,
        )

        reset_observability()
        obs1 = get_observability()
        obs2 = get_observability()
        assert obs1 is obs2

    def test_trace_context_manager(self, manager):
        """Test trace context manager."""
        with manager.trace("test-trace") as trace_id:
            assert trace_id is not None
            assert len(trace_id) > 0

    def test_trace_with_metadata(self, manager):
        """Test trace with metadata."""
        metadata = {"session_id": "test-123", "user": "test-user"}
        with manager.trace("test-trace", metadata=metadata) as trace_id:
            assert trace_id is not None

    def test_span_context_manager(self, manager):
        """Test span context manager."""
        with manager.trace("test-trace"):
            with manager.span("test-span") as span_id:
                assert span_id is not None
                assert len(span_id) > 0

    def test_span_standalone(self, manager):
        """Test span without active trace creates standalone trace."""
        with manager.span("standalone-span") as span_id:
            assert span_id is not None

    def test_span_with_metadata(self, manager):
        """Test span with metadata."""
        with manager.trace("test-trace"):
            metadata = {"agent": "test_agent", "step": 1}
            with manager.span("test-span", metadata=metadata) as span_id:
                assert span_id is not None

    def test_trace_llm(self, manager):
        """Test LLM call tracing."""
        with manager.trace("test-trace"):
            manager.trace_llm(
                provider="anthropic",
                model="claude-3-haiku",
                messages=[{"role": "user", "content": "test"}],
                response="test response",
                tokens={"input_tokens": 10, "output_tokens": 20},
                duration_ms=100.5,
            )
        # Should not raise - metrics are recorded

    def test_trace_llm_no_tokens(self, manager):
        """Test LLM call tracing without tokens."""
        with manager.trace("test-trace"):
            manager.trace_llm(
                provider="anthropic",
                model="claude-3-haiku",
                messages=[{"role": "user", "content": "test"}],
                response="test response",
            )
        # Should not raise

    def test_set_provider_status(self, manager):
        """Test setting provider status."""
        manager.set_provider_status("anthropic", True)
        manager.set_provider_status("groq", False)
        # Should not raise - status is recorded in metrics

    def test_flush(self, manager):
        """Test flush method."""
        manager.flush()
        # Should not raise

    def test_backend_initialization(self, manager):
        """Test backend is initialized."""
        assert manager._backend is not None

    def test_environment_detection(self, manager):
        """Test environment detection."""
        assert manager.env is not None

    @pytest.mark.asyncio
    async def test_trace_agent_decorator(self, manager):
        """Test trace_agent decorator."""
        from valerie.infrastructure.correlation import (
            set_correlation_id,
        )

        # Set up correlation ID for tracing
        set_correlation_id("test-correlation-id")

        @manager.trace_agent("test_agent")
        async def mock_agent(state: ChatState) -> ChatState:
            return state

        state = ChatState()
        result = await mock_agent(state)
        assert result is not None

    @pytest.mark.asyncio
    async def test_trace_agent_decorator_error(self, manager):
        """Test trace_agent decorator with error."""
        from valerie.infrastructure.correlation import (
            set_correlation_id,
        )

        set_correlation_id("test-correlation-id")

        @manager.trace_agent("test_agent")
        async def mock_agent_error(state: ChatState) -> ChatState:
            raise ValueError("Test error")

        state = ChatState()

        with pytest.raises(ValueError):
            await mock_agent_error(state)

    @pytest.mark.asyncio
    async def test_trace_agent_decorator_no_correlation(self, manager):
        """Test trace_agent decorator without correlation ID."""
        from valerie.infrastructure.correlation import (
            reset_correlation_context,
        )

        reset_correlation_context()

        @manager.trace_agent("test_agent")
        async def mock_agent(state: ChatState) -> ChatState:
            return state

        state = ChatState()
        result = await mock_agent(state)
        assert result is not None
