"""Health check endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter

from ..schemas import HealthResponse, ReadinessResponse, ServiceHealth

router = APIRouter(tags=["Health"])

# Version from package
VERSION = "2.2.0"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the overall health status of the service and its dependencies.
    """
    services = []
    overall_status = "healthy"

    # Check LangGraph availability
    try:
        start = time.time()
        from valerie.graph import build_graph

        graph = build_graph()
        latency = (time.time() - start) * 1000
        services.append(
            ServiceHealth(
                name="langgraph",
                status="healthy",
                latency_ms=latency,
                message=f"Graph compiled with {len(graph.nodes)} nodes",
            )
        )
    except Exception as e:
        services.append(ServiceHealth(name="langgraph", status="unhealthy", message=str(e)))
        overall_status = "degraded"

    # Check Redis (optional)
    try:
        from valerie.models import get_settings

        settings = get_settings()
        if settings.redis_url:
            services.append(
                ServiceHealth(
                    name="redis",
                    status="healthy" if settings.redis_url else "skipped",
                    message="Redis configured" if settings.redis_url else "Redis not configured",
                )
            )
    except Exception as e:
        services.append(ServiceHealth(name="redis", status="degraded", message=str(e)))

    # Check API key configuration
    try:
        from valerie.models import get_settings

        settings = get_settings()
        api_key_status = "configured" if settings.anthropic_api_key else "not configured"
        services.append(
            ServiceHealth(
                name="anthropic_api",
                status="healthy" if settings.anthropic_api_key else "degraded",
                message=f"API key {api_key_status}",
            )
        )
        if not settings.anthropic_api_key:
            overall_status = "degraded"
    except Exception as e:
        services.append(ServiceHealth(name="anthropic_api", status="unhealthy", message=str(e)))

    return HealthResponse(
        status=overall_status, version=VERSION, timestamp=datetime.now(), services=services
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint.

    Returns whether the service is ready to accept requests.
    Used by Kubernetes/load balancers for traffic routing.
    """
    checks = {}

    # Check if graph can be built
    try:
        from valerie.graph import build_graph

        build_graph()
        checks["graph"] = True
    except Exception:
        checks["graph"] = False

    # Check settings can be loaded
    try:
        from valerie.models import get_settings

        get_settings()
        checks["config"] = True
    except Exception:
        checks["config"] = False

    # Check demo mode availability (always available)
    checks["demo_mode"] = True

    ready = all(checks.values())

    return ReadinessResponse(ready=ready, checks=checks)


@router.get("/live")
async def liveness_check() -> dict:
    """
    Liveness check endpoint.

    Simple check to verify the service is running.
    Used by Kubernetes for pod restarts.
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}
