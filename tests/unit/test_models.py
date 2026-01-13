"""Unit tests for data models."""

from datetime import datetime

from valerie.models import (
    AgentOutput,
    Certification,
    ChatState,
    ComplianceInfo,
    HITLRequest,
    Intent,
    RiskScore,
    Supplier,
)


class TestIntent:
    """Tests for Intent enum."""

    def test_all_intents_exist(self):
        """Verify all expected intents are defined."""
        expected = [
            "supplier_search",
            "supplier_comparison",
            "compliance_check",
            "technical_question",
            "risk_assessment",
            "clarification",
            "greeting",
            "unknown",
        ]
        for intent_value in expected:
            assert Intent(intent_value) is not None

    def test_default_intent_is_unknown(self):
        """Verify default intent is UNKNOWN."""
        state = ChatState()
        assert state.intent == Intent.UNKNOWN


class TestSupplier:
    """Tests for Supplier model."""

    def test_create_minimal_supplier(self):
        """Create supplier with minimal required fields."""
        supplier = Supplier(id="SUP-001", name="Test Supplier")
        assert supplier.id == "SUP-001"
        assert supplier.name == "Test Supplier"
        assert supplier.capabilities == []
        assert supplier.certifications == []

    def test_create_full_supplier(self):
        """Create supplier with all fields."""
        cert = Certification(
            type="nadcap",
            scope="Heat Treating",
            status="active",
        )
        supplier = Supplier(
            id="SUP-002",
            name="Full Supplier",
            location="California, USA",
            capabilities=["heat_treatment", "ndt"],
            certifications=[cert],
            oem_approvals=["Boeing", "Airbus"],
            quality_rate=98.5,
            on_time_delivery=96.0,
            risk_score=0.15,
            contact_email="test@example.com",
        )
        assert supplier.location == "California, USA"
        assert len(supplier.capabilities) == 2
        assert len(supplier.certifications) == 1
        assert supplier.quality_rate == 98.5


class TestCertification:
    """Tests for Certification model."""

    def test_create_certification(self):
        """Create a certification."""
        cert = Certification(
            type="as9100",
            scope="Quality Management",
            status="active",
            auditor="SAI Global",
        )
        assert cert.type == "as9100"
        assert cert.status == "active"

    def test_certification_with_expiry(self):
        """Create certification with expiry date."""
        expiry = datetime(2025, 12, 31)
        cert = Certification(
            type="nadcap",
            scope="NDT",
            expiry_date=expiry,
        )
        assert cert.expiry_date == expiry


class TestComplianceInfo:
    """Tests for ComplianceInfo model."""

    def test_compliant_supplier(self):
        """Test compliant supplier info."""
        info = ComplianceInfo(
            supplier_id="SUP-001",
            is_compliant=True,
            certifications_valid=["nadcap", "as9100"],
            itar_cleared=True,
        )
        assert info.is_compliant
        assert len(info.certifications_valid) == 2
        assert info.itar_cleared

    def test_non_compliant_supplier(self):
        """Test non-compliant supplier info."""
        info = ComplianceInfo(
            supplier_id="SUP-002",
            is_compliant=False,
            certifications_missing=["itar"],
            certifications_expiring=["nadcap"],
        )
        assert not info.is_compliant
        assert "itar" in info.certifications_missing


class TestRiskScore:
    """Tests for RiskScore model."""

    def test_low_risk_score(self):
        """Test low risk score."""
        risk = RiskScore(
            supplier_id="SUP-001",
            overall_score=0.15,
            categories={
                "compliance": 0.1,
                "quality": 0.1,
                "financial": 0.2,
            },
        )
        assert risk.overall_score < 0.2
        assert len(risk.categories) == 3

    def test_high_risk_with_alerts(self):
        """Test high risk score with alerts."""
        risk = RiskScore(
            supplier_id="SUP-002",
            overall_score=0.75,
            categories={"compliance": 0.9},
            alerts=["Missing required certifications"],
            mitigations=["Request certification update"],
        )
        assert risk.overall_score >= 0.6
        assert len(risk.alerts) == 1
        assert len(risk.mitigations) == 1


class TestHITLRequest:
    """Tests for HITLRequest model."""

    def test_create_hitl_request(self):
        """Create HITL request."""
        request = HITLRequest(
            request_type="itar_decision",
            priority="critical",
            context={"supplier_id": "SUP-001"},
            decision_options=[
                {"id": "approve", "label": "Approve"},
                {"id": "reject", "label": "Reject"},
            ],
        )
        assert request.request_type == "itar_decision"
        assert request.priority == "critical"
        assert len(request.decision_options) == 2

    def test_default_timeout(self):
        """Test default timeout is 24 hours."""
        request = HITLRequest(request_type="review")
        assert request.timeout_ms == 86400000


class TestAgentOutput:
    """Tests for AgentOutput model."""

    def test_successful_output(self):
        """Test successful agent output."""
        output = AgentOutput(
            agent_name="search",
            success=True,
            data={"results": 5},
            confidence=0.95,
            processing_time_ms=150,
        )
        assert output.success
        assert output.confidence == 0.95

    def test_failed_output(self):
        """Test failed agent output."""
        output = AgentOutput(
            agent_name="compliance",
            success=False,
            error="API timeout",
        )
        assert not output.success
        assert output.error == "API timeout"


class TestChatState:
    """Tests for ChatState model."""

    def test_create_empty_state(self):
        """Create empty state with defaults."""
        state = ChatState()
        assert state.session_id == ""
        assert state.intent == Intent.UNKNOWN
        assert state.messages == []
        assert state.guardrails_passed is True

    def test_state_with_session(self):
        """Create state with session info."""
        state = ChatState(
            session_id="sess-123",
            user_id="user-456",
            user_role="admin",
        )
        assert state.session_id == "sess-123"
        assert state.user_id == "user-456"
        assert state.user_role == "admin"

    def test_state_with_suppliers(self):
        """Create state with suppliers."""
        suppliers = [
            Supplier(id="SUP-001", name="Supplier 1"),
            Supplier(id="SUP-002", name="Supplier 2"),
        ]
        state = ChatState(suppliers=suppliers)
        assert len(state.suppliers) == 2

    def test_state_flags(self):
        """Test state flags."""
        state = ChatState(
            guardrails_passed=False,
            pii_detected=True,
            itar_flagged=True,
            requires_human_approval=True,
        )
        assert not state.guardrails_passed
        assert state.pii_detected
        assert state.itar_flagged
        assert state.requires_human_approval

    def test_state_agent_outputs(self):
        """Test adding agent outputs to state."""
        state = ChatState()
        state.agent_outputs["search"] = AgentOutput(
            agent_name="search",
            success=True,
            data={"count": 3},
        )
        assert "search" in state.agent_outputs
        assert state.agent_outputs["search"].success
