"""FastAPI application for Valerie Supplier Chatbot."""

import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from valerie.infrastructure import (
    CORRELATION_ID_HEADER,
    get_logger,
    get_observability,
    get_or_create_correlation_id,
    record_request,
    set_correlation_id,
)

from .routes import chat_router, health_router, webhooks_router
from .schemas import ErrorResponse
from .websocket import router as websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("api_startup", message="Starting Valerie Supplier Chatbot API...")

    # Initialize observability
    observability = get_observability()
    logger.info(
        "observability_ready",
        backend=type(observability._backend).__name__,
    )

    # Verify graph can be built
    try:
        from valerie.graph import build_graph

        graph = build_graph()
        logger.info("langgraph_initialized", nodes=len(graph.nodes))
    except Exception as e:
        logger.warning("langgraph_init_failed", error=str(e))
        logger.info("api_demo_mode", message="API will run in demo mode only")

    # Check LLM API key (Groq or Anthropic)
    try:
        import os
        from valerie.models import get_settings

        settings = get_settings()
        groq_key = os.getenv("VALERIE_GROQ_API_KEY")
        if groq_key:
            logger.info("api_full_mode", message="Groq API key configured (free tier)")
        elif settings.anthropic_api_key:
            logger.info("api_full_mode", message="Anthropic API key configured")
        else:
            logger.info("api_demo_mode", message="No LLM API key - running in demo mode")
    except Exception:
        logger.warning("settings_load_failed", message="Could not load settings")

    yield

    # Shutdown
    observability.flush()
    logger.info("api_shutdown", message="Shutting down Valerie Supplier Chatbot API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Valerie Supplier Chatbot API",
        description="""
## Aerospace Supplier Management Chatbot

REST API for the Valerie multi-agent chatbot system.

### Features
- **Chat Interface**: Natural language queries about suppliers
- **Supplier Search**: Direct search by process, certification, location
- **Compliance Checking**: Verify supplier certifications
- **Supplier Comparison**: Compare suppliers side-by-side
- **Multi-Agent Pipeline**: 15 specialized AI agents

### Authentication
API key authentication coming soon. Currently in demo mode.

### Rate Limits
- 60 requests per minute per IP
- 1000 requests per hour per IP
        """,
        version="2.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Add correlation ID to all requests."""
        # Get or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = get_or_create_correlation_id()
        else:
            set_correlation_id(correlation_id)

        # Track request timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        # Record metrics (skip /metrics and /health endpoints)
        skip_metrics = request.url.path.startswith(("/metrics", "/health"))
        if not skip_metrics:
            record_request(
                endpoint=request.url.path,
                method=request.method,
                status=response.status_code,
                duration=duration,
            )
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

        return response

    # Include routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(websocket_router)
    app.include_router(webhooks_router)

    # Prometheus metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(
            "unhandled_exception",
            method=request.method,
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal Server Error",
                details=[{"code": "INTERNAL_ERROR", "message": str(exc)}],
                timestamp=datetime.now(),
            ).model_dump(mode="json"),
        )

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "Valerie Supplier Chatbot API",
            "version": "2.2.0",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "status": "running",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("valerie.api.main:app", host="0.0.0.0", port=8000, reload=True)
