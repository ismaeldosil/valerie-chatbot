"""Tests for OracleIntegrationAgent HTTP methods."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from valerie.agents.oracle_integration import OracleIntegrationAgent
from valerie.models import ChatState, Settings, Supplier


class TestOracleIntegrationInit:
    """Tests for OracleIntegrationAgent initialization."""

    def test_init_defaults(self):
        agent = OracleIntegrationAgent()
        assert agent.name == "oracle_integration"
        assert agent._client is None
        assert agent._token is None
        assert agent._token_expires is None

    def test_init_with_settings(self):
        settings = Settings(oracle_base_url="http://test-oracle:3000")
        agent = OracleIntegrationAgent(settings=settings)
        assert agent.settings.oracle_base_url == "http://test-oracle:3000"


class TestOracleIntegrationGetClient:
    """Tests for _get_client method."""

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self):
        agent = OracleIntegrationAgent()

        oracle_http = "valerie.agents.oracle_integration.httpx"
        with patch(f"{oracle_http}.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            client = await agent._get_client()

            mock_client_class.assert_called_once_with(
                base_url=agent.settings.oracle_base_url,
                timeout=30.0,
            )
            assert client == mock_client
            assert agent._client == mock_client

    @pytest.mark.asyncio
    async def test_get_client_returns_existing_client(self):
        agent = OracleIntegrationAgent()
        existing_client = AsyncMock()
        agent._client = existing_client

        client = await agent._get_client()
        assert client == existing_client


class TestOracleIntegrationEnsureToken:
    """Tests for _ensure_token method."""

    @pytest.mark.asyncio
    async def test_ensure_token_returns_existing_valid_token(self):
        agent = OracleIntegrationAgent()
        agent._token = "existing-token"
        agent._token_expires = datetime.now() + timedelta(minutes=30)

        # Should not make any HTTP calls
        await agent._ensure_token()
        assert agent._token == "existing-token"

    @pytest.mark.asyncio
    async def test_ensure_token_fetches_new_token_when_none(self):
        agent = OracleIntegrationAgent()
        agent._token = None

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new-token"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(agent, "_get_client", return_value=mock_client):
            await agent._ensure_token()

            mock_client.post.assert_called_once_with(
                "/oauth2/v1/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": agent.settings.oracle_client_id,
                    "client_secret": agent.settings.oracle_client_secret,
                },
            )
            assert agent._token == "new-token"
            assert agent._token_expires is not None

    @pytest.mark.asyncio
    async def test_ensure_token_fetches_new_token_when_expired(self):
        agent = OracleIntegrationAgent()
        agent._token = "old-token"
        agent._token_expires = datetime.now() - timedelta(minutes=5)

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "refreshed-token"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(agent, "_get_client", return_value=mock_client):
            await agent._ensure_token()
            assert agent._token == "refreshed-token"


class TestOracleIntegrationFetchSuppliers:
    """Tests for _fetch_suppliers method."""

    @pytest.mark.asyncio
    async def test_fetch_suppliers_success(self):
        agent = OracleIntegrationAgent()
        agent._token = "test-token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"supplier_id": "SUP-001", "name": "Test"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent._fetch_suppliers(["SUP-001"])

            mock_client.get.assert_called_once_with(
                "/fscmRestApi/resources/11.13.18.05/suppliers/SUP-001",
                headers={"Authorization": "Bearer test-token"},
            )
            assert len(result) == 1
            assert result[0]["supplier_id"] == "SUP-001"

    @pytest.mark.asyncio
    async def test_fetch_suppliers_multiple(self):
        agent = OracleIntegrationAgent()
        agent._token = "test-token"

        mock_client = AsyncMock()
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {"id": "SUP-001"}

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {"id": "SUP-002"}

        mock_client.get.side_effect = [mock_response_1, mock_response_2]

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent._fetch_suppliers(["SUP-001", "SUP-002"])
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_fetch_suppliers_not_found(self):
        agent = OracleIntegrationAgent()
        agent._token = "test-token"

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent._fetch_suppliers(["SUP-MISSING"])
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_suppliers_http_error(self):
        agent = OracleIntegrationAgent()
        agent._token = "test-token"

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent._fetch_suppliers(["SUP-001"])
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_suppliers_partial_failure(self):
        agent = OracleIntegrationAgent()
        agent._token = "test-token"

        mock_client = AsyncMock()

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {"id": "SUP-001"}

        # First succeeds, second raises error
        mock_client.get.side_effect = [
            mock_response_ok,
            httpx.HTTPError("Failed"),
        ]

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent._fetch_suppliers(["SUP-001", "SUP-002"])
            assert len(result) == 1


class TestOracleIntegrationClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_with_client(self):
        agent = OracleIntegrationAgent()
        mock_client = AsyncMock()
        agent._client = mock_client

        await agent.close()

        mock_client.aclose.assert_called_once()
        assert agent._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        agent = OracleIntegrationAgent()
        agent._client = None

        # Should not raise
        await agent.close()
        assert agent._client is None


class TestOracleIntegrationProcess:
    """Extended tests for process method."""

    @pytest.fixture
    def agent(self):
        return OracleIntegrationAgent()

    @pytest.mark.asyncio
    async def test_process_with_supplier_ids_success(self, agent):
        state = ChatState()
        state.suppliers = [
            Supplier(id="SUP-001", name="Test Supplier 1"),
            Supplier(id="SUP-002", name="Test Supplier 2"),
        ]

        oracle_data = [
            {"supplier_id": "SUP-001", "rating": "A"},
            {"supplier_id": "SUP-002", "rating": "B"},
        ]

        with (
            patch.object(agent, "_ensure_token", new_callable=AsyncMock),
            patch.object(agent, "_fetch_suppliers", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_fetch.return_value = oracle_data
            result = await agent.process(state)

            mock_fetch.assert_called_once_with(["SUP-001", "SUP-002"])
            assert result.agent_outputs["oracle_integration"].success
            assert result.agent_outputs["oracle_integration"].data["fetched_count"] == 2
            assert result.agent_outputs["oracle_integration"].data["oracle_data"] == oracle_data

    @pytest.mark.asyncio
    async def test_process_token_error(self, agent):
        state = ChatState()
        state.suppliers = [Supplier(id="SUP-001", name="Test")]

        with patch.object(agent, "_ensure_token", new_callable=AsyncMock) as mock_token:
            mock_token.side_effect = httpx.HTTPError("Auth failed")
            result = await agent.process(state)

            assert not result.agent_outputs["oracle_integration"].success
            assert "Auth failed" in result.agent_outputs["oracle_integration"].error

    @pytest.mark.asyncio
    async def test_process_fetch_error(self, agent):
        state = ChatState()
        state.suppliers = [Supplier(id="SUP-001", name="Test")]

        with (
            patch.object(agent, "_ensure_token", new_callable=AsyncMock),
            patch.object(agent, "_fetch_suppliers", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_fetch.side_effect = Exception("Fetch failed")
            result = await agent.process(state)

            assert not result.agent_outputs["oracle_integration"].success
            assert "Fetch failed" in result.agent_outputs["oracle_integration"].error

    @pytest.mark.asyncio
    async def test_process_records_processing_time(self, agent):
        state = ChatState()

        with patch.object(agent, "_ensure_token", new_callable=AsyncMock):
            result = await agent.process(state)
            output = result.agent_outputs["oracle_integration"]
            assert output.processing_time_ms >= 0
