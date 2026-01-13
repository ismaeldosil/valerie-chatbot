"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SessionStatus(str, Enum):
    """Status of a chat session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ERROR = "error"


class AgentStatus(str, Enum):
    """Status of an agent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


# ============================================================================
# Request Schemas
# ============================================================================


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: str | None = Field(None, description="Existing session ID (optional)")
    user_id: str | None = Field(None, description="User identifier (optional)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Find heat treatment suppliers with Nadcap certification",
                "session_id": None,
                "user_id": "user-123",
            }
        }
    }


class SupplierSearchRequest(BaseModel):
    """Direct supplier search request."""

    processes: list[str] = Field(..., min_length=1, description="Processes to search for")
    certifications: list[str] | None = Field(None, description="Required certifications")
    location: str | None = Field(None, description="Preferred location")
    min_quality_score: float | None = Field(None, ge=0, le=1, description="Minimum quality score")

    model_config = {
        "json_schema_extra": {
            "example": {
                "processes": ["heat_treatment", "shot_peening"],
                "certifications": ["Nadcap", "AS9100D"],
                "location": "USA",
                "min_quality_score": 0.85,
            }
        }
    }


# ============================================================================
# Response Schemas
# ============================================================================


class Message(BaseModel):
    """A single chat message."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentExecution(BaseModel):
    """Details of an agent's execution."""

    agent_name: str
    display_name: str
    status: AgentStatus
    duration_ms: int = 0
    output: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    session_id: str
    message: str
    agents_executed: list[AgentExecution] = Field(default_factory=list)
    intent: str | None = None
    confidence: float | None = None
    requires_approval: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "sess-abc123",
                "message": "I found 3 suppliers for heat treatment...",
                "agents_executed": [
                    {
                        "agent_name": "guardrails",
                        "display_name": "Guardrails",
                        "status": "completed",
                        "duration_ms": 45,
                    }
                ],
                "intent": "supplier_search",
                "confidence": 0.94,
                "requires_approval": False,
            }
        }
    }


class SessionResponse(BaseModel):
    """Response with session details."""

    session_id: str
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    message_count: int
    messages: list[Message] = Field(default_factory=list)


class SupplierResult(BaseModel):
    """A supplier search result."""

    id: str
    name: str
    location: str
    processes: list[str]
    certifications: list[dict[str, Any]]
    quality_score: float
    delivery_score: float
    capacity_available: bool
    lead_time_days: int


class SupplierSearchResponse(BaseModel):
    """Response from supplier search."""

    suppliers: list[SupplierResult]
    total_count: int
    search_criteria: dict[str, Any]


# ============================================================================
# Health Check Schemas
# ============================================================================


class ServiceHealth(BaseModel):
    """Health status of a service."""

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: list[ServiceHealth] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    checks: dict[str, bool] = Field(default_factory=dict)


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorDetail(BaseModel):
    """Details of an error."""

    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
