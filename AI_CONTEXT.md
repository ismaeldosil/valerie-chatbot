# AI_CONTEXT.md - Valerie Chatbot

This file provides guidance to AI assistant when working with this repository.

## Project Overview

**Valerie Chatbot** is a multi-domain AI chatbot platform built with LangGraph. The first domain implementation is for aerospace supplier management, integrating with Oracle Fusion Cloud ERP.

### Key Stats
- **Version**: 1.0.0
- **Tests**: 609 (79% coverage)
- **Agents**: 15 (10 core + 5 infrastructure)
- **LLM Providers**: 7

## Quick Start

```bash
# Install dependencies
uv sync

# Run with Ollama (free, local)
ollama serve &
ollama pull llama3.2
uv run python -m valerie.cli chat

# Run tests
uv run pytest tests/ -v

# Start API server
uv run uvicorn valerie.api.main:app --reload
```

## Architecture

### Multi-Agent System (15 Agents)

**Core Agents (10)** - `src/valerie/agents/`:
| Agent | File | Purpose |
|-------|------|---------|
| Orchestrator | `orchestrator.py` | Routes requests to agents |
| Intent Classifier | `intent_classifier.py` | Classifies user intent |
| Supplier Search | `supplier_search.py` | Finds suppliers |
| Compliance | `compliance.py` | Validates certifications |
| Comparison | `comparison.py` | Compares suppliers |
| Risk Assessment | `risk_assessment.py` | Evaluates supplier risk |
| Process Expertise | `process_expertise.py` | Technical Q&A |
| Oracle Integration | `oracle_integration.py` | ERP API integration |
| Response Generation | `response_generation.py` | Formats responses |
| Memory Context | `memory_context.py` | Conversation context |

**Infrastructure Agents (5)** - `src/valerie/infrastructure/`:
| Agent | File | Purpose |
|-------|------|---------|
| Guardrails | `guardrails.py` | Security validation |
| HITL | `hitl.py` | Human-in-the-loop |
| Fallback | `fallback.py` | Error recovery |
| Evaluation | `evaluation.py` | LLM-as-Judge |
| Observability | `observability.py` | Tracing/metrics |

### LLM Providers (7)

Located in `src/valerie/llm/`:

| Provider | File | Cost | Use Case |
|----------|------|------|----------|
| Ollama | `ollama.py` | Free | Local development |
| Groq | `groq.py` | Free | Fast cloud inference |
| Gemini | `gemini.py` | Free | 2M context window |
| Anthropic | `anthropic.py` | Paid | Production quality |
| AWS Bedrock | `bedrock.py` | Paid | AWS deployments |
| Azure OpenAI | `azure_openai.py` | Paid | Azure deployments |
| LightLLM | `lightllm.py` | Free | On-premise GPU |

### Multi-Domain Architecture

```
src/valerie/
├── core/
│   ├── domain/          # Domain abstractions
│   │   ├── base.py      # BaseDomain class
│   │   └── registry.py  # DomainRegistry
│   └── state/           # State management
│       ├── core.py      # CoreState
│       └── composite.py # CompositeState
├── domains/
│   └── supplier/        # Supplier domain implementation
│       ├── domain.py
│       ├── intents.py
│       └── state.py
└── graph/
    ├── builder.py       # LangGraph builder
    └── multi_domain.py  # Multi-domain graph
```

## Common Commands

### Development
```bash
# Run CLI chat
uv run python -m valerie.cli chat

# Run API server
uv run uvicorn valerie.api.main:app --reload --port 8000

# Run demo UI
uv run streamlit run demo/app.py
```

### Testing
```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# With coverage
uv run pytest tests/ --cov=src/valerie --cov-report=term-missing

# Specific test file
uv run pytest tests/unit/test_agents.py -v
```

### Code Quality
```bash
# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Type check
uv run mypy src/valerie/
```

### Docker
```bash
# Development
docker-compose -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Variables

### Required for Production
```bash
# LLM Provider (choose one)
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx

# Security
JWT_SECRET_KEY=your-secret-key
```

### Optional
```bash
# Provider fallback
VALERIE_LLM_FALLBACK=ollama,groq,anthropic

# Free providers
VALERIE_GROQ_API_KEY=gsk_xxx
VALERIE_GEMINI_API_KEY=AIzaSy_xxx

# Enterprise providers
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxx
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://...

# Redis (optional)
VALERIE_REDIS_URL=redis://localhost:6379

# Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxx
```

## Project Structure

```
valerie-chatbot/
├── src/valerie/
│   ├── agents/          # 10 core agents
│   ├── infrastructure/  # 5 infrastructure agents
│   ├── llm/            # 7 LLM providers
│   ├── api/            # FastAPI routes
│   ├── graph/          # LangGraph builder
│   ├── models/         # Pydantic models
│   ├── middleware/     # Auth, rate limiting
│   ├── core/           # Domain abstractions
│   ├── domains/        # Domain implementations
│   └── cli.py          # CLI interface
├── tests/
│   ├── unit/           # Unit tests (570)
│   ├── api/            # API tests (31)
│   └── integration/    # Integration tests (8)
├── config/
│   ├── model-registry.yaml  # LLM configuration
│   ├── grafana/            # Grafana dashboards
│   └── prometheus/         # Prometheus alerts
├── docker/
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── demo/               # Streamlit demo UI
├── docs/               # Documentation
└── ../valerie-docs/     # Development docs (external, sibling folder)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/valerie/graph/builder.py` | LangGraph state machine |
| `src/valerie/llm/factory.py` | Provider factory with fallback |
| `src/valerie/models/state.py` | ChatState definition |
| `config/model-registry.yaml` | Model tier configuration |
| `src/valerie/api/main.py` | FastAPI application |
| `src/valerie/api/websocket.py` | WebSocket streaming |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat` | POST | Send chat message |
| `/api/v1/sessions/{id}` | GET | Get session |
| `/api/v1/sessions/{id}` | DELETE | Delete session |
| `/ws/chat/{session_id}` | WS | WebSocket streaming |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Swagger UI |

## Testing Strategy

- **Unit Tests**: Each agent, provider, and utility
- **API Tests**: All REST endpoints
- **Integration Tests**: Full pipeline flows
- **Coverage Target**: 70%+

## Deployment Options

1. **Local**: `uv run uvicorn valerie.api.main:app`
2. **Docker**: `docker-compose up`
3. **Railway**: Push to main branch
4. **Kubernetes**: See `valerie-infrastructure/` repo

## Related Repositories

- `valerie-infrastructure/` - Terraform, Kubernetes, Helm charts
- `oracle-fusion-mock-server/` - Oracle API mock for testing
- `../valerie-docs/templates/` - Domain customization templates

## Domain Customization

To adapt for a new domain:
1. Copy `../valerie-docs/templates/new_domain/` to `src/valerie/domains/<name>/`
2. Define intents in `intents.py`
3. Define state in `state.py`
4. Implement domain in `domain.py`
5. Update prompts in `../valerie-docs/prompts/`

See `docs/DOMAIN_CUSTOMIZATION_GUIDE.md` for details.

## Coding Standards

- Python 3.11+
- Type hints required
- Ruff for formatting
- Mypy for type checking
- Pydantic v2 for models
- Async/await for I/O

## Common Issues

### "No LLM provider available"
```bash
# Start Ollama
ollama serve
ollama pull llama3.2
```

### "Redis connection refused"
```bash
# Run without Redis (uses in-memory)
# Or start Redis
docker run -d -p 6379:6379 redis:alpine
```

### "Oracle connection failed"
```bash
# Start mock server
cd ../oracle-fusion-mock-server && npm start
```

## Documentation

- `README.md` - Project overview
- `DEPLOYMENT.md` - Deployment guide
- `ENVIRONMENT.md` - Environment variables
- `docs/components.md` - Component details
- `docs/system-architecture.md` - Architecture
- `docs/llm-configuration.md` - LLM setup
- `docs/user-guide.md` - User guide
