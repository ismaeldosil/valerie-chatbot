# Valerie Supplier Chatbot - Deployment Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Development Deployment](#development-deployment)
4. [Production Deployment](#production-deployment)
5. [LLM Provider Configuration](#llm-provider-configuration)
6. [Observability Stack](#observability-stack)
7. [Scaling & High Availability](#scaling--high-availability)
8. [Troubleshooting](#troubleshooting)
9. [Backup & Recovery](#backup--recovery)

---

## Quick Start

### Development (5 minutes)

```bash
# Clone and enter directory
cd valerie-chatbot

# Start all services (API + Redis + Ollama + Oracle Mock)
docker-compose -f docker-compose.dev.yml up -d

# Wait for Ollama to download the model (~2-3 minutes first time)
docker-compose -f docker-compose.dev.yml logs -f ollama

# Test the API
curl http://localhost:8000/health

# Open Demo UI
open http://localhost:8501
```

### Production (10 minutes)

```bash
# Copy and configure environment
cp .env.production.example .env.production
# Edit .env.production with your API keys

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Verify all services are healthy
docker-compose -f docker-compose.prod.yml ps

# Access services
# API:      http://localhost:8000
# Grafana:  http://localhost:3001 (admin/valerie123)
# Prometheus: http://localhost:9090
```

---

## Architecture Overview

```
                                    ┌─────────────────┐
                                    │    Clients      │
                                    │  (Web/Mobile)   │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │     Nginx       │
                                    │  Load Balancer  │
                                    │     :8000       │
                                    └────────┬────────┘
                         ┌───────────────────┼───────────────────┐
                         │                   │                   │
                    ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
                    │  API-1  │         │  API-2  │         │  API-3  │
                    │ FastAPI │         │ FastAPI │         │ FastAPI │
                    └────┬────┘         └────┬────┘         └────┬────┘
                         │                   │                   │
                         └───────────────────┼───────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
         ┌────▼────┐                    ┌────▼────┐                   ┌─────▼─────┐
         │  Redis  │                    │   LLM   │                   │  Oracle   │
         │ :6379   │                    │ Provider│                   │  Fusion   │
         │(Sessions)│                   │         │                   │  Cloud    │
         └─────────┘                    └─────────┘                   └───────────┘

                         Observability Stack
         ┌─────────────────────────────────────────────────┐
         │  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
         │  │Prometheus │  │  Grafana  │  │ Langfuse  │   │
         │  │  :9090    │  │   :3001   │  │   :3002   │   │
         │  └───────────┘  └───────────┘  └───────────┘   │
         └─────────────────────────────────────────────────┘
```

---

## Development Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Start development environment with hot-reload
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f api

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Option 2: Local Python + Docker Services

```bash
# Start only infrastructure services
docker-compose -f docker-compose.dev.yml up -d redis ollama oracle-mock

# Run API locally with hot-reload
cd valerie-chatbot
uv run uvicorn valerie.api.main:app --reload --port 8000

# Run demo UI locally
uv run streamlit run demo/app.py
```

### Development Environment Variables

Create `.env` file:

```bash
# LLM - Use Ollama for free local inference
VALERIE_LLM_PROVIDER=ollama
VALERIE_USE_PAID_LLM=false
VALERIE_OLLAMA_BASE_URL=http://localhost:11434

# Or use Groq for free cloud inference
# VALERIE_LLM_PROVIDER=groq
# VALERIE_GROQ_API_KEY=gsk_xxx

# Tracing with LangSmith (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxx
LANGCHAIN_PROJECT=valerie-dev
```

---

## Production Deployment

### Prerequisites

1. Docker and Docker Compose installed
2. At least 8GB RAM available
3. LLM provider API key (Anthropic recommended)
4. (Optional) Domain name and SSL certificate

### Step 1: Configure Environment

```bash
# Copy template
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

**Required variables:**

```bash
# LLM Provider (choose one)
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx

# Security
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Langfuse (for LLM tracing)
LANGFUSE_NEXTAUTH_SECRET=$(openssl rand -hex 32)
LANGFUSE_SALT=$(openssl rand -hex 32)
```

### Step 2: Start Production Stack

```bash
# Basic production (without Langfuse)
docker-compose -f docker-compose.prod.yml up -d

# With Langfuse tracing
docker-compose -f docker-compose.prod.yml --profile with-langfuse up -d

# With Oracle Mock (for testing)
docker-compose -f docker-compose.prod.yml --profile with-mock up -d
```

### Step 3: Verify Deployment

```bash
# Check all services are running
docker-compose -f docker-compose.prod.yml ps

# Expected output:
# NAME                    STATUS
# valerie-nginx           Up (healthy)
# valerie-api-1           Up (healthy)
# valerie-api-2           Up (healthy)
# valerie-api-3           Up (healthy)
# valerie-redis-prod      Up (healthy)
# valerie-prometheus-prod Up (healthy)
# valerie-grafana-prod    Up (healthy)

# Test API
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

### Step 4: Configure Langfuse (Optional)

1. Open http://localhost:3002
2. Create admin account
3. Create new project
4. Copy API keys to `.env.production`:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
```

5. Restart API containers:

```bash
docker-compose -f docker-compose.prod.yml restart api
```

---

## LLM Provider Configuration

### Provider Priority

The system uses a fallback chain:

1. **Primary**: Configured via `VALERIE_LLM_PROVIDER`
2. **Fallback 1**: Groq (if API key provided)
3. **Fallback 2**: Ollama (if available)

### Anthropic (Recommended for Production)

```bash
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx
VALERIE_USE_PAID_LLM=true
```

### AWS Bedrock

```bash
VALERIE_LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_DEFAULT_REGION=us-east-1
```

### Azure OpenAI

```bash
VALERIE_LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-turbo
```

### Groq (Free Tier Available)

```bash
VALERIE_LLM_PROVIDER=groq
VALERIE_GROQ_API_KEY=gsk_xxx
```

### Ollama (Free, Local)

```bash
VALERIE_LLM_PROVIDER=ollama
VALERIE_OLLAMA_BASE_URL=http://ollama:11434
VALERIE_USE_PAID_LLM=false
```

---

## Observability Stack

### Accessing Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3001 | admin / valerie123 |
| Prometheus | http://localhost:9090 | - |
| Langfuse | http://localhost:3002 | Create on first access |

### Available Dashboards

1. **Valerie Overview** - Request rates, latency, errors, sessions
2. **LLM Providers** - Provider status, token usage, costs
3. **Agents** - Per-agent performance metrics

### Key Metrics

```promql
# Request rate
sum(rate(valerie_requests_total[1m]))

# Error rate
sum(rate(valerie_requests_total{status=~"5.."}[5m])) / sum(rate(valerie_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, sum(rate(valerie_request_duration_seconds_bucket[5m])) by (le))

# LLM token usage
sum(rate(valerie_llm_tokens_total[1h])) by (provider, direction)
```

### Alert Rules

Pre-configured alerts in `config/prometheus/alert-rules.yml`:

- API down for >1 minute
- Error rate >5% for >5 minutes
- P95 latency >10 seconds
- LLM provider unavailable
- Redis connection lost

---

## Scaling & High Availability

### Horizontal Scaling

```bash
# Scale API replicas
docker-compose -f docker-compose.prod.yml up -d --scale api=5

# Or modify docker-compose.prod.yml:
# deploy:
#   replicas: 5
```

### Resource Limits

Default limits per container:

| Service | CPU | Memory |
|---------|-----|--------|
| API | 1.0 | 2G |
| Redis | 0.5 | 512M |
| Prometheus | 0.5 | 1G |
| Grafana | 0.5 | 512M |

### Load Balancing

Nginx uses `least_conn` algorithm:
- Requests go to the replica with fewest active connections
- Failed replicas are removed from rotation after 3 failures
- Automatic retry on upstream errors

---

## Troubleshooting

### Common Issues

#### API containers keep restarting

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Common causes:
# 1. Missing API keys
# 2. Redis not ready
# 3. Invalid JWT_SECRET_KEY
```

#### Redis connection refused

```bash
# Verify Redis is running
docker-compose -f docker-compose.prod.yml ps redis

# Check Redis logs
docker-compose -f docker-compose.prod.yml logs redis

# Test connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

#### Ollama model not loading

```bash
# Check Ollama logs
docker-compose -f docker-compose.dev.yml logs ollama

# Manually pull model
docker-compose -f docker-compose.dev.yml exec ollama ollama pull llama3.2

# Verify model is available
docker-compose -f docker-compose.dev.yml exec ollama ollama list
```

#### High memory usage

```bash
# Check container stats
docker stats

# Reduce Redis memory
# In docker-compose.prod.yml, modify Redis command:
# command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Detailed health with components
curl http://localhost:8000/health/detailed

# Prometheus targets
curl http://localhost:9090/api/v1/targets
```

---

## Backup & Recovery

### Session Data (Redis)

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker cp valerie-redis-prod:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb

# Restore
docker cp ./backups/redis-20241220.rdb valerie-redis-prod:/data/dump.rdb
docker-compose -f docker-compose.prod.yml restart redis
```

### Prometheus Data

```bash
# Backup (snapshot API)
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Data is stored in prometheus-prod-data volume
```

### Grafana Dashboards

Dashboards are provisioned from `config/grafana/dashboards/` - no backup needed.

### Langfuse Data

```bash
# Backup PostgreSQL
docker-compose -f docker-compose.prod.yml exec langfuse-db \
  pg_dump -U langfuse langfuse > ./backups/langfuse-$(date +%Y%m%d).sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T langfuse-db \
  psql -U langfuse langfuse < ./backups/langfuse-20241220.sql
```

---

## Security Checklist

- [ ] Change default Grafana password (`GRAFANA_ADMIN_PASSWORD`)
- [ ] Generate strong `JWT_SECRET_KEY` (256-bit)
- [ ] Generate strong `LANGFUSE_NEXTAUTH_SECRET` and `LANGFUSE_SALT`
- [ ] Restrict Prometheus/Grafana access to internal networks
- [ ] Enable TLS/SSL with reverse proxy (nginx/traefik)
- [ ] Set `AUTH_DISABLE_SIGNUP=true` for Langfuse after initial setup
- [ ] Review and restrict CORS origins
- [ ] Enable rate limiting in production

---

## Support

- **Documentation**: `/docs` endpoint on the API
- **Health Status**: `/health` endpoint
- **Metrics**: `/metrics` endpoint (Prometheus format)
- **Issues**: https://github.com/ismaeldosil/valerie-chatbot/issues
