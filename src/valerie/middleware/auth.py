"""JWT Authentication Middleware for FastAPI.

This module provides JWT-based authentication middleware for the Valerie Supplier Chatbot API.
It validates Bearer tokens, extracts tenant_id and user_roles from JWT claims, and stores
them in request.state for downstream use.

Environment Variables:
    VALERIE_JWT_SECRET: Secret key for HS256 signature validation (required in production)
    VALERIE_JWT_ALGORITHM: JWT algorithm (default: HS256)
    VALERIE_AUTH_ENABLED: Enable/disable authentication (default: false for dev)
    VALERIE_AUTH_EXCLUDE_PATHS: Comma-separated paths to exclude from auth
        (default: /health,/live,/ready,/docs,/redoc,/openapi.json)

Example:
    from fastapi import FastAPI
    from valerie.middleware import JWTAuthMiddleware

    app = FastAPI()
    app.add_middleware(JWTAuthMiddleware)
"""

import os
from typing import Any

import jwt
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT Authentication Middleware for FastAPI.

    This middleware:
    1. Checks if the request path is excluded from authentication
    2. Validates JWT Bearer token if auth is enabled
    3. Extracts tenant_id and user_roles from JWT claims
    4. Stores claims in request.state for downstream handlers
    5. Returns 401 for invalid/expired tokens

    Attributes:
        auth_enabled: Whether authentication is enabled (from VALERIE_AUTH_ENABLED)
        jwt_secret: Secret key for JWT validation (from VALERIE_JWT_SECRET)
        jwt_algorithm: JWT algorithm (from VALERIE_JWT_ALGORITHM)
        exclude_paths: Set of paths to exclude from authentication
    """

    def __init__(self, app):
        """Initialize the JWT auth middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)

        # Load configuration from environment
        self.auth_enabled = os.getenv("VALERIE_AUTH_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        self.jwt_secret = os.getenv("VALERIE_JWT_SECRET", "")
        self.jwt_algorithm = os.getenv("VALERIE_JWT_ALGORITHM", "HS256")

        # Parse excluded paths
        exclude_paths_str = os.getenv(
            "VALERIE_AUTH_EXCLUDE_PATHS",
            "/health,/live,/ready,/docs,/redoc,/openapi.json",
        )
        self.exclude_paths = {path.strip() for path in exclude_paths_str.split(",")}

        # Validate configuration
        if self.auth_enabled and not self.jwt_secret:
            raise ValueError(
                "VALERIE_JWT_SECRET is required when VALERIE_AUTH_ENABLED=true. "
                "Set VALERIE_JWT_SECRET environment variable."
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request through authentication middleware.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the next handler or 401 Unauthorized
        """
        # Check if path is excluded from authentication
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # If auth is disabled, run in demo mode
        if not self.auth_enabled:
            self._set_demo_claims(request)
            return await call_next(request)

        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            return self._unauthorized_response("Missing Authorization header")

        # Validate JWT and extract claims
        try:
            claims = self._validate_token(token)
            self._set_claims(request, claims)
        except jwt.ExpiredSignatureError:
            return self._unauthorized_response("Token has expired")
        except jwt.InvalidTokenError as e:
            return self._unauthorized_response(f"Invalid token: {str(e)}")
        except Exception as e:
            return self._unauthorized_response(f"Authentication error: {str(e)}")

        # Proceed to next handler
        return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the request path is excluded from authentication.

        Args:
            path: The URL path to check

        Returns:
            True if path is excluded, False otherwise
        """
        return path in self.exclude_paths

    def _extract_token(self, request: Request) -> str | None:
        """Extract Bearer token from Authorization header.

        Args:
            request: The incoming HTTP request

        Returns:
            JWT token string or None if not found
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        # Parse "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            Dictionary of JWT claims

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        return jwt.decode(
            token,
            self.jwt_secret,
            algorithms=[self.jwt_algorithm],
        )

    def _set_claims(self, request: Request, claims: dict[str, Any]) -> None:
        """Store JWT claims in request.state for downstream use.

        Args:
            request: The incoming HTTP request
            claims: Dictionary of JWT claims
        """
        # Extract tenant_id (required)
        tenant_id = claims.get("tenant_id")
        if not tenant_id:
            raise ValueError("JWT token missing required claim: tenant_id")

        # Extract user_roles (optional, defaults to empty list)
        user_roles = claims.get("user_roles", [])
        if not isinstance(user_roles, list):
            user_roles = [user_roles]

        # Store in request.state
        request.state.tenant_id = tenant_id
        request.state.user_roles = user_roles
        request.state.jwt_claims = claims
        request.state.auth_enabled = True

    def _set_demo_claims(self, request: Request) -> None:
        """Set demo claims when authentication is disabled.

        Args:
            request: The incoming HTTP request
        """
        request.state.tenant_id = "demo-tenant"
        request.state.user_roles = ["demo-user"]
        request.state.jwt_claims = {
            "tenant_id": "demo-tenant",
            "user_roles": ["demo-user"],
            "sub": "demo@example.com",
        }
        request.state.auth_enabled = False

    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Create a 401 Unauthorized response.

        Args:
            message: Error message to include in response

        Returns:
            JSONResponse with 401 status code
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "message": message,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
