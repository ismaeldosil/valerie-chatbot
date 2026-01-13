# Valerie Chatbot - Production Dockerfile
# Multi-stage build for optimized image size

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim as runtime

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r valerie && useradd -r -g valerie valerie

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY demo/ ./demo/
COPY config/ ./config/

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# LLM Configuration
# Uses Groq free tier (30 req/min, 14,400 req/day)
# Set VALERIE_GROQ_API_KEY in Railway environment variables
# Get free API key at: https://console.groq.com/
ENV VALERIE_LLM_PROVIDER=groq
ENV VALERIE_GROQ_MODEL=llama-3.3-70b-versatile

# Service URLs (optional - demo mode works without these)
# ENV VALERIE_REDIS_URL=redis://redis:6379
# ENV VALERIE_ORACLE_BASE_URL=http://oracle-mock:3000

# Expose port (Railway sets PORT dynamically)
EXPOSE 8000

# Copy run.py for Railway deployment
COPY run.py .

# Switch to non-root user
USER valerie

# Run the API using Python script that handles PORT env var
CMD ["python", "run.py"]
