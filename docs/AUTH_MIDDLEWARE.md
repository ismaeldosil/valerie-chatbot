# JWT Authentication Middleware

This document describes the JWT authentication middleware for the Valerie Supplier Chatbot API.

## Overview

The `JWTAuthMiddleware` provides JWT-based authentication for FastAPI applications. It validates Bearer tokens, extracts tenant and user information from JWT claims, and stores them in `request.state` for downstream handlers.

## Features

- JWT token validation with configurable algorithms (HS256, HS512, etc.)
- Support for Bearer tokens in Authorization headers
- Extraction of `tenant_id` and `user_roles` from JWT claims
- Configurable via environment variables
- Demo mode for development (auth disabled)
- Flexible path exclusion for public endpoints
- Proper 401 error responses with WWW-Authenticate headers

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VALERIE_AUTH_ENABLED` | Enable/disable authentication | `false` | No |
| `VALERIE_JWT_SECRET` | Secret key for JWT validation | - | Yes (when auth enabled) |
| `VALERIE_JWT_ALGORITHM` | JWT algorithm (HS256, HS512, etc.) | `HS256` | No |
| `VALERIE_AUTH_EXCLUDE_PATHS` | Comma-separated paths to exclude | `/health,/live,/ready,/docs,/redoc,/openapi.json` | No |

## Installation

The middleware is included in the `valerie-chatbot` package. PyJWT is a required dependency.

```bash
# PyJWT is already in pyproject.toml dependencies
uv pip install pyjwt
```

## Usage

### Basic Setup

```python
from fastapi import FastAPI
from valerie.middleware import JWTAuthMiddleware

app = FastAPI()

# Add JWT authentication middleware
app.add_middleware(JWTAuthMiddleware)

@app.get("/protected/data")
async def protected_endpoint(request: Request):
    # Access authenticated user information
    tenant_id = request.state.tenant_id
    user_roles = request.state.user_roles

    return {
        "tenant_id": tenant_id,
        "roles": user_roles
    }
```

### Development Mode (Auth Disabled)

For local development, you can disable authentication:

```bash
# .env file
VALERIE_AUTH_ENABLED=false
```

When auth is disabled, the middleware sets demo claims:
- `tenant_id`: "demo-tenant"
- `user_roles`: ["demo-user"]
- `auth_enabled`: False

### Production Mode (Auth Enabled)

For production, enable authentication and set your JWT secret:

```bash
# .env file
VALERIE_AUTH_ENABLED=true
VALERIE_JWT_SECRET=your-secret-key-here
VALERIE_JWT_ALGORITHM=HS256
```

### Custom Exclude Paths

Exclude specific paths from authentication:

```bash
# .env file
VALERIE_AUTH_EXCLUDE_PATHS=/health,/docs,/api/public,/webhooks
```

## JWT Token Format

### Required Claims

- `tenant_id` (string): Tenant identifier - **required**
- `user_roles` (array of strings): User roles - optional, defaults to empty list

### Optional Claims

- `sub` (string): Subject (typically user email or ID)
- `exp` (integer): Expiration timestamp
- `iat` (integer): Issued at timestamp
- Any custom claims your application needs

### Example Token Payload

```json
{
  "tenant_id": "acme-corp",
  "user_roles": ["admin", "user"],
  "sub": "john.doe@example.com",
  "organization": "ACME Corporation",
  "iat": 1734729600,
  "exp": 1734816000
}
```

## Creating JWT Tokens

### Python Example

```python
import jwt
from datetime import datetime, timedelta

def create_token(tenant_id: str, user_roles: list[str], secret: str) -> str:
    """Create a JWT token for authentication."""
    claims = {
        "tenant_id": tenant_id,
        "user_roles": user_roles,
        "sub": "user@example.com",
        "iat": datetime.now(datetime.UTC),
        "exp": datetime.now(datetime.UTC) + timedelta(hours=24),
    }
    return jwt.encode(claims, secret, algorithm="HS256")

# Example
token = create_token(
    tenant_id="acme-corp",
    user_roles=["admin", "user"],
    secret="your-secret-key"
)
```

### Command Line Example

```bash
# Using Python one-liner
python -c "import jwt; from datetime import datetime, timedelta; print(jwt.encode({'tenant_id': 'test', 'user_roles': ['user'], 'exp': datetime.now(datetime.UTC) + timedelta(hours=1)}, 'secret', algorithm='HS256'))"
```

## Making Authenticated Requests

### Using curl

```bash
# Set your token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/protected

# Example response
{
  "tenant_id": "acme-corp",
  "user_roles": ["admin", "user"],
  "data": "..."
}
```

### Using Python requests

```python
import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

response = requests.get(
    "http://localhost:8000/api/protected",
    headers={"Authorization": f"Bearer {token}"}
)

data = response.json()
print(f"Tenant: {data['tenant_id']}")
```

## Accessing User Information in Handlers

The middleware stores authentication information in `request.state`:

```python
from fastapi import Request

@app.get("/api/data")
async def get_data(request: Request):
    # Access tenant ID
    tenant_id = request.state.tenant_id

    # Access user roles
    user_roles = request.state.user_roles

    # Access all JWT claims
    jwt_claims = request.state.jwt_claims

    # Check auth mode
    is_auth_enabled = request.state.auth_enabled

    return {
        "tenant": tenant_id,
        "roles": user_roles,
        "email": jwt_claims.get("sub"),
    }
```

## Role-Based Access Control

Implement role checking in your endpoints:

```python
from fastapi import Request, HTTPException

@app.get("/api/admin/settings")
async def admin_settings(request: Request):
    # Check for admin role
    if "admin" not in request.state.user_roles:
        raise HTTPException(
            status_code=403,
            detail="Admin role required"
        )

    return {"settings": "..."}
```

## Error Responses

### 401 Unauthorized

The middleware returns 401 for authentication failures:

```json
{
  "error": "Unauthorized",
  "message": "Missing Authorization header"
}
```

Common error messages:
- "Missing Authorization header"
- "Token has expired"
- "Invalid token: <details>"
- "JWT token missing required claim: tenant_id"

All 401 responses include `WWW-Authenticate: Bearer` header.

## Testing

### Unit Tests

The middleware includes comprehensive unit tests:

```bash
# Run all auth middleware tests
pytest tests/unit/test_auth_middleware.py -v

# Run specific test class
pytest tests/unit/test_auth_middleware.py::TestJWTAuthMiddlewareEnabled -v
```

### Integration Testing

```python
from fastapi.testclient import TestClient
import jwt

def test_authenticated_endpoint():
    client = TestClient(app)

    # Create test token
    token = jwt.encode(
        {"tenant_id": "test", "user_roles": ["user"]},
        "test-secret",
        algorithm="HS256"
    )

    # Make authenticated request
    response = client.get(
        "/api/data",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "test"
```

## Security Best Practices

1. **Use Strong Secrets**: Use cryptographically secure random strings for `VALERIE_JWT_SECRET`
   ```bash
   # Generate secure secret
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use HTTPS**: Always use HTTPS in production to prevent token interception

3. **Set Token Expiration**: Include `exp` claim in your tokens
   ```python
   claims["exp"] = datetime.now(datetime.UTC) + timedelta(hours=1)
   ```

4. **Rotate Secrets**: Regularly rotate your JWT secrets

5. **Validate Input**: Always validate tenant_id and user_roles in your handlers

6. **Minimal Exclude Paths**: Only exclude paths that truly need to be public

## Troubleshooting

### "VALERIE_JWT_SECRET is required" Error

**Problem**: Auth is enabled but no secret is configured.

**Solution**: Set the `VALERIE_JWT_SECRET` environment variable:
```bash
export VALERIE_JWT_SECRET=your-secret-key-here
```

### "Token has expired" Error

**Problem**: JWT token expiration time has passed.

**Solution**: Generate a new token with a fresh expiration time.

### "JWT token missing required claim: tenant_id" Error

**Problem**: Token doesn't include `tenant_id` claim.

**Solution**: Ensure your token includes the required `tenant_id` claim:
```python
claims = {"tenant_id": "your-tenant", ...}
```

### Middleware Not Applied to Endpoint

**Problem**: Endpoint is accessible without authentication.

**Solution**:
1. Check that path is not in `VALERIE_AUTH_EXCLUDE_PATHS`
2. Verify `VALERIE_AUTH_ENABLED=true`
3. Ensure middleware is added before route definitions

## Examples

See `examples/auth_middleware_example.py` for a complete working example with:
- Public and protected endpoints
- Role-based access control
- Custom JWT claims
- Token generation helpers

Run the example:
```bash
cd examples
python auth_middleware_example.py
```

## Architecture

The middleware follows the FastAPI/Starlette middleware pattern:

1. Request arrives at middleware
2. Check if path is excluded → skip auth
3. If auth disabled → set demo claims
4. If auth enabled → validate JWT token
5. Extract claims and store in `request.state`
6. Pass request to next handler
7. Return response

```
Request → Middleware → Extract Token → Validate JWT → Set State → Handler → Response
                ↓                                          ↓
         Excluded Path?                              Auth Enabled?
                ↓                                          ↓
            Skip Auth                                  Demo Mode
```

## Integration with Existing API

To add JWT auth to the existing Valerie Supplier Chatbot API:

1. Update `api/main.py`:
```python
from valerie.middleware import JWTAuthMiddleware

def create_app() -> FastAPI:
    app = FastAPI(...)

    # Add JWT auth middleware (before other middleware)
    app.add_middleware(JWTAuthMiddleware)

    # Add CORS and other middleware
    app.add_middleware(CORSMiddleware, ...)

    return app
```

2. Set environment variables in `.env`:
```bash
VALERIE_AUTH_ENABLED=true
VALERIE_JWT_SECRET=your-secret-key
```

3. Update route handlers to use tenant information:
```python
@router.post("/chat")
async def chat(request: Request, message: ChatRequest):
    tenant_id = request.state.tenant_id
    # Use tenant_id for session management, data isolation, etc.
```

## License

MIT License - See project LICENSE file for details.
