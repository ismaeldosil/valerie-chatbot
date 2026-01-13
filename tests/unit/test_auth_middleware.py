"""Unit tests for JWT authentication middleware."""

from datetime import datetime, timedelta

import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from valerie.middleware import JWTAuthMiddleware


@pytest.fixture
def jwt_secret():
    """Secret key for testing."""
    return "test-secret-key-123"


@pytest.fixture
def test_app():
    """Create a minimal FastAPI app for testing."""
    app = FastAPI()

    @app.get("/public/health")
    async def health():
        return {"status": "ok"}

    @app.get("/protected/data")
    async def protected_data(request: Request):
        return {
            "tenant_id": request.state.tenant_id,
            "user_roles": request.state.user_roles,
            "auth_enabled": request.state.auth_enabled,
        }

    @app.get("/claims")
    async def get_claims(request: Request):
        return {
            "tenant_id": request.state.tenant_id,
            "user_roles": request.state.user_roles,
            "jwt_claims": request.state.jwt_claims,
        }

    return app


@pytest.fixture
def create_token(jwt_secret):
    """Factory fixture to create JWT tokens."""

    def _create_token(
        tenant_id="test-tenant",
        user_roles=None,
        extra_claims=None,
        expires_delta=None,
        algorithm="HS256",
    ):
        if user_roles is None:
            user_roles = ["user", "admin"]

        claims = {
            "tenant_id": tenant_id,
            "user_roles": user_roles,
            "sub": "user@example.com",
            "iat": datetime.utcnow(),
        }

        if expires_delta is not None:
            claims["exp"] = datetime.utcnow() + expires_delta

        if extra_claims:
            claims.update(extra_claims)

        return jwt.encode(claims, jwt_secret, algorithm=algorithm)

    return _create_token


class TestJWTAuthMiddlewareInit:
    """Test middleware initialization and configuration."""

    def test_init_with_auth_disabled(self, test_app, monkeypatch):
        """Test middleware initialization with auth disabled."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "false")
        monkeypatch.delenv("VALERIE_JWT_SECRET", raising=False)

        middleware = JWTAuthMiddleware(test_app)

        assert middleware.auth_enabled is False
        assert middleware.jwt_algorithm == "HS256"
        assert "/health" in middleware.exclude_paths
        assert "/docs" in middleware.exclude_paths

    def test_init_with_auth_enabled_and_secret(self, test_app, monkeypatch, jwt_secret):
        """Test middleware initialization with auth enabled and secret provided."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)

        middleware = JWTAuthMiddleware(test_app)

        assert middleware.auth_enabled is True
        assert middleware.jwt_secret == jwt_secret

    def test_init_with_auth_enabled_no_secret(self, test_app, monkeypatch):
        """Test middleware initialization fails when auth enabled without secret."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.delenv("VALERIE_JWT_SECRET", raising=False)

        with pytest.raises(ValueError, match="VALERIE_JWT_SECRET is required"):
            JWTAuthMiddleware(test_app)

    def test_custom_algorithm(self, test_app, monkeypatch, jwt_secret):
        """Test middleware with custom JWT algorithm."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)
        monkeypatch.setenv("VALERIE_JWT_ALGORITHM", "HS512")

        middleware = JWTAuthMiddleware(test_app)

        assert middleware.jwt_algorithm == "HS512"

    def test_custom_exclude_paths(self, test_app, monkeypatch, jwt_secret):
        """Test middleware with custom exclude paths."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)
        monkeypatch.setenv("VALERIE_AUTH_EXCLUDE_PATHS", "/custom,/api/public")

        middleware = JWTAuthMiddleware(test_app)

        assert "/custom" in middleware.exclude_paths
        assert "/api/public" in middleware.exclude_paths
        assert "/health" not in middleware.exclude_paths


class TestJWTAuthMiddlewareDisabled:
    """Test middleware behavior when authentication is disabled (demo mode)."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Setup environment for disabled auth tests."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "false")
        monkeypatch.delenv("VALERIE_JWT_SECRET", raising=False)

    def test_demo_mode_sets_default_claims(self, test_app):
        """Test that demo mode sets default claims in request.state."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "demo-tenant"
        assert data["user_roles"] == ["demo-user"]
        assert data["auth_enabled"] is False

    def test_demo_mode_no_auth_header_required(self, test_app):
        """Test that demo mode works without Authorization header."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data")

        assert response.status_code == 200

    def test_demo_mode_ignores_invalid_token(self, test_app):
        """Test that demo mode ignores invalid tokens."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data", headers={"Authorization": "Bearer invalid-token"})

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "demo-tenant"


class TestJWTAuthMiddlewareEnabled:
    """Test middleware behavior when authentication is enabled."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch, jwt_secret):
        """Setup environment for enabled auth tests."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)
        monkeypatch.setenv("VALERIE_JWT_ALGORITHM", "HS256")
        monkeypatch.setenv("VALERIE_AUTH_EXCLUDE_PATHS", "/health,/docs")

    def test_valid_token_allows_access(self, test_app, create_token):
        """Test that valid JWT token allows access to protected endpoint."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        token = create_token(
            tenant_id="tenant-123",
            user_roles=["admin", "user"],
            expires_delta=timedelta(hours=1),
        )

        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert data["user_roles"] == ["admin", "user"]
        assert data["auth_enabled"] is True

    def test_missing_auth_header_returns_401(self, test_app):
        """Test that missing Authorization header returns 401."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Unauthorized"
        assert "Missing Authorization header" in data["message"]

    def test_invalid_auth_header_format_returns_401(self, test_app):
        """Test that invalid Authorization header format returns 401."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Test without "Bearer" prefix
        response = client.get("/protected/data", headers={"Authorization": "token123"})
        assert response.status_code == 401

        # Test with wrong prefix
        response = client.get("/protected/data", headers={"Authorization": "Basic token123"})
        assert response.status_code == 401

    def test_expired_token_returns_401(self, test_app, create_token):
        """Test that expired JWT token returns 401."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Create token that expired 1 hour ago
        token = create_token(expires_delta=timedelta(hours=-1))

        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        data = response.json()
        assert "expired" in data["message"].lower()

    def test_invalid_signature_returns_401(self, test_app, create_token):
        """Test that token with invalid signature returns 401."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Create token with different secret
        token = jwt.encode(
            {"tenant_id": "test", "user_roles": ["user"]},
            "wrong-secret",
            algorithm="HS256",
        )

        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        data = response.json()
        assert "Invalid token" in data["message"]

    def test_malformed_token_returns_401(self, test_app):
        """Test that malformed JWT token returns 401."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get(
            "/protected/data", headers={"Authorization": "Bearer not-a-jwt-token"}
        )

        assert response.status_code == 401

    def test_missing_tenant_id_claim_returns_401(self, test_app, jwt_secret):
        """Test that token missing tenant_id claim returns 401."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Create token without tenant_id
        token = jwt.encode(
            {"user_roles": ["user"], "sub": "user@example.com"},
            jwt_secret,
            algorithm="HS256",
        )

        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        data = response.json()
        assert "tenant_id" in data["message"]

    def test_user_roles_defaults_to_empty_list(self, test_app, jwt_secret):
        """Test that missing user_roles claim defaults to empty list."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Create token without user_roles
        token = jwt.encode(
            {"tenant_id": "test-tenant", "sub": "user@example.com"},
            jwt_secret,
            algorithm="HS256",
        )

        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["user_roles"] == []

    def test_user_roles_as_string_converted_to_list(self, test_app, jwt_secret):
        """Test that user_roles as string is converted to list."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Create token with user_roles as string
        token = jwt.encode(
            {"tenant_id": "test-tenant", "user_roles": "admin", "sub": "user@example.com"},
            jwt_secret,
            algorithm="HS256",
        )

        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["user_roles"] == ["admin"]

    def test_all_jwt_claims_stored_in_state(self, test_app, create_token):
        """Test that all JWT claims are stored in request.state."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        token = create_token(
            tenant_id="tenant-123",
            user_roles=["admin"],
            extra_claims={"custom_claim": "custom_value", "organization": "Acme Corp"},
        )

        response = client.get("/claims", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["jwt_claims"]["tenant_id"] == "tenant-123"
        assert data["jwt_claims"]["custom_claim"] == "custom_value"
        assert data["jwt_claims"]["organization"] == "Acme Corp"


class TestExcludedPaths:
    """Test that excluded paths bypass authentication."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch, jwt_secret):
        """Setup environment for excluded paths tests."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)
        monkeypatch.setenv("VALERIE_AUTH_EXCLUDE_PATHS", "/health,/docs,/redoc")

    def test_excluded_paths_bypass_auth(self, test_app):
        """Test that excluded paths don't require authentication."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Note: /public/health is not in exclude list, but this tests the logic
        # In real scenario, you'd test with paths that exist and are excluded
        response = client.get("/health")
        # This will 404 since route doesn't exist, but wouldn't 401
        assert response.status_code == 404  # Not 401

    def test_non_excluded_paths_require_auth(self, test_app):
        """Test that non-excluded paths require authentication."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data")

        assert response.status_code == 401


class TestAuthHeaderExtraction:
    """Test Authorization header token extraction."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch, jwt_secret):
        """Setup environment."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)

    def test_case_insensitive_bearer_prefix(self, test_app, create_token):
        """Test that Bearer prefix is case insensitive."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        token = create_token(expires_delta=timedelta(hours=1))

        # Test lowercase "bearer"
        response = client.get("/protected/data", headers={"Authorization": f"bearer {token}"})
        assert response.status_code == 200

        # Test mixed case "Bearer"
        response = client.get("/protected/data", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

        # Test uppercase "BEARER"
        response = client.get("/protected/data", headers={"Authorization": f"BEARER {token}"})
        assert response.status_code == 200

    def test_extra_whitespace_in_header(self, test_app):
        """Test that extra whitespace in header causes failure."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        # Multiple spaces between Bearer and token
        response = client.get("/protected/data", headers={"Authorization": "Bearer  token"})
        assert response.status_code == 401


class TestResponseFormat:
    """Test authentication error response format."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch, jwt_secret):
        """Setup environment."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)

    def test_unauthorized_response_has_www_authenticate_header(self, test_app):
        """Test that 401 responses include WWW-Authenticate header."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data")

        assert response.status_code == 401
        assert "www-authenticate" in response.headers
        assert response.headers["www-authenticate"] == "Bearer"

    def test_unauthorized_response_format(self, test_app):
        """Test that 401 responses have correct JSON format."""
        test_app.add_middleware(JWTAuthMiddleware)
        client = TestClient(test_app)

        response = client.get("/protected/data")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert data["error"] == "Unauthorized"


class TestEnvironmentVariableParsing:
    """Test environment variable parsing edge cases."""

    def test_auth_enabled_true_values(self, test_app, monkeypatch, jwt_secret):
        """Test various true values for VALERIE_AUTH_ENABLED."""
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)

        for value in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
            monkeypatch.setenv("VALERIE_AUTH_ENABLED", value)
            middleware = JWTAuthMiddleware(test_app)
            assert middleware.auth_enabled is True

    def test_auth_enabled_false_values(self, test_app, monkeypatch):
        """Test various false values for VALERIE_AUTH_ENABLED."""
        for value in ["false", "False", "FALSE", "0", "no", "No", "NO", ""]:
            monkeypatch.setenv("VALERIE_AUTH_ENABLED", value)
            monkeypatch.delenv("VALERIE_JWT_SECRET", raising=False)
            middleware = JWTAuthMiddleware(test_app)
            assert middleware.auth_enabled is False

    def test_exclude_paths_with_whitespace(self, test_app, monkeypatch, jwt_secret):
        """Test exclude paths parsing with extra whitespace."""
        monkeypatch.setenv("VALERIE_AUTH_ENABLED", "true")
        monkeypatch.setenv("VALERIE_JWT_SECRET", jwt_secret)
        monkeypatch.setenv("VALERIE_AUTH_EXCLUDE_PATHS", " /health , /docs , /api ")

        middleware = JWTAuthMiddleware(test_app)

        assert "/health" in middleware.exclude_paths
        assert "/docs" in middleware.exclude_paths
        assert "/api" in middleware.exclude_paths
