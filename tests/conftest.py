"""Pytest configuration and shared fixtures."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from valerie.data.sources.mock import MockDataSource
from valerie.models import (
    AgentOutput,
    Certification,
    ChatState,
    ComplianceInfo,
    Intent,
    RiskScore,
    Supplier,
)


@pytest.fixture
def mock_data_source():
    """Create a mock data source for testing."""
    return MockDataSource()


@pytest.fixture
def sample_supplier():
    """Create a sample supplier for testing."""
    return Supplier(
        id="SUP-001",
        name="Aerotech Precision",
        location="Los Angeles, CA",
        capabilities=["heat_treatment", "ndt", "machining"],
        certifications=[
            Certification(type="nadcap", scope="Heat Treating", status="active"),
            Certification(type="as9100", scope="Quality", status="active"),
        ],
        oem_approvals=["Boeing", "Airbus"],
        quality_rate=98.5,
        on_time_delivery=96.2,
        risk_score=0.15,
    )


@pytest.fixture
def sample_suppliers():
    """Create multiple sample suppliers for testing."""
    return [
        Supplier(
            id="SUP-001",
            name="Aerotech Precision",
            location="Los Angeles, CA",
            capabilities=["heat_treatment", "ndt"],
            quality_rate=98.5,
            on_time_delivery=96.2,
            risk_score=0.15,
        ),
        Supplier(
            id="SUP-002",
            name="Pacific Coatings",
            location="Seattle, WA",
            capabilities=["coating", "painting"],
            quality_rate=97.0,
            on_time_delivery=94.5,
            risk_score=0.22,
        ),
        Supplier(
            id="SUP-003",
            name="Midwest Processing",
            location="Cleveland, OH",
            capabilities=["heat_treatment", "forging"],
            quality_rate=99.1,
            on_time_delivery=97.8,
            risk_score=0.12,
        ),
    ]


@pytest.fixture
def sample_compliance():
    """Create sample compliance info."""
    return ComplianceInfo(
        supplier_id="SUP-001",
        is_compliant=True,
        certifications_valid=["nadcap", "as9100"],
        certifications_missing=[],
        certifications_expiring=[],
        itar_cleared=False,
    )


@pytest.fixture
def sample_risk():
    """Create sample risk score."""
    return RiskScore(
        supplier_id="SUP-001",
        overall_score=0.25,
        categories={
            "compliance": 0.1,
            "quality": 0.15,
            "financial": 0.3,
            "capacity": 0.2,
            "geographic": 0.25,
            "dependency": 0.35,
        },
        mitigations=["Monitor financial health quarterly"],
        alerts=[],
    )


@pytest.fixture
def empty_state():
    """Create empty chat state."""
    return ChatState(session_id="test-session")


@pytest.fixture
def state_with_message():
    """Create state with a user message."""
    state = ChatState(session_id="test-session")
    state.messages = [HumanMessage(content="Find Nadcap heat treat suppliers in California")]
    return state


@pytest.fixture
def state_with_suppliers(sample_suppliers):
    """Create state with suppliers."""
    state = ChatState(session_id="test-session")
    state.suppliers = sample_suppliers
    state.intent = Intent.SUPPLIER_SEARCH
    return state


@pytest.fixture
def state_with_comparison(sample_suppliers, sample_compliance, sample_risk):
    """Create state ready for comparison."""
    state = ChatState(session_id="test-session")
    state.suppliers = sample_suppliers
    state.intent = Intent.SUPPLIER_COMPARISON
    state.compliance_results = [
        sample_compliance,
        ComplianceInfo(supplier_id="SUP-002", is_compliant=True),
        ComplianceInfo(supplier_id="SUP-003", is_compliant=True),
    ]
    state.risk_results = [
        sample_risk,
        RiskScore(supplier_id="SUP-002", overall_score=0.35, categories={}),
        RiskScore(supplier_id="SUP-003", overall_score=0.18, categories={}),
    ]
    return state


@pytest.fixture
def state_with_itar():
    """Create state with ITAR flag."""
    state = ChatState(session_id="test-session")
    state.messages = [HumanMessage(content="Need ITAR cleared supplier")]
    state.itar_flagged = True
    state.requires_human_approval = True
    return state


@pytest.fixture
def state_with_errors():
    """Create state with agent errors."""
    state = ChatState(session_id="test-session")
    state.agent_outputs["oracle"] = AgentOutput(
        agent_name="oracle",
        success=False,
        error="Connection timeout",
    )
    return state


@pytest.fixture
def conversation_state():
    """Create state with conversation history."""
    state = ChatState(session_id="test-session")
    state.messages = [
        HumanMessage(content="Find heat treat suppliers"),
        AIMessage(content="I found 3 suppliers..."),
        HumanMessage(content="Compare the first two"),
    ]
    return state
