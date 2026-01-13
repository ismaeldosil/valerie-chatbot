"""Example usage of JWT Authentication Middleware with FastAPI.

This example demonstrates how to integrate the JWT authentication middleware
into your FastAPI application and how to access authenticated user information
from request handlers.

To run this example:
    1. Set environment variables:
       export VALERIE_AUTH_ENABLED=true
       export VALERIE_JWT_SECRET=your-secret-key-here

    2. Run the example:
       python examples/auth_middleware_example.py

    3. Test with curl:
       # Get a token (you'd normally get this from your auth service)
       TOKEN=$(python -c "import jwt; print(jwt.encode({'tenant_id': 'acme-corp', 'user_roles': ['admin', 'user']}, 'your-secret-key-here', algorithm='HS256'))")

       # Access protected endpoint
       curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/users
"""

import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from valerie.middleware import JWTAuthMiddleware


# Create FastAPI app
app = FastAPI(
    title="JWT Auth Example",
    description="Example of JWT authentication middleware",
)

# Add JWT authentication middleware
app.add_middleware(JWTAuthMiddleware)


# Public endpoint - no authentication required (must be in exclude paths)
@app.get("/health")
async def health():
    """Health check endpoint - publicly accessible."""
    return {"status": "healthy"}


# Protected endpoint - requires authentication
@app.get("/api/users")
async def get_users(request: Request):
    """Get users - requires authentication.

    This endpoint demonstrates accessing authenticated user information
    from request.state.
    """
    return {
        "tenant_id": request.state.tenant_id,
        "user_roles": request.state.user_roles,
        "message": f"Hello from tenant {request.state.tenant_id}",
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ],
    }


# Protected endpoint with role checking
@app.get("/api/admin/settings")
async def get_admin_settings(request: Request):
    """Get admin settings - requires admin role.

    This endpoint demonstrates checking user roles from JWT claims.
    """
    # Check if user has admin role
    if "admin" not in request.state.user_roles:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Forbidden",
                "message": "Admin role required",
            },
        )

    return {
        "tenant_id": request.state.tenant_id,
        "settings": {
            "max_users": 100,
            "features": ["analytics", "export"],
        },
    }


# Endpoint that accesses custom JWT claims
@app.get("/api/profile")
async def get_profile(request: Request):
    """Get user profile - accesses custom JWT claims."""
    jwt_claims = request.state.jwt_claims

    return {
        "tenant_id": request.state.tenant_id,
        "user_roles": request.state.user_roles,
        "email": jwt_claims.get("sub"),
        "organization": jwt_claims.get("organization", "N/A"),
        "custom_claims": {
            k: v for k, v in jwt_claims.items()
            if k not in ["tenant_id", "user_roles", "sub", "iat", "exp"]
        },
    }


# Helper function to generate test tokens
def create_test_token(
    tenant_id: str = "test-tenant",
    user_roles: list[str] | None = None,
    secret: str = "test-secret-key",
) -> str:
    """Create a test JWT token.

    Args:
        tenant_id: Tenant identifier
        user_roles: List of user roles
        secret: Secret key for signing

    Returns:
        Encoded JWT token string
    """
    if user_roles is None:
        user_roles = ["user"]

    claims = {
        "tenant_id": tenant_id,
        "user_roles": user_roles,
        "sub": "user@example.com",
        "organization": "Acme Corp",
        "iat": datetime.now(datetime.UTC),
        "exp": datetime.now(datetime.UTC) + timedelta(hours=24),
    }

    return jwt.encode(claims, secret, algorithm="HS256")


if __name__ == "__main__":
    import uvicorn

    # Print example token for testing
    print("\n" + "=" * 80)
    print("JWT Authentication Middleware Example")
    print("=" * 80)
    print("\nExample token (valid for 24 hours):")
    token = create_test_token(
        tenant_id="acme-corp",
        user_roles=["admin", "user"],
        secret="test-secret-key",
    )
    print(f"\n{token}\n")
    print("Test with:")
    print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/users')
    print("\n" + "=" * 80 + "\n")

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)
