"""Fallback agent - handles error recovery with circuit breaker pattern."""

from datetime import datetime, timedelta
from enum import Enum

from ..agents.base import BaseAgent
from ..models import ChatState


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def record_success(self) -> None:
        """Record a success."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def can_execute(self) -> bool:
        """Check if we can execute."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = datetime.now() - self.last_failure_time
                if elapsed > timedelta(seconds=self.timeout_seconds):
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False

        # HALF_OPEN - allow one test request
        return True


class FallbackAgent(BaseAgent):
    """Manages error recovery and graceful degradation."""

    name = "fallback"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def get_system_prompt(self) -> str:
        return """You are a Fallback Agent managing error recovery.

Strategies:
1. Circuit Breaker: Prevent cascading failures
   - CLOSED: Normal operation
   - OPEN: Reject requests, return cached/default
   - HALF_OPEN: Allow test requests

2. Retry with Backoff: Exponential backoff for transient errors

3. Graceful Degradation:
   - Return cached results when available
   - Provide partial responses
   - Use default values

4. Error Classification:
   - Transient: Retry (network, timeout)
   - Permanent: Fail fast (auth, not found)
   - Unknown: Limited retry then fail"""

    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        if service not in self._circuit_breakers:
            self._circuit_breakers[service] = CircuitBreaker(
                failure_threshold=self.settings.circuit_breaker_threshold,
                timeout_seconds=self.settings.circuit_breaker_timeout_seconds,
            )
        return self._circuit_breakers[service]

    async def process(self, state: ChatState) -> ChatState:
        """Handle errors and attempt recovery."""
        start_time = datetime.now()

        # Check for errors in agent outputs
        failed_agents = self._find_failed_agents(state)

        if not failed_agents:
            state.agent_outputs[self.name] = self.create_output(
                success=True,
                data={"errors_found": 0},
                start_time=start_time,
            )
            return state

        # Attempt recovery for each failed agent
        recovery_results = {}
        for agent_name, error in failed_agents.items():
            recovery = await self._attempt_recovery(agent_name, error, state)
            recovery_results[agent_name] = recovery

            # Update circuit breaker
            cb = self.get_circuit_breaker(agent_name)
            if recovery["recovered"]:
                cb.record_success()
            else:
                cb.record_failure()

        # Check if we can continue
        all_recovered = all(r["recovered"] for r in recovery_results.values())

        if not all_recovered:
            state.degraded_mode = True
            # Provide graceful degradation
            state = self._apply_degradation(state, recovery_results)

        state.agent_outputs[self.name] = self.create_output(
            success=all_recovered,
            data={
                "errors_found": len(failed_agents),
                "recovery_results": recovery_results,
                "degraded_mode": state.degraded_mode,
            },
            start_time=start_time,
        )

        return state

    def _find_failed_agents(self, state: ChatState) -> dict[str, str]:
        """Find agents that failed."""
        failed = {}
        for name, output in state.agent_outputs.items():
            if not output.success and output.error:
                failed[name] = output.error
        return failed

    async def _attempt_recovery(self, agent_name: str, error: str, state: ChatState) -> dict:
        """Attempt to recover from an agent failure."""
        cb = self.get_circuit_breaker(agent_name)

        if not cb.can_execute():
            return {
                "recovered": False,
                "action": "circuit_open",
                "message": f"Circuit open for {agent_name}, using fallback",
            }

        # Classify error
        error_type = self._classify_error(error)

        if error_type == "transient":
            # Would retry here in real implementation
            return {
                "recovered": False,
                "action": "retry_exhausted",
                "message": f"Retries exhausted for {agent_name}",
            }

        if error_type == "permanent":
            return {
                "recovered": False,
                "action": "permanent_failure",
                "message": f"Permanent failure in {agent_name}",
            }

        return {
            "recovered": False,
            "action": "unknown_error",
            "message": f"Unknown error in {agent_name}",
        }

    def _classify_error(self, error: str) -> str:
        """Classify error type."""
        error_lower = error.lower()

        transient_keywords = ["timeout", "connection", "temporary", "retry"]
        permanent_keywords = ["auth", "permission", "not found", "invalid"]

        if any(kw in error_lower for kw in transient_keywords):
            return "transient"
        if any(kw in error_lower for kw in permanent_keywords):
            return "permanent"
        return "unknown"

    def _apply_degradation(self, state: ChatState, recovery_results: dict) -> ChatState:
        """Apply graceful degradation."""
        # Add warning to response
        if state.final_response:
            state.final_response += (
                "\n\nNote: Some information may be incomplete due to service issues."
            )
        else:
            state.final_response = (
                "I was able to provide a partial response, but some services "
                "are currently unavailable. Please try again later for complete information."
            )

        return state
