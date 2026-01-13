"""
Rate limiting middleware for FastAPI using sliding window algorithm.

Supports both in-memory and Redis-backed rate limiting with per-IP
and per-tenant tracking.
"""

import logging
import os
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitStore:
    """Base class for rate limit storage backends."""

    async def add_request(self, key: str, timestamp: float, window: int) -> int:
        """Add a request timestamp and return current count in window."""
        raise NotImplementedError

    async def get_count(self, key: str, window: int) -> int:
        """Get request count in the current window."""
        raise NotImplementedError

    async def cleanup(self, key: str, cutoff: float):
        """Remove expired timestamps."""
        raise NotImplementedError


class InMemoryStore(RateLimitStore):
    """In-memory storage for rate limiting using sliding window."""

    def __init__(self):
        self.store: dict[str, list[float]] = defaultdict(list)

    async def add_request(self, key: str, timestamp: float, window: int) -> int:
        """Add a request timestamp and return current count in window."""
        cutoff = timestamp - window

        # Clean up old timestamps
        self.store[key] = [ts for ts in self.store[key] if ts > cutoff]

        # Add new timestamp
        self.store[key].append(timestamp)

        return len(self.store[key])

    async def get_count(self, key: str, window: int) -> int:
        """Get request count in the current window."""
        now = time.time()
        cutoff = now - window

        # Clean up and count
        self.store[key] = [ts for ts in self.store[key] if ts > cutoff]
        return len(self.store[key])

    async def cleanup(self, key: str, cutoff: float):
        """Remove expired timestamps."""
        self.store[key] = [ts for ts in self.store[key] if ts > cutoff]
        if not self.store[key]:
            del self.store[key]


class RedisStore(RateLimitStore):
    """Redis-backed storage for distributed rate limiting."""

    def __init__(self, redis_url: str):
        # Always initialize fallback
        self.fallback = InMemoryStore()

        try:
            import redis.asyncio as aioredis

            self.redis = aioredis.from_url(redis_url, decode_responses=False)
            self._available = True
        except ImportError:
            logger.warning("redis package not installed, falling back to in-memory store")
            self._available = False
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, falling back to in-memory store")
            self._available = False

    async def add_request(self, key: str, timestamp: float, window: int) -> int:
        """Add a request timestamp using Redis sorted set."""
        if not self._available:
            return await self.fallback.add_request(key, timestamp, window)

        try:
            pipe = self.redis.pipeline()
            cutoff = timestamp - window

            # Remove old timestamps
            pipe.zremrangebyscore(key, 0, cutoff)

            # Add new timestamp
            pipe.zadd(key, {str(timestamp): timestamp})

            # Count items in window
            pipe.zcard(key)

            # Set expiration
            pipe.expire(key, int(window) + 60)

            results = await pipe.execute()
            return results[2]  # Count from zcard
        except Exception as e:
            logger.error(f"Redis error: {e}, using fallback")
            return await self.fallback.add_request(key, timestamp, window)

    async def get_count(self, key: str, window: int) -> int:
        """Get request count in the current window."""
        if not self._available:
            return await self.fallback.get_count(key, window)

        try:
            now = time.time()
            cutoff = now - window

            # Remove old entries and count
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            results = await pipe.execute()
            return results[1]
        except Exception as e:
            logger.error(f"Redis error: {e}, using fallback")
            return await self.fallback.get_count(key, window)

    async def cleanup(self, key: str, cutoff: float):
        """Remove expired timestamps."""
        if not self._available:
            return await self.fallback.cleanup(key, cutoff)

        try:
            await self.redis.zremrangebyscore(key, 0, cutoff)
        except Exception as e:
            logger.error(f"Redis cleanup error: {e}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    Supports per-IP and per-tenant rate limiting with configurable limits
    and optional Redis backend for distributed systems.
    """

    def __init__(
        self,
        app,
        enabled: bool | None = None,
        per_minute: int | None = None,
        per_hour: int | None = None,
        redis_url: str | None = None,
    ):
        super().__init__(app)

        # Load configuration from environment or use defaults
        self.enabled = (
            enabled
            if enabled is not None
            else (os.getenv("VALERIE_RATE_LIMIT_ENABLED", "true").lower() == "true")
        )
        self.per_minute = per_minute or int(os.getenv("VALERIE_RATE_LIMIT_PER_MINUTE", "60"))
        self.per_hour = per_hour or int(os.getenv("VALERIE_RATE_LIMIT_PER_HOUR", "1000"))

        # Initialize storage backend
        redis_url = redis_url or os.getenv("VALERIE_RATE_LIMIT_REDIS_URL")
        if redis_url:
            self.store = RedisStore(redis_url)
            logger.info("Rate limiting initialized with Redis backend")
        else:
            self.store = InMemoryStore()
            logger.info("Rate limiting initialized with in-memory backend")

        logger.info(
            f"Rate limiting configured: enabled={self.enabled}, "
            f"per_minute={self.per_minute}, per_hour={self.per_hour}"
        )

    def _get_client_identifier(self, request: Request) -> str:
        """
        Extract client identifier from request.

        Tries tenant_id from headers/query, then falls back to IP address.
        """
        # Check for tenant identifier in headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Check query parameters
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Fall back to IP address
        # Try to get real IP from proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit(
        self, identifier: str, timestamp: float
    ) -> tuple[bool, int, int, int]:
        """
        Check if request should be rate limited.

        Returns:
            Tuple of (is_allowed, limit, remaining, reset_time)
        """
        # Check minute limit
        minute_key = f"{identifier}:minute"
        minute_count = await self.store.add_request(minute_key, timestamp, 60)

        if minute_count > self.per_minute:
            reset_time = int(timestamp + 60)
            return False, self.per_minute, 0, reset_time

        # Check hour limit
        hour_key = f"{identifier}:hour"
        hour_count = await self.store.add_request(hour_key, timestamp, 3600)

        if hour_count > self.per_hour:
            reset_time = int(timestamp + 3600)
            return False, self.per_hour, 0, reset_time

        # Use the more restrictive limit for headers
        # Normalize to same time window for comparison
        minute_remaining = self.per_minute - minute_count
        hour_remaining_normalized = self.per_hour - hour_count

        # Return minute-based limits as they're more restrictive in short term
        remaining = min(minute_remaining, hour_remaining_normalized)
        reset_time = int(timestamp + 60)

        return True, self.per_minute, max(0, remaining), reset_time

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Get client identifier
        identifier = self._get_client_identifier(request)
        timestamp = time.time()

        # Check rate limit
        is_allowed, limit, remaining, reset_time = await self._check_rate_limit(
            identifier, timestamp
        )

        # If rate limited, return 429
        if not is_allowed:
            retry_after = reset_time - int(timestamp)

            logger.warning(
                f"Rate limit exceeded for {identifier}: limit={limit}, retry_after={retry_after}s"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response
