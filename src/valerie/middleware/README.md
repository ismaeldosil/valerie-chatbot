# Rate Limiting Middleware

FastAPI middleware for rate limiting using sliding window algorithm with support for both in-memory and Redis backends.

## Features

- **Per-IP and per-tenant rate limiting** - Tracks requests by IP address or tenant ID
- **Sliding window algorithm** - More accurate than fixed windows, no burst issues
- **Dual backend support** - In-memory (for single instance) or Redis (for distributed systems)
- **Configurable limits** - Separate per-minute and per-hour limits
- **Standard HTTP headers** - Returns proper `429 Too Many Requests` with `Retry-After` and `X-RateLimit-*` headers
- **Environment variable configuration** - Easy deployment configuration

## Installation

The middleware is included in the `valerie-chatbot` package. For Redis support, install the optional dependency:

```bash
pip install redis
```

## Basic Usage

### In-Memory Backend (Single Instance)

```python
from fastapi import FastAPI
from valerie.middleware import RateLimitMiddleware

app = FastAPI()

# Add rate limiting with in-memory storage
app.add_middleware(
    RateLimitMiddleware,
    enabled=True,
    per_minute=60,
    per_hour=1000,
)
```

### Redis Backend (Distributed)

```python
from fastapi import FastAPI
from valerie.middleware import RateLimitMiddleware

app = FastAPI()

# Add rate limiting with Redis backend
app.add_middleware(
    RateLimitMiddleware,
    enabled=True,
    per_minute=60,
    per_hour=1000,
    redis_url="redis://localhost:6379/0",
)
```

## Environment Variables

Configure the middleware using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `VALERIE_RATE_LIMIT_ENABLED` | Enable/disable rate limiting | `true` |
| `VALERIE_RATE_LIMIT_PER_MINUTE` | Requests per minute per client | `60` |
| `VALERIE_RATE_LIMIT_PER_HOUR` | Requests per hour per client | `1000` |
| `VALERIE_RATE_LIMIT_REDIS_URL` | Redis connection URL (optional) | None |

Example `.env` file:

```bash
VALERIE_RATE_LIMIT_ENABLED=true
VALERIE_RATE_LIMIT_PER_MINUTE=100
VALERIE_RATE_LIMIT_PER_HOUR=5000
VALERIE_RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
```

## Client Identification

The middleware identifies clients using the following priority:

1. **Tenant ID from header** - `X-Tenant-ID` header
2. **Tenant ID from query** - `?tenant_id=xxx` query parameter
3. **IP address** - Client IP from `X-Forwarded-For` or direct connection

This allows you to implement per-tenant rate limiting in multi-tenant applications.

## Response Headers

All responses include rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1703088000
```

When rate limited:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1703088000
Retry-After: 30

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 30
}
```

## Sliding Window Algorithm

The middleware uses a sliding window algorithm for more accurate rate limiting:

- Tracks individual request timestamps
- No burst issues at window boundaries
- More fair than fixed windows
- Automatic cleanup of expired timestamps

Example with 5 requests per minute:

```
Time:     0s   10s   20s   30s   40s   50s   60s   70s
Requests: 1    2     3     4     5     X     1     2
                                     ^
                                   Rate limited
                              (5 requests in last 60s)
```

## Architecture

### Storage Backends

#### InMemoryStore

- Default backend
- Stores timestamps in memory using Python dictionaries
- Suitable for single-instance deployments
- No external dependencies
- Fast and simple

#### RedisStore

- Optional backend for distributed systems
- Uses Redis sorted sets (`ZSET`) for timestamp storage
- Automatic TTL/expiration
- Thread-safe across multiple instances
- Falls back to InMemoryStore if Redis is unavailable

### Implementation Details

```python
# Storage interface
class RateLimitStore:
    async def add_request(self, key: str, timestamp: float, window: int) -> int:
        """Add request and return count in window"""

    async def get_count(self, key: str, window: int) -> int:
        """Get current request count"""

    async def cleanup(self, key: str, cutoff: float):
        """Remove expired timestamps"""
```

## Testing

Run the unit tests:

```bash
pytest tests/unit/test_rate_limit_middleware.py -v
```

The test suite covers:

- ✓ In-memory storage operations
- ✓ Redis storage with fallback
- ✓ Per-minute and per-hour limits
- ✓ Client identification (IP, tenant header, tenant query)
- ✓ Response headers
- ✓ Concurrent requests
- ✓ Environment variable configuration
- ✓ Edge cases

## Production Considerations

### Distributed Systems

For multi-instance deployments, use Redis backend:

```python
app.add_middleware(
    RateLimitMiddleware,
    enabled=True,
    per_minute=60,
    per_hour=1000,
    redis_url=os.getenv("REDIS_URL"),
)
```

### Redis High Availability

Configure Redis with replication for production:

```bash
# Primary-replica setup
VALERIE_RATE_LIMIT_REDIS_URL=redis://primary:6379/0

# Redis Sentinel
VALERIE_RATE_LIMIT_REDIS_URL=redis+sentinel://sentinel:26379/mymaster/0

# Redis Cluster
VALERIE_RATE_LIMIT_REDIS_URL=redis://cluster:6379/0?cluster=true
```

### Memory Management

In-memory backend cleanup:

- Old timestamps are automatically removed when checking limits
- No background cleanup tasks required
- Memory usage scales with active clients and window size

Redis backend cleanup:

- Uses Redis TTL for automatic expiration
- TTL set to `window + 60` seconds
- No manual cleanup required

### Performance

Typical performance characteristics:

| Backend | Latency | Throughput | Memory |
|---------|---------|------------|--------|
| In-Memory | < 1ms | 10k+ req/s | Low |
| Redis (local) | 1-3ms | 5k+ req/s | Medium |
| Redis (remote) | 5-20ms | 2k+ req/s | Low |

### Monitoring

Log rate limit events:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# The middleware logs warnings when clients are rate limited
logger = logging.getLogger("valerie.middleware.rate_limit")
```

## Examples

### Per-Tenant Limiting

```python
# Client includes tenant header
curl -H "X-Tenant-ID: acme-corp" https://api.example.com/chat
```

### Development Mode

```python
# Disable rate limiting in development
app.add_middleware(
    RateLimitMiddleware,
    enabled=os.getenv("ENVIRONMENT") == "production",
    per_minute=100,
)
```

### Custom Limits by Endpoint

```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

class CustomRateLimitMiddleware(RateLimitMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.endpoint_limits = {
            "/api/expensive": (10, 100),  # (per_minute, per_hour)
            "/api/cheap": (100, 1000),
        }

    async def dispatch(self, request: Request, call_next):
        # Override limits based on endpoint
        path = request.url.path
        if path in self.endpoint_limits:
            old_min, old_hour = self.per_minute, self.per_hour
            self.per_minute, self.per_hour = self.endpoint_limits[path]
            response = await super().dispatch(request, call_next)
            self.per_minute, self.per_hour = old_min, old_hour
            return response
        return await super().dispatch(request, call_next)
```

## Troubleshooting

### Redis Connection Issues

If Redis is unavailable, the middleware automatically falls back to in-memory storage:

```
WARNING - Failed to connect to Redis: Connection refused, falling back to in-memory store
```

### Rate Limit Not Working

Check that:

1. Middleware is enabled: `VALERIE_RATE_LIMIT_ENABLED=true`
2. Limits are set correctly
3. Client identifier is stable (same IP or tenant ID)

### Unexpected Rate Limiting

Verify client identification:

```python
# Add debug logging to see which identifier is used
middleware = RateLimitMiddleware(app, enabled=True)

# In dispatch method, add:
identifier = self._get_client_identifier(request)
logger.info(f"Rate limiting for: {identifier}")
```

## License

Part of the valerie-chatbot project.
