"""
Example usage of RateLimitMiddleware with FastAPI.

Run this example:
    python example_usage.py

Then test with curl:
    # Make requests
    curl http://localhost:8000/test

    # Check headers
    curl -v http://localhost:8000/test

    # Test tenant-based limiting
    curl -H "X-Tenant-ID: tenant-1" http://localhost:8000/test

    # Trigger rate limit (make 6+ requests quickly)
    for i in {1..10}; do curl http://localhost:8000/test; echo ""; done
"""

import os

import uvicorn
from fastapi import FastAPI, Request

from valerie.middleware import RateLimitMiddleware

# Create FastAPI app
app = FastAPI(title="Rate Limit Example")


# Add rate limiting middleware with low limits for easy testing
app.add_middleware(
    RateLimitMiddleware,
    enabled=True,
    per_minute=5,  # Only 5 requests per minute for demo
    per_hour=20,  # 20 requests per hour
    redis_url=os.getenv("REDIS_URL"),  # Optional Redis backend
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Rate Limiting Example",
        "endpoints": {
            "/test": "Test endpoint (rate limited)",
            "/health": "Health check (always works)",
        },
        "limits": {
            "per_minute": 5,
            "per_hour": 20,
        },
    }


@app.get("/test")
async def test_endpoint(request: Request):
    """
    Test endpoint that is rate limited.

    Try making multiple requests quickly to trigger rate limiting.
    """
    # Get rate limit info from headers (added by middleware)
    return {
        "message": "Success! Request processed.",
        "tip": "Make 6+ requests quickly to see rate limiting in action",
        "client": request.client.host if request.client else "unknown",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint (not rate limited in this example)."""
    return {"status": "healthy"}


@app.get("/tenant-demo")
async def tenant_demo(request: Request):
    """
    Demo endpoint showing tenant-based rate limiting.

    Test with different tenant headers:
        curl -H "X-Tenant-ID: tenant-1" http://localhost:8000/tenant-demo
        curl -H "X-Tenant-ID: tenant-2" http://localhost:8000/tenant-demo
    """
    tenant_id = request.headers.get("X-Tenant-ID", "none")

    return {
        "message": f"Request from tenant: {tenant_id}",
        "tip": "Each tenant has separate rate limits. Try different X-Tenant-ID headers.",
    }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Rate Limiting Example Server")
    print("=" * 70)
    print("\nLimits:")
    print("  - 5 requests per minute per client")
    print("  - 20 requests per hour per client")
    print("\nTest commands:")
    print("  # Normal request")
    print("  curl http://localhost:8000/test")
    print("\n  # See rate limit headers")
    print("  curl -v http://localhost:8000/test")
    print("\n  # Trigger rate limit (make 6+ requests)")
    print("  for i in {1..10}; do curl http://localhost:8000/test; echo ''; done")
    print("\n  # Test tenant-based limiting")
    print("  curl -H 'X-Tenant-ID: tenant-1' http://localhost:8000/tenant-demo")
    print("  curl -H 'X-Tenant-ID: tenant-2' http://localhost:8000/tenant-demo")
    print("\n" + "=" * 70 + "\n")

    # Run the server
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
