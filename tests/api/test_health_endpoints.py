"""Tests for health check endpoints."""


class TestHealthEndpoints:
    """Tests for /health, /ready, /live endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Valerie Supplier Chatbot API"
        assert "version" in data
        assert data["status"] == "running"

    def test_health_endpoint(self, client):
        """Test /health returns system health."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data
        assert isinstance(data["services"], list)

    def test_health_includes_langgraph_service(self, client):
        """Test health check includes LangGraph service status."""
        response = client.get("/health")
        data = response.json()

        service_names = [s["name"] for s in data["services"]]
        assert "langgraph" in service_names

    def test_ready_endpoint(self, client):
        """Test /ready returns readiness status."""
        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_ready_includes_graph_check(self, client):
        """Test readiness includes graph compilation check."""
        response = client.get("/ready")
        data = response.json()

        assert "graph" in data["checks"]
        assert "config" in data["checks"]

    def test_live_endpoint(self, client):
        """Test /live returns liveness status."""
        response = client.get("/live")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_docs_endpoint(self, client):
        """Test /docs returns Swagger UI."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_endpoint(self, client):
        """Test /openapi.json returns OpenAPI spec."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "info" in data
