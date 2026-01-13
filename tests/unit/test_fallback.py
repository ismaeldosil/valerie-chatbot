"""Unit tests for Fallback agent and Circuit Breaker."""

from datetime import datetime, timedelta

import pytest

from valerie.infrastructure.fallback import (
    CircuitBreaker,
    CircuitState,
    FallbackAgent,
)
from valerie.models import AgentOutput, ChatState


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts closed."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()

    def test_failures_below_threshold(self):
        """Test failures below threshold keep circuit closed."""
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()

    def test_failures_at_threshold_opens_circuit(self):
        """Test circuit opens at failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()

    def test_success_resets_counter(self):
        """Test success resets failure counter."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_timeout_moves_to_half_open(self):
        """Test timeout moves circuit to half-open."""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Simulate timeout
        cb.last_failure_time = datetime.now() - timedelta(seconds=2)
        assert cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        cb = CircuitBreaker(failure_threshold=10, timeout_seconds=120)
        assert cb.failure_threshold == 10
        assert cb.timeout_seconds == 120


class TestFallbackAgent:
    """Tests for FallbackAgent."""

    @pytest.fixture
    def agent(self):
        """Create fallback agent instance."""
        return FallbackAgent()

    def test_agent_name(self, agent):
        """Test agent has correct name."""
        assert agent.name == "fallback"

    def test_system_prompt_exists(self, agent):
        """Test system prompt is defined."""
        prompt = agent.get_system_prompt()
        assert len(prompt) > 0
        assert "Circuit Breaker" in prompt

    def test_get_circuit_breaker_creates_new(self, agent):
        """Test getting circuit breaker creates new instance."""
        cb = agent.get_circuit_breaker("test_service")
        assert cb is not None
        assert cb.state == CircuitState.CLOSED

    def test_get_circuit_breaker_returns_same(self, agent):
        """Test getting circuit breaker returns same instance."""
        cb1 = agent.get_circuit_breaker("test_service")
        cb2 = agent.get_circuit_breaker("test_service")
        assert cb1 is cb2

    def test_get_different_circuit_breakers(self, agent):
        """Test different services get different circuit breakers."""
        cb1 = agent.get_circuit_breaker("service_a")
        cb2 = agent.get_circuit_breaker("service_b")
        assert cb1 is not cb2

    def test_classify_transient_error(self, agent):
        """Test transient error classification."""
        assert agent._classify_error("Connection timeout") == "transient"
        assert agent._classify_error("Temporary failure") == "transient"
        assert agent._classify_error("Please retry later") == "transient"

    def test_classify_permanent_error(self, agent):
        """Test permanent error classification."""
        assert agent._classify_error("Authentication failed") == "permanent"
        assert agent._classify_error("Permission denied") == "permanent"
        assert agent._classify_error("Resource not found") == "permanent"

    def test_classify_unknown_error(self, agent):
        """Test unknown error classification."""
        assert agent._classify_error("Something went wrong") == "unknown"

    def test_find_no_failed_agents(self, agent):
        """Test finding no failed agents."""
        state = ChatState()
        state.agent_outputs["search"] = AgentOutput(
            agent_name="search",
            success=True,
            data={},
        )
        failed = agent._find_failed_agents(state)
        assert len(failed) == 0

    def test_find_failed_agents(self, agent):
        """Test finding failed agents."""
        state = ChatState()
        state.agent_outputs["search"] = AgentOutput(
            agent_name="search",
            success=False,
            error="API timeout",
        )
        state.agent_outputs["compliance"] = AgentOutput(
            agent_name="compliance",
            success=True,
            data={},
        )
        failed = agent._find_failed_agents(state)
        assert "search" in failed
        assert "compliance" not in failed

    @pytest.mark.asyncio
    async def test_process_no_errors(self, agent):
        """Test processing state with no errors."""
        state = ChatState()
        state.agent_outputs["search"] = AgentOutput(
            agent_name="search",
            success=True,
            data={},
        )
        result = await agent.process(state)
        assert not result.degraded_mode
        assert agent.name in result.agent_outputs
        assert result.agent_outputs[agent.name].success

    @pytest.mark.asyncio
    async def test_process_with_errors_degrades(self, agent):
        """Test processing state with errors triggers degradation."""
        state = ChatState()
        state.agent_outputs["oracle"] = AgentOutput(
            agent_name="oracle",
            success=False,
            error="Connection refused",
        )
        result = await agent.process(state)
        assert result.degraded_mode

    def test_apply_degradation_adds_warning(self, agent):
        """Test degradation adds warning to response."""
        state = ChatState()
        state.final_response = "Here are your results"
        result = agent._apply_degradation(state, {})
        response_lower = result.final_response.lower()
        assert "incomplete" in response_lower or "partial" in response_lower

    def test_apply_degradation_no_response(self, agent):
        """Test degradation with no existing response."""
        state = ChatState()
        result = agent._apply_degradation(state, {})
        assert result.final_response is not None
        assert len(result.final_response) > 0
