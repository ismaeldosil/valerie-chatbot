"""Tests for agent modules."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from valerie.agents.comparison import ComparisonAgent
from valerie.agents.compliance import ComplianceAgent
from valerie.agents.intent_classifier import IntentClassifierAgent
from valerie.agents.memory_context import MemoryContextAgent
from valerie.agents.oracle_integration import OracleIntegrationAgent
from valerie.agents.orchestrator import OrchestratorAgent
from valerie.agents.process_expertise import ProcessExpertiseAgent
from valerie.agents.response_generation import ResponseGenerationAgent
from valerie.agents.risk_assessment import RiskAssessmentAgent
from valerie.agents.supplier_search import SupplierSearchAgent
from valerie.models import (
    AgentOutput,
    Certification,
    ChatState,
    ComplianceInfo,
    Intent,
    Supplier,
)


class TestIntentClassifierAgent:
    """Tests for IntentClassifierAgent."""

    @pytest.fixture
    def agent(self):
        return IntentClassifierAgent()

    def test_agent_name(self, agent):
        assert agent.name == "intent_classifier"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Intent Classifier" in prompt
        assert "supplier_search" in prompt

    @pytest.mark.asyncio
    async def test_process_no_message(self, agent):
        """Test processing with no user message."""
        state = ChatState()
        result = await agent.process(state)
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_process_valid_intent(self, agent):
        """Test processing with valid LLM response."""
        state = ChatState()
        state.messages = [HumanMessage(content="Find heat treatment suppliers")]

        mock_response = json.dumps(
            {
                "intent": "supplier_search",
                "confidence": 0.95,
                "entities": {"processes": ["heat_treatment"]},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.SUPPLIER_SEARCH
            assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_process_invalid_json(self, agent):
        """Test processing with invalid JSON response falls back to pattern matching."""
        state = ChatState()
        # Use a message that doesn't match any pattern
        state.messages = [HumanMessage(content="xyzabc123 random gibberish")]

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "not valid json"
            result = await agent.process(state)
            # With invalid JSON and no pattern match, should fall back to UNKNOWN
            assert result.intent == Intent.UNKNOWN

    @pytest.mark.asyncio
    async def test_process_unknown_intent(self, agent):
        """Test processing with unknown intent value falls back to pattern matching."""
        state = ChatState()
        # Use a message that doesn't match any pattern
        state.messages = [HumanMessage(content="xyzabc123 random gibberish")]

        mock_response = json.dumps(
            {
                "intent": "nonexistent_intent",
                "confidence": 0.5,
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            # With unknown intent and no pattern match, should fall back to UNKNOWN
            assert result.intent == Intent.UNKNOWN

    @pytest.mark.asyncio
    async def test_process_product_search_intent(self, agent):
        """Test processing product search intent with pattern matching."""
        state = ChatState()
        state.messages = [HumanMessage(content="Quien vende acetona?")]

        mock_response = json.dumps(
            {
                "intent": "product_search",
                "confidence": 0.90,
                "entities": {"products_mentioned": ["acetona"]},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.PRODUCT_SEARCH

    @pytest.mark.asyncio
    async def test_process_category_browse_intent(self, agent):
        """Test processing category browse intent."""
        state = ChatState()
        state.messages = [HumanMessage(content="Que categorias de quimicos hay?")]

        mock_response = json.dumps(
            {
                "intent": "category_browse",
                "confidence": 0.92,
                "entities": {"categories_mentioned": ["quimicos"]},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.CATEGORY_BROWSE

    @pytest.mark.asyncio
    async def test_process_price_inquiry_intent(self, agent):
        """Test processing price inquiry intent."""
        state = ChatState()
        state.messages = [HumanMessage(content="Cuanto cuesta el alcohol isopropilico?")]

        mock_response = json.dumps(
            {
                "intent": "price_inquiry",
                "confidence": 0.95,
                "entities": {"products_mentioned": ["alcohol isopropilico"]},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.PRICE_INQUIRY

    @pytest.mark.asyncio
    async def test_process_supplier_detail_intent(self, agent):
        """Test processing supplier detail intent."""
        state = ChatState()
        state.messages = [HumanMessage(content="Dame info de Grainger")]

        mock_response = json.dumps(
            {
                "intent": "supplier_detail",
                "confidence": 0.93,
                "entities": {"suppliers_mentioned": ["Grainger"]},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.SUPPLIER_DETAIL

    @pytest.mark.asyncio
    async def test_process_top_suppliers_intent(self, agent):
        """Test processing top suppliers intent."""
        state = ChatState()
        state.messages = [HumanMessage(content="Top 10 suppliers por volumen")]

        mock_response = json.dumps(
            {
                "intent": "top_suppliers",
                "confidence": 0.91,
                "entities": {},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.TOP_SUPPLIERS

    @pytest.mark.asyncio
    async def test_process_item_comparison_intent(self, agent):
        """Test processing item comparison intent."""
        state = ChatState()
        state.messages = [HumanMessage(content="Compara precios de guantes de nitrilo")]

        mock_response = json.dumps(
            {
                "intent": "item_comparison",
                "confidence": 0.94,
                "entities": {"products_mentioned": ["guantes de nitrilo"]},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            assert result.intent == Intent.ITEM_COMPARISON

    @pytest.mark.asyncio
    async def test_pattern_matching_fallback(self, agent):
        """Test that pattern matching is used when LLM returns unknown."""
        state = ChatState()
        state.messages = [HumanMessage(content="Quien vende guantes?")]

        # LLM returns unknown but pattern matching should detect product_search
        mock_response = json.dumps(
            {
                "intent": "unknown",
                "confidence": 0.3,
                "entities": {},
            }
        )

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await agent.process(state)
            # Pattern matching should override with product_search
            assert result.intent == Intent.PRODUCT_SEARCH

    @pytest.mark.asyncio
    async def test_pattern_matching_on_llm_failure(self, agent):
        """Test that pattern matching is used when LLM fails."""
        state = ChatState()
        state.messages = [HumanMessage(content="Cuanto cuesta la acetona?")]

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "invalid json response"
            result = await agent.process(state)
            # Pattern matching should provide fallback
            assert result.intent == Intent.PRICE_INQUIRY

    def test_detect_intent_by_pattern_product_search(self, agent):
        """Test pattern detection for product search."""
        intent, confidence = agent._detect_intent_by_pattern("Busco proveedores de acetona")
        assert intent == Intent.PRODUCT_SEARCH
        assert confidence > 0

    def test_detect_intent_by_pattern_category_browse(self, agent):
        """Test pattern detection for category browse."""
        intent, confidence = agent._detect_intent_by_pattern("Que categorias tienen disponibles?")
        assert intent == Intent.CATEGORY_BROWSE
        assert confidence > 0

    def test_detect_intent_by_pattern_price_inquiry(self, agent):
        """Test pattern detection for price inquiry."""
        intent, confidence = agent._detect_intent_by_pattern("Cual es el precio de los guantes?")
        assert intent == Intent.PRICE_INQUIRY
        assert confidence > 0

    def test_detect_intent_by_pattern_top_suppliers(self, agent):
        """Test pattern detection for top suppliers."""
        intent, confidence = agent._detect_intent_by_pattern("Dame el ranking de proveedores")
        assert intent == Intent.TOP_SUPPLIERS
        assert confidence > 0

    def test_detect_intent_by_pattern_no_match(self, agent):
        """Test pattern detection with no match."""
        intent, confidence = agent._detect_intent_by_pattern("Random message without patterns")
        assert intent is None
        assert confidence == 0.0


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent."""

    @pytest.fixture
    def agent(self):
        return OrchestratorAgent()

    def test_agent_name(self, agent):
        assert agent.name == "orchestrator"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Orchestrator" in prompt

    @pytest.mark.asyncio
    async def test_process_supplier_search(self, agent):
        """Test routing for supplier search."""
        state = ChatState()
        state.intent = Intent.SUPPLIER_SEARCH
        result = await agent.process(state)
        assert result.agent_outputs["orchestrator"].success
        assert "search" in result.agent_outputs["orchestrator"].data["route"]

    @pytest.mark.asyncio
    async def test_process_comparison(self, agent):
        """Test routing for comparison."""
        state = ChatState()
        state.intent = Intent.SUPPLIER_COMPARISON
        result = await agent.process(state)
        route = result.agent_outputs["orchestrator"].data["route"]
        assert "comparison" in route

    @pytest.mark.asyncio
    async def test_process_technical_question(self, agent):
        """Test routing for technical question."""
        state = ChatState()
        state.intent = Intent.TECHNICAL_QUESTION
        result = await agent.process(state)
        route = result.agent_outputs["orchestrator"].data["route"]
        assert "process_expertise" in route

    @pytest.mark.asyncio
    async def test_process_greeting(self, agent):
        """Test routing for greeting."""
        state = ChatState()
        state.intent = Intent.GREETING
        result = await agent.process(state)
        route = result.agent_outputs["orchestrator"].data["route"]
        assert "response" in route

    def test_get_next_agent_no_output(self, agent):
        """Test get_next_agent with no output."""
        state = ChatState()
        result = agent.get_next_agent(state)
        assert result == "error_handler"

    def test_get_next_agent_failed_output(self, agent):
        """Test get_next_agent with failed output."""
        state = ChatState()
        state.agent_outputs["orchestrator"] = AgentOutput(agent_name="orchestrator", success=False)
        result = agent.get_next_agent(state)
        assert result == "error_handler"

    def test_get_next_agent_with_route(self, agent):
        """Test get_next_agent with valid route."""
        state = ChatState()
        state.agent_outputs["orchestrator"] = AgentOutput(
            agent_name="orchestrator",
            success=True,
            data={"route": ["search", "compliance", "response"]},
        )
        result = agent.get_next_agent(state)
        assert result == "search"

    def test_get_next_agent_all_completed(self, agent):
        """Test get_next_agent when all agents completed."""
        state = ChatState()
        state.agent_outputs["orchestrator"] = AgentOutput(
            agent_name="orchestrator",
            success=True,
            data={"route": ["search"]},
        )
        state.agent_outputs["search"] = AgentOutput(agent_name="search", success=True)
        result = agent.get_next_agent(state)
        assert result == "response"


class TestMemoryContextAgent:
    """Tests for MemoryContextAgent."""

    @pytest.fixture
    def agent(self):
        return MemoryContextAgent()

    def test_agent_name(self, agent):
        assert agent.name == "memory_context"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Memory" in prompt or "Context" in prompt

    @pytest.mark.asyncio
    async def test_process_no_messages(self, agent):
        """Test processing with no messages."""
        state = ChatState()
        result = await agent.process(state)
        assert result.agent_outputs["memory_context"].success

    @pytest.mark.asyncio
    async def test_process_with_context(self, agent):
        """Test processing with existing context."""
        state = ChatState()
        state.messages = [
            HumanMessage(content="Find supplier ABC"),
            AIMessage(content="Found supplier ABC"),
            HumanMessage(content="Tell me more about it"),
        ]
        result = await agent.process(state)
        assert "memory_context" in result.agent_outputs


class TestProcessExpertiseAgent:
    """Tests for ProcessExpertiseAgent."""

    @pytest.fixture
    def agent(self):
        return ProcessExpertiseAgent()

    def test_agent_name(self, agent):
        assert agent.name == "process_expertise"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Heat Treatment" in prompt or "SME" in prompt

    @pytest.mark.asyncio
    async def test_process_no_question(self, agent):
        """Test processing with no question."""
        state = ChatState()
        result = await agent.process(state)
        assert not result.agent_outputs["process_expertise"].success

    @pytest.mark.asyncio
    async def test_process_with_question(self, agent):
        """Test processing with a question."""
        state = ChatState()
        state.messages = [HumanMessage(content="What is heat treatment?")]
        state.entities = {"processes": ["heat_treatment"]}

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Heat treatment is a process..."
            result = await agent.process(state)
            assert result.agent_outputs["process_expertise"].success

    @pytest.mark.asyncio
    async def test_process_llm_error(self, agent):
        """Test processing with LLM error."""
        state = ChatState()
        state.messages = [HumanMessage(content="What is heat treatment?")]

        with patch.object(agent, "invoke_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM error")
            result = await agent.process(state)
            assert not result.agent_outputs["process_expertise"].success


class TestOracleIntegrationAgent:
    """Tests for OracleIntegrationAgent."""

    @pytest.fixture
    def agent(self):
        return OracleIntegrationAgent()

    def test_agent_name(self, agent):
        assert agent.name == "oracle_integration"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Oracle" in prompt

    @pytest.mark.asyncio
    async def test_process_no_suppliers(self, agent):
        """Test processing with no suppliers."""
        state = ChatState()
        with patch.object(agent, "_ensure_token", new_callable=AsyncMock):
            result = await agent.process(state)
            assert result.agent_outputs["oracle_integration"].success
            data = result.agent_outputs["oracle_integration"].data
            assert data["message"] == "No supplier IDs to fetch"

    @pytest.mark.asyncio
    async def test_process_with_suppliers(self, agent):
        """Test processing with suppliers."""
        state = ChatState()
        state.suppliers = [Supplier(id="SUP-001", name="Test Supplier")]
        with (
            patch.object(agent, "_ensure_token", new_callable=AsyncMock),
            patch.object(agent, "_fetch_suppliers", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_fetch.return_value = [{"supplier_id": "SUP-001", "name": "Test"}]
            result = await agent.process(state)
            assert result.agent_outputs["oracle_integration"].success
            assert result.agent_outputs["oracle_integration"].data["fetched_count"] == 1

    @pytest.mark.asyncio
    async def test_process_error(self, agent):
        """Test processing with error."""
        state = ChatState()
        with patch.object(agent, "_ensure_token", new_callable=AsyncMock) as mock_token:
            mock_token.side_effect = Exception("Token error")
            result = await agent.process(state)
            assert not result.agent_outputs["oracle_integration"].success
            assert "error" in result.agent_outputs["oracle_integration"].error.lower()


class TestRiskAssessmentAgent:
    """Tests for RiskAssessmentAgent."""

    @pytest.fixture
    def agent(self):
        return RiskAssessmentAgent()

    def test_agent_name(self, agent):
        assert agent.name == "risk_assessment"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Risk" in prompt

    @pytest.mark.asyncio
    async def test_process_no_suppliers(self, agent):
        """Test processing with no suppliers."""
        state = ChatState()
        result = await agent.process(state)
        assert result.agent_outputs["risk_assessment"].success

    @pytest.mark.asyncio
    async def test_process_with_suppliers(self, agent):
        """Test processing with suppliers."""
        state = ChatState()
        state.suppliers = [
            Supplier(
                id="SUP-001",
                name="Test",
                quality_rate=95.0,
                on_time_delivery=90.0,
                risk_score=0.2,
            )
        ]
        result = await agent.process(state)
        assert result.agent_outputs["risk_assessment"].success
        assert len(result.risk_results) > 0


class TestComparisonAgent:
    """Tests for ComparisonAgent."""

    @pytest.fixture
    def agent(self):
        return ComparisonAgent()

    def test_agent_name(self, agent):
        assert agent.name == "comparison"

    @pytest.mark.asyncio
    async def test_process_insufficient_suppliers(self, agent):
        """Test processing with less than 2 suppliers."""
        state = ChatState()
        state.suppliers = [Supplier(id="SUP-001", name="Test")]
        result = await agent.process(state)
        assert not result.agent_outputs["comparison"].success

    @pytest.mark.asyncio
    async def test_process_two_suppliers(self, agent):
        """Test processing with two suppliers."""
        state = ChatState()
        state.suppliers = [
            Supplier(id="SUP-001", name="Supplier A", quality_rate=95.0),
            Supplier(id="SUP-002", name="Supplier B", quality_rate=90.0),
        ]
        state.compliance_results = [
            ComplianceInfo(supplier_id="SUP-001", is_compliant=True),
            ComplianceInfo(supplier_id="SUP-002", is_compliant=False),
        ]
        result = await agent.process(state)
        assert result.agent_outputs["comparison"].success
        assert result.comparison_data is not None


class TestResponseGenerationAgent:
    """Tests for ResponseGenerationAgent."""

    @pytest.fixture
    def agent(self):
        return ResponseGenerationAgent()

    def test_agent_name(self, agent):
        assert agent.name == "response_generation"

    @pytest.mark.asyncio
    async def test_process_error_response(self, agent):
        """Test generating error response."""
        state = ChatState()
        state.error = "Something went wrong"
        result = await agent.process(state)
        assert result.response_type == "error"
        assert "Something went wrong" in result.final_response

    @pytest.mark.asyncio
    async def test_process_comparison_response(self, agent):
        """Test generating comparison response."""
        state = ChatState()
        state.comparison_data = {
            "suppliers": [
                {"name": "A", "scores": {"quality": 95}},
                {"name": "B", "scores": {"quality": 90}},
            ],
            "recommendation": {"supplier_name": "A", "rationale": "Best overall"},
        }
        result = await agent.process(state)
        assert result.response_type == "comparison"

    @pytest.mark.asyncio
    async def test_process_supplier_response(self, agent):
        """Test generating supplier response."""
        state = ChatState()
        state.suppliers = [Supplier(id="SUP-001", name="Test", capabilities=["heat"])]
        result = await agent.process(state)
        assert result.response_type == "table"
        assert "Test" in result.final_response

    @pytest.mark.asyncio
    async def test_process_technical_response(self, agent):
        """Test generating technical response."""
        state = ChatState()
        state.technical_answer = "Heat treatment is..."
        result = await agent.process(state)
        assert result.response_type == "text"

    @pytest.mark.asyncio
    async def test_process_greeting_response(self, agent):
        """Test generating greeting response."""
        state = ChatState()
        state.intent = Intent.GREETING
        result = await agent.process(state)
        assert "Hello" in result.final_response

    @pytest.mark.asyncio
    async def test_process_unknown_response(self, agent):
        """Test generating unknown intent response."""
        state = ChatState()
        state.intent = Intent.UNKNOWN
        result = await agent.process(state)
        assert "not sure" in result.final_response.lower()

    @pytest.mark.asyncio
    async def test_process_no_suppliers_found(self, agent):
        """Test response when no suppliers found."""
        state = ChatState()
        state.suppliers = []
        state.intent = Intent.SUPPLIER_SEARCH
        # Force supplier response path by setting intent
        result = await agent.process(state)
        # Should generate generic response since no suppliers
        assert result is not None


class TestSupplierSearchAgent:
    """Tests for SupplierSearchAgent."""

    @pytest.fixture
    def agent(self, mock_data_source):
        return SupplierSearchAgent(data_source=mock_data_source)

    def test_agent_name(self, agent):
        assert agent.name == "supplier_search"

    def test_system_prompt(self, agent):
        prompt = agent.get_system_prompt()
        assert "Supplier" in prompt or "Search" in prompt

    @pytest.mark.asyncio
    async def test_process_with_criteria(self, agent):
        """Test processing with search criteria."""
        state = ChatState()
        state.entities = {"processes": ["heat_treatment"]}
        result = await agent.process(state)
        assert result.agent_outputs["supplier_search"].success
        assert "results_count" in result.agent_outputs["supplier_search"].data

    @pytest.mark.asyncio
    async def test_process_returns_suppliers(self, agent):
        """Test that search returns suppliers from data source."""
        state = ChatState()
        state.entities = {}  # No filter criteria - should return all
        result = await agent.process(state)
        assert result.agent_outputs["supplier_search"].success
        # MockDataSource returns 5 suppliers by default
        assert len(result.suppliers) > 0

    @pytest.mark.asyncio
    async def test_process_no_results_graceful(self, agent):
        """Test graceful handling when no results found."""
        state = ChatState()
        # Use a name filter that won't match any mock suppliers
        state.entities = {"location": "NonexistentLocation12345"}
        result = await agent.process(state)
        # Should still succeed, just with empty results
        assert result.agent_outputs["supplier_search"].success
        assert result.agent_outputs["supplier_search"].data["results_count"] >= 0

    @pytest.mark.asyncio
    async def test_process_with_name_search(self, agent):
        """Test processing with name-based search."""
        state = ChatState()
        state.entities = {"location": "Grainger"}  # Location used as name search
        result = await agent.process(state)
        assert result.agent_outputs["supplier_search"].success

    @pytest.mark.asyncio
    async def test_data_source_injection(self, mock_data_source):
        """Test that data source can be injected."""
        agent = SupplierSearchAgent(data_source=mock_data_source)
        assert agent._data_source is mock_data_source
        assert agent.data_source is mock_data_source


class TestComplianceAgent:
    """Tests for ComplianceAgent."""

    @pytest.fixture
    def agent(self):
        return ComplianceAgent()

    def test_agent_name(self, agent):
        assert agent.name == "compliance"

    @pytest.mark.asyncio
    async def test_process_with_itar(self, agent):
        """Test processing with ITAR requirement."""
        state = ChatState()
        state.entities = {"certifications": ["itar"]}
        state.suppliers = [
            Supplier(
                id="SUP-001",
                name="Test",
                certifications=[Certification(type="itar", name="ITAR", status="active")],
            )
        ]
        result = await agent.process(state)
        assert result.itar_flagged
        assert result.requires_human_approval
