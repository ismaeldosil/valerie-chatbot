"""Oracle Fusion Integration agent - interfaces with Oracle Fusion Cloud."""

from datetime import datetime

import httpx

from ..models import ChatState, Settings
from .base import BaseAgent


class OracleIntegrationAgent(BaseAgent):
    """Handles all interactions with Oracle Fusion Cloud APIs."""

    name = "oracle_integration"

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings)
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._token_expires: datetime | None = None

    def get_system_prompt(self) -> str:
        return """You are an Oracle Fusion Integration Agent.

Your role is to:
1. Authenticate with Oracle Fusion Cloud
2. Fetch supplier data from Oracle APIs
3. Handle pagination and rate limiting
4. Transform Oracle responses to internal format
5. Cache responses appropriately

Supported Oracle APIs:
- /fscmRestApi/resources/11.13.18.05/suppliers
- /fscmRestApi/resources/11.13.18.05/purchaseOrders
- /fscmRestApi/resources/11.13.18.05/purchaseRequisitions
- /fscmRestApi/resources/11.13.18.05/purchaseAgreements

Implement circuit breaker for resilience."""

    async def process(self, state: ChatState) -> ChatState:
        """Fetch data from Oracle Fusion based on state needs."""
        start_time = datetime.now()

        try:
            # Ensure we have a valid token
            await self._ensure_token()

            # Fetch supplier data if we have supplier IDs
            supplier_ids = [s.id for s in state.suppliers]
            if supplier_ids:
                oracle_data = await self._fetch_suppliers(supplier_ids)
                state.agent_outputs[self.name] = self.create_output(
                    success=True,
                    data={"oracle_data": oracle_data, "fetched_count": len(oracle_data)},
                    start_time=start_time,
                )
            else:
                state.agent_outputs[self.name] = self.create_output(
                    success=True,
                    data={"message": "No supplier IDs to fetch"},
                    start_time=start_time,
                )

        except Exception as e:
            state.agent_outputs[self.name] = self.create_output(
                success=False,
                error=f"Oracle integration error: {str(e)}",
                start_time=start_time,
            )

        return state

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.settings.oracle_base_url,
                timeout=30.0,
            )
        return self._client

    async def _ensure_token(self) -> None:
        """Ensure we have a valid OAuth token."""
        now = datetime.now()
        if self._token and self._token_expires and self._token_expires > now:
            return

        client = await self._get_client()
        response = await client.post(
            "/oauth2/v1/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.oracle_client_id,
                "client_secret": self.settings.oracle_client_secret,
            },
        )
        response.raise_for_status()

        data = response.json()
        self._token = data.get("access_token")
        # Token expires in 1 hour, refresh 5 minutes early
        from datetime import timedelta

        self._token_expires = now + timedelta(minutes=55)

    async def _fetch_suppliers(self, supplier_ids: list[str]) -> list[dict]:
        """Fetch supplier data from Oracle."""
        client = await self._get_client()
        results = []

        for supplier_id in supplier_ids:
            try:
                response = await client.get(
                    f"/fscmRestApi/resources/11.13.18.05/suppliers/{supplier_id}",
                    headers={"Authorization": f"Bearer {self._token}"},
                )
                if response.status_code == 200:
                    results.append(response.json())
            except httpx.HTTPError:
                # Skip failed fetches, log in production
                pass

        return results

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
