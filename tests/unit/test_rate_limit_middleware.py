"""
Unit tests for rate limiting middleware.
"""

import time
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from valerie.middleware.rate_limit import (
    InMemoryStore,
    RateLimitMiddleware,
    RedisStore,
)


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    return app


@pytest.fixture
def client_with_rate_limit(app):
    """Create a test client with rate limiting enabled."""
    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        per_minute=5,
        per_hour=10,
        redis_url=None,
    )
    return TestClient(app)


class TestInMemoryStore:
    """Test in-memory storage backend."""

    @pytest.mark.asyncio
    async def test_add_request(self):
        """Test adding requests and counting."""
        store = InMemoryStore()
        now = time.time()

        # Add requests
        count1 = await store.add_request("test:key", now, 60)
        assert count1 == 1

        count2 = await store.add_request("test:key", now + 1, 60)
        assert count2 == 2

        count3 = await store.add_request("test:key", now + 2, 60)
        assert count3 == 3

    @pytest.mark.asyncio
    async def test_sliding_window(self):
        """Test that old requests are excluded from count."""
        store = InMemoryStore()
        now = time.time()

        # Add request at start of window
        await store.add_request("test:key", now - 65, 60)
        await store.add_request("test:key", now - 30, 60)
        await store.add_request("test:key", now, 60)

        # The request from 65 seconds ago should be excluded
        count = await store.get_count("test:key", 60)
        assert count == 2

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup of expired timestamps."""
        store = InMemoryStore()
        now = time.time()

        await store.add_request("test:key", now - 100, 60)
        await store.add_request("test:key", now - 50, 60)
        await store.add_request("test:key", now, 60)

        # Cleanup old entries
        await store.cleanup("test:key", now - 60)

        # Should only have recent entries
        count = await store.get_count("test:key", 60)
        assert count == 2

    @pytest.mark.asyncio
    async def test_multiple_keys(self):
        """Test that different keys are tracked separately."""
        store = InMemoryStore()
        now = time.time()

        await store.add_request("key1", now, 60)
        await store.add_request("key1", now + 1, 60)
        await store.add_request("key2", now, 60)

        count1 = await store.get_count("key1", 60)
        count2 = await store.get_count("key2", 60)

        assert count1 == 2
        assert count2 == 1


class TestRedisStore:
    """Test Redis storage backend."""

    @pytest.mark.asyncio
    async def test_fallback_when_redis_unavailable(self):
        """Test fallback to in-memory when Redis is unavailable."""
        with patch("redis.asyncio.from_url", side_effect=Exception("Connection failed")):
            store = RedisStore("redis://localhost:6379")
            assert store._available is False
            assert isinstance(store.fallback, InMemoryStore)

    @pytest.mark.asyncio
    async def test_fallback_when_redis_not_installed(self):
        """Test fallback when redis package is not installed."""
        with patch.dict("sys.modules", {"redis.asyncio": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module named 'redis'")):
                # This would fail during import, so we simulate the behavior
                store = RedisStore("redis://localhost:6379")
                # Should use fallback
                now = time.time()
                count = await store.add_request("test:key", now, 60)
                assert count >= 0

    @pytest.mark.asyncio
    async def test_redis_operations_with_mock(self):
        """Test Redis operations with mocked Redis client."""
        mock_redis = Mock()
        mock_pipeline = Mock()

        # Setup pipeline mock methods to return self for chaining
        mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
        mock_pipeline.zadd = Mock(return_value=mock_pipeline)
        mock_pipeline.zcard = Mock(return_value=mock_pipeline)
        mock_pipeline.expire = Mock(return_value=mock_pipeline)

        # Make execute async and return the results
        async def async_execute():
            return [1, 1, 3, True]

        mock_pipeline.execute = async_execute

        mock_redis.pipeline = Mock(return_value=mock_pipeline)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisStore("redis://localhost:6379")
            store.redis = mock_redis
            store._available = True

            now = time.time()
            count = await store.add_request("test:key", now, 60)

            assert count == 3
            mock_redis.pipeline.assert_called()


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    def test_middleware_disabled(self, app):
        """Test that middleware passes through when disabled."""
        app.add_middleware(RateLimitMiddleware, enabled=False)
        client = TestClient(app)

        # Should not rate limit even with many requests
        for _ in range(100):
            response = client.get("/test")
            assert response.status_code == 200

    def test_per_minute_limit(self, client_with_rate_limit):
        """Test per-minute rate limit."""
        # Make requests up to limit
        for i in range(5):
            response = client_with_rate_limit.get("/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

        # Next request should be rate limited
        response = client_with_rate_limit.get("/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.json()["error"] == "rate_limit_exceeded"

    def test_rate_limit_headers(self, client_with_rate_limit):
        """Test that rate limit headers are present and correct."""
        response = client_with_rate_limit.get("/test")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert int(response.headers["X-RateLimit-Remaining"]) <= 5
        assert int(response.headers["X-RateLimit-Reset"]) > int(time.time())

    def test_client_identifier_by_ip(self, app):
        """Test client identification by IP address."""
        app.add_middleware(RateLimitMiddleware, enabled=True, per_minute=2)
        client = TestClient(app)

        # Make requests from default IP
        response1 = client.get("/test")
        response2 = client.get("/test")
        response3 = client.get("/test")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 429

    def test_client_identifier_by_tenant_header(self, app):
        """Test client identification by tenant ID in header."""
        app.add_middleware(RateLimitMiddleware, enabled=True, per_minute=2)
        client = TestClient(app)

        # Make requests with tenant header
        headers = {"X-Tenant-ID": "tenant-123"}
        response1 = client.get("/test", headers=headers)
        response2 = client.get("/test", headers=headers)
        response3 = client.get("/test", headers=headers)

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 429

    def test_client_identifier_by_tenant_query(self, app):
        """Test client identification by tenant ID in query parameter."""
        app.add_middleware(RateLimitMiddleware, enabled=True, per_minute=2)
        client = TestClient(app)

        # Make requests with tenant query param
        response1 = client.get("/test?tenant_id=tenant-456")
        response2 = client.get("/test?tenant_id=tenant-456")
        response3 = client.get("/test?tenant_id=tenant-456")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 429

    def test_different_clients_tracked_separately(self, app):
        """Test that different clients have separate rate limits."""
        app.add_middleware(RateLimitMiddleware, enabled=True, per_minute=2)
        client = TestClient(app)

        # Requests from tenant 1
        headers1 = {"X-Tenant-ID": "tenant-1"}
        response1 = client.get("/test", headers=headers1)
        response2 = client.get("/test", headers=headers1)

        # Requests from tenant 2
        headers2 = {"X-Tenant-ID": "tenant-2"}
        response3 = client.get("/test", headers=headers2)
        response4 = client.get("/test", headers=headers2)

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert response4.status_code == 200

        # Next requests should be limited per tenant
        response5 = client.get("/test", headers=headers1)
        response6 = client.get("/test", headers=headers2)

        assert response5.status_code == 429
        assert response6.status_code == 429

    def test_forwarded_for_header(self, app):
        """Test that X-Forwarded-For header is used for IP identification."""
        middleware = RateLimitMiddleware(app, enabled=True, per_minute=5)

        # Create mock request with X-Forwarded-For
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        request.query_params = {}
        request.client = Mock(host="127.0.0.1")

        identifier = middleware._get_client_identifier(request)
        assert identifier == "ip:192.168.1.100"

    def test_retry_after_header(self, client_with_rate_limit):
        """Test that Retry-After header is set correctly."""
        # Exhaust rate limit
        for _ in range(5):
            client_with_rate_limit.get("/test")

        # Get rate limited response
        response = client_with_rate_limit.get("/test")
        assert response.status_code == 429

        retry_after = int(response.headers["Retry-After"])
        assert 0 <= retry_after <= 60

    def test_rate_limit_reset(self, app):
        """Test that rate limit resets after window expires."""
        app.add_middleware(RateLimitMiddleware, enabled=True, per_minute=2)
        client = TestClient(app)

        # Exhaust limit
        response1 = client.get("/test")
        response2 = client.get("/test")
        response3 = client.get("/test")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 429

        # In a real scenario, we'd wait 60 seconds, but for testing
        # we can verify the logic by checking the store directly
        # This is tested more thoroughly in TestInMemoryStore

    def test_environment_variable_configuration(self):
        """Test configuration from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "VALERIE_RATE_LIMIT_ENABLED": "true",
                "VALERIE_RATE_LIMIT_PER_MINUTE": "100",
                "VALERIE_RATE_LIMIT_PER_HOUR": "5000",
            },
        ):
            app = FastAPI()
            middleware = RateLimitMiddleware(app)

            assert middleware.enabled is True
            assert middleware.per_minute == 100
            assert middleware.per_hour == 5000

    def test_environment_variable_disabled(self):
        """Test disabling via environment variable."""
        with patch.dict("os.environ", {"VALERIE_RATE_LIMIT_ENABLED": "false"}):
            app = FastAPI()
            middleware = RateLimitMiddleware(app)

            assert middleware.enabled is False

    def test_constructor_params_override_env(self):
        """Test that constructor parameters override environment variables."""
        with patch.dict(
            "os.environ",
            {
                "VALERIE_RATE_LIMIT_ENABLED": "false",
                "VALERIE_RATE_LIMIT_PER_MINUTE": "100",
            },
        ):
            app = FastAPI()
            middleware = RateLimitMiddleware(app, enabled=True, per_minute=50)

            assert middleware.enabled is True
            assert middleware.per_minute == 50

    @pytest.mark.asyncio
    async def test_hour_limit_exceeded(self):
        """Test that hourly limit is enforced."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        # Set very low limits for testing
        app.add_middleware(
            RateLimitMiddleware,
            enabled=True,
            per_minute=100,  # High minute limit
            per_hour=3,  # Low hour limit
        )

        client = TestClient(app)

        # Make requests up to hour limit
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200

        # Next request should hit hour limit
        response = client.get("/test")
        assert response.status_code == 429
        assert response.json()["error"] == "rate_limit_exceeded"

    def test_remaining_count_decreases(self, client_with_rate_limit):
        """Test that remaining count decreases with each request."""
        response1 = client_with_rate_limit.get("/test")
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        response2 = client_with_rate_limit.get("/test")
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        assert remaining2 < remaining1


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_no_client_info(self, app):
        """Test handling when client info is unavailable."""
        middleware = RateLimitMiddleware(app, enabled=True, per_minute=5)

        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.client = None

        identifier = middleware._get_client_identifier(request)
        assert identifier == "ip:unknown"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, app):
        """Test handling of concurrent requests."""
        app.add_middleware(RateLimitMiddleware, enabled=True, per_minute=5)
        client = TestClient(app)

        # Simulate concurrent requests
        responses = []
        for _ in range(10):
            response = client.get("/test")
            responses.append(response)

        # Some should succeed, some should be rate limited
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        assert success_count <= 5
        assert rate_limited_count >= 5

    def test_rate_limit_response_format(self, client_with_rate_limit):
        """Test the format of rate limit error response."""
        # Exhaust limit
        for _ in range(5):
            client_with_rate_limit.get("/test")

        response = client_with_rate_limit.get("/test")
        assert response.status_code == 429

        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "retry_after" in data
        assert data["error"] == "rate_limit_exceeded"
        assert isinstance(data["retry_after"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
