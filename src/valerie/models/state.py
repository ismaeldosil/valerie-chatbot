"""State models for the LangGraph chatbot."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field


class Intent(str, Enum):
    """User intent classifications."""

    # Core supplier operations
    SUPPLIER_SEARCH = "supplier_search"
    SUPPLIER_COMPARISON = "supplier_comparison"
    COMPLIANCE_CHECK = "compliance_check"
    TECHNICAL_QUESTION = "technical_question"
    RISK_ASSESSMENT = "risk_assessment"

    # Product and category intents
    PRODUCT_SEARCH = "product_search"
    CATEGORY_BROWSE = "category_browse"
    PRICE_INQUIRY = "price_inquiry"
    SUPPLIER_DETAIL = "supplier_detail"
    TOP_SUPPLIERS = "top_suppliers"
    ITEM_COMPARISON = "item_comparison"

    # Common intents
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class Certification(BaseModel):
    """Certification information for a supplier."""

    type: str  # nadcap, as9100, itar, iso
    scope: str | None = None
    expiry_date: datetime | None = None
    status: str = "active"  # active, expired, pending
    auditor: str | None = None


class Supplier(BaseModel):
    """Supplier data model."""

    id: str
    name: str
    location: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    oem_approvals: list[str] = Field(default_factory=list)
    quality_rate: float | None = None  # 0-100
    on_time_delivery: float | None = None  # 0-100
    risk_score: float | None = None  # 0-1
    contact_email: str | None = None
    contact_phone: str | None = None


class ComplianceInfo(BaseModel):
    """Compliance validation result."""

    supplier_id: str
    is_compliant: bool
    certifications_valid: list[str] = Field(default_factory=list)
    certifications_missing: list[str] = Field(default_factory=list)
    certifications_expiring: list[str] = Field(default_factory=list)
    itar_cleared: bool | None = None
    notes: str | None = None


class RiskScore(BaseModel):
    """Risk assessment result."""

    supplier_id: str
    overall_score: float  # 0-1, higher = more risky
    categories: dict[str, float] = Field(default_factory=dict)
    # Categories: compliance, financial, capacity, geographic, quality, dependency
    mitigations: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """Standard output from any agent."""

    agent_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    confidence: float = 1.0
    processing_time_ms: int = 0


class HITLRequest(BaseModel):
    """Human-in-the-loop request."""

    request_type: str  # approval_required, review_request, escalation, itar_decision
    priority: str = "normal"  # low, normal, high, urgent, critical
    context: dict[str, Any] = Field(default_factory=dict)
    decision_options: list[dict[str, Any]] = Field(default_factory=list)
    timeout_ms: int = 86400000  # 24 hours default


class ChatState(BaseModel):
    """Main state for the LangGraph chatbot.

    This state is passed through all nodes in the graph.
    """

    # Core conversation
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)
    session_id: str = ""
    user_id: str | None = None
    user_role: str = "standard_user"

    # Intent and entities
    intent: Intent = Intent.UNKNOWN
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0

    # Search criteria
    search_criteria: dict[str, Any] = Field(default_factory=dict)

    # Results
    suppliers: list[Supplier] = Field(default_factory=list)
    compliance_results: list[ComplianceInfo] = Field(default_factory=list)
    risk_results: list[RiskScore] = Field(default_factory=list)
    comparison_data: dict[str, Any] = Field(default_factory=dict)
    technical_answer: str | None = None

    # Agent outputs
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)

    # Infrastructure flags
    guardrails_passed: bool = True
    guardrails_warnings: list[str] = Field(default_factory=list)
    pii_detected: bool = False
    itar_flagged: bool = False

    # HITL
    requires_human_approval: bool = False
    hitl_request: HITLRequest | None = None
    hitl_decision: dict[str, Any] | None = None

    # Response
    final_response: str | None = None
    response_type: str = "text"  # text, table, comparison, error

    # Quality
    evaluation_score: float | None = None
    evaluation_feedback: dict[str, Any] = Field(default_factory=dict)

    # Tracing
    trace_id: str | None = None
    span_id: str | None = None

    # Error handling
    error: str | None = None
    degraded_mode: bool = False

    # Domain-specific state extensions
    domain_data: dict[str, dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
