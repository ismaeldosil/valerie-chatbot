# Valerie Chatbot v1.0.0

[![CI](https://github.com/ismaeldosil/valerie-chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/ismaeldosil/valerie-chatbot/actions/workflows/ci.yml)
[![Deploy](https://github.com/ismaeldosil/valerie-chatbot/actions/workflows/deploy-railway.yml/badge.svg)](https://github.com/ismaeldosil/valerie-chatbot/actions/workflows/deploy-railway.yml)
[![codecov](https://codecov.io/gh/ismaeldosil/valerie-chatbot/graph/badge.svg)](https://codecov.io/gh/ismaeldosil/valerie-chatbot)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: 609 passed](https://img.shields.io/badge/tests-609%20passed-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Multi-domain AI chatbot platform** with pluggable business domains. Built with LangGraph, FastAPI, and integrated with Oracle Fusion ERP.

## What's New in v1.0.0

- **7 LLM Providers**: Ollama, Groq, Gemini (free), Anthropic, AWS Bedrock, Azure OpenAI, LightLLM
- **Multi-Domain Architecture**: Pluggable domain system for multiple business areas
- **Enterprise Security**: JWT authentication, rate limiting, Redis sessions
- **Observability**: Structlog, Prometheus metrics, LangSmith/Langfuse tracing
- **609 Tests**: Comprehensive test coverage with Codecov integration

## Features

- **Multi-Domain Architecture**: Pluggable business domains (supplier, client, inventory, etc.)
- **15 Specialized Agents**: 10 core + 5 infrastructure agents
- **7 LLM Providers**: Ollama, Groq, Gemini (free) | Anthropic, Bedrock, Azure OpenAI (paid) | LightLLM (on-premise)
- **LangGraph Orchestration**: Supervisor pattern with conditional routing
- **REST API**: FastAPI with OpenAPI documentation
- **WebSocket Streaming**: Real-time response streaming
- **Demo UI**: Streamlit interface for demonstrations
- **Human-in-the-Loop**: ITAR decisions and high-risk queries require approval
- **Defense-in-Depth**: 4-layer guardrails (regex, ML, LLM, human)
- **Circuit Breaker**: Graceful degradation on failures
- **Docker Ready**: Production-ready containerization
- **CI/CD**: GitHub Actions workflows

## LLM Configuration

### Multi-LLM Support

The system features a **centralized model registry** (`config/model-registry.yaml`) that serves as the single source of truth for all LLM configurations. This enables:

- **7 LLM Providers**: Free (Ollama, Groq, Gemini), Paid (Anthropic, Bedrock, Azure), On-Premise (LightLLM)
- **4 Model Tiers**: default (balanced), fast (speed), quality (best), evaluation (judging)
- **Easy Provider Toggle**: Switch between providers with environment variables
- **Per-Agent Optimization**: Different agents use different model tiers based on their needs
- **Automatic Fallback**: Graceful degradation if primary provider fails

| Provider | Type | Cost | Context | Use Case |
|----------|------|------|---------|----------|
| **Ollama** | Local | Free | Varies | Development, testing |
| **Groq** | Cloud | Free | 32K | Fast demos, prototypes |
| **Gemini** | Cloud | Free | 2M | Long context, production |
| **Anthropic** | Cloud | Paid | 200K | Production, high quality |
| **AWS Bedrock** | Cloud | Paid | Varies | AWS-native deployments |
| **Azure OpenAI** | Cloud | Paid | 128K | Azure-native deployments |
| **LightLLM** | On-Premise | Free | Varies | GPU clusters, self-hosted |

### Model Tiers

Different agents use different model tiers based on their computational needs:

| Tier | Model Examples | Use Case | Agents |
|------|---------------|----------|--------|
| **Quality** | Claude Opus 4, Llama 3.2:70b | Complex reasoning | Orchestrator, Risk Assessment, Compliance |
| **Default** | Claude Sonnet 4, Llama 3.3 70b | Balanced | Supplier Search, Process Expertise |
| **Fast** | Claude Haiku, Llama 3.2:3b | Speed critical | Intent Classifier, Guardrails |
| **Evaluation** | Claude Sonnet 3.5, Llama 3.3 70b | LLM-as-Judge | Evaluation Agent |

### Quick Setup: Free LLM with Ollama

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Download required models
ollama pull llama3.2          # Default tier
ollama pull llama3.2:3b       # Fast tier (optional)
ollama pull llama3.2:70b      # Quality tier (optional)

# Start Ollama server
ollama serve

# Configure the chatbot (ollama is default)
export VALERIE_LLM_PROVIDER=ollama
```

### Quick Setup: Free Cloud LLM with Groq

```bash
# Get free API key at https://console.groq.com/
export VALERIE_GROQ_API_KEY=gsk_xxx...
export VALERIE_LLM_PROVIDER=groq
```

### Quick Setup: Free Cloud LLM with Gemini

```bash
# Get free API key at https://aistudio.google.com/app/apikey
export VALERIE_GEMINI_API_KEY=AIzaSy_xxx...
export VALERIE_LLM_PROVIDER=gemini
```

### Quick Setup: Paid LLM with Anthropic

```bash
# Get API key at https://console.anthropic.com/
export VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx...
export VALERIE_LLM_PROVIDER=anthropic
```

### Switching Providers

You can switch providers in several ways:

**1. Environment Variable (recommended)**

```bash
# Free providers
export VALERIE_LLM_PROVIDER=ollama   # Local, free
export VALERIE_LLM_PROVIDER=groq     # Cloud, free (30 req/min)
export VALERIE_LLM_PROVIDER=gemini   # Cloud, free (15 req/min, 2M context)

# Paid providers
export VALERIE_LLM_PROVIDER=anthropic    # Cloud, paid
export VALERIE_LLM_PROVIDER=bedrock      # AWS, paid
export VALERIE_LLM_PROVIDER=azure_openai # Azure, paid

# On-premise
export VALERIE_LLM_PROVIDER=lightllm     # GPU cluster
```

**2. Demo UI Provider Selector**

The Streamlit demo includes a radio button selector in the sidebar:
- Ollama (Free - Local)
- Groq (Free - Cloud)
- Gemini (Free - Cloud)
- Anthropic (Paid)

**3. Programmatic Access**

```python
from valerie.models import get_model_registry

# Get the registry
registry = get_model_registry()

# Get model for specific provider and tier
model = registry.get_model("ollama", "fast")  # llama3.2:3b

# Get model for specific agent (auto-selects tier)
model = registry.get_model_for_agent("orchestrator")  # Uses quality tier

# Get parameters for agent
params = registry.get_parameters_for_agent("intent_classifier")
# Returns: {"temperature": 0.0, "max_tokens": 512}

# Check current provider
if registry.is_using_paid_llm:
    print("Using paid Anthropic")
else:
    print("Using free LLM")
```

### Centralized Model Registry

All model configurations are defined in `config/model-registry.yaml`. To change models globally:

**Edit the registry file:**

```yaml
providers:
  ollama:
    models:
      default: "llama3.2"          # Change to llama3.1 or other model
      fast: "llama3.2:3b"
      quality: "llama3.2:70b"

agent_assignments:
  quality:                          # High-quality models for critical agents
    model_tier: "quality"
    agents:
      - orchestrator
      - risk_assessment
      - compliance_validation

  fast:                             # Fast models for speed-critical agents
    model_tier: "fast"
    agents:
      - intent_classifier
      - guardrails
```

This ensures consistency across the entire codebase without modifying code.

For detailed information on the LLM configuration system, see [docs/llm-configuration.md](docs/llm-configuration.md).

## Documentation

- [User Guide](docs/user-guide.md) - Getting started and usage instructions
- [System Architecture](docs/system-architecture.md) - High-level architecture and design
- [Multi-Domain Architecture](docs/multi-domain-architecture.md) - **How to add new domains**
- [Component Documentation](docs/components.md) - Detailed component descriptions
- [LLM Configuration](docs/llm-configuration.md) - Model registry and provider management

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│   │Guardrails│  │   HITL   │  │ Fallback │  │Evaluation│  │Observab. │ │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                           DOMAIN LAYER (v3.0)                            │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                      Domain Registry                             │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│   │   │  Supplier   │  │   Client    │  │  Inventory  │  ...        │   │
│   │   │   Domain    │  │   Domain    │  │   Domain    │             │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   User → Guardrails → Domain Classifier → Intent Classifier             │
│                                              │                           │
│        ┌──────────────┬──────────────┬──────┴──────┬──────────────┐     │
│        ▼              ▼              ▼             ▼              ▼     │
│   ┌─────────┐   ┌──────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐ │
│   │ Search  │   │Compliance│  │ Comparison│  │  Risk   │  │ Process  │ │
│   │         │   │          │  │           │  │Assessment│  │Expertise │ │
│   └─────────┘   └──────────┘  └───────────┘  └─────────┘  └──────────┘ │
│        │              │              │             │              │     │
│        └──────────────┴──────────────┴──────┬──────┴──────────────┘     │
│                                             ▼                           │
│   ┌─────────────┐  ┌─────────────────────────────────────┐              │
│   │   Memory    │  │      Response Generation           │              │
│   │   Context   │  │                                    │              │
│   └─────────────┘  └────────────────┬────────────────────┘              │
│                                     ▼                                   │
│                             Final Response → User                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and start all services
cd valerie-chatbot
docker-compose up -d

# Access points:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Demo UI: http://localhost:8501
```

### Option 2: Local Development

```bash
# Setup
cd valerie-chatbot
./install.sh

# Configure
cp .env.example .env
# Edit .env with your API keys (or use free Ollama - no key needed)

# For free local LLM (default - no API key needed)
export VALERIE_LLM_PROVIDER=ollama
ollama pull llama3.2

# OR for free cloud LLM
export VALERIE_LLM_PROVIDER=groq
export VALERIE_GROQ_API_KEY=gsk_xxx...

# OR for paid cloud LLM
export VALERIE_USE_PAID_LLM=true
export VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx...

# Run API
source venv/bin/activate
uvicorn valerie.api.main:app --reload

# Run Demo (in another terminal)
cd demo && streamlit run app.py
```

### Option 3: CLI Only

```bash
source venv/bin/activate
python -m valerie.cli chat
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check with service status |
| `/ready` | GET | Readiness check for K8s |
| `/live` | GET | Liveness check |
| `/docs` | GET | Swagger UI documentation |
| `/api/v1/chat` | POST | Send chat message |
| `/api/v1/sessions/{id}` | GET | Get session details |
| `/api/v1/sessions/{id}` | DELETE | Delete session |
| `/api/v1/suppliers/search` | POST | Direct supplier search |
| `/ws/chat/{session_id}` | WS | WebSocket for streaming |
| `/webhooks/slack` | POST | Slack webhook integration |
| `/webhooks/teams` | POST | MS Teams webhook integration |
| `/webhooks/generic/{channel}` | POST | Generic webhook for custom integrations |
| `/webhooks/health` | GET | Webhook endpoints health check |

### Example: Chat Request

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find heat treatment suppliers"}'
```

### Example: Supplier Search

```bash
curl -X POST http://localhost:8000/api/v1/suppliers/search \
  -H "Content-Type: application/json" \
  -d '{"processes": ["heat_treatment"], "certifications": ["Nadcap"]}'
```

## Demo UI

The Streamlit demo provides a visual interface for testing:

```bash
cd demo
streamlit run app.py
```

**Features:**
- Chat interface with message history
- Real-time agent activity panel
- Pre-built demo scenarios (Search, Compare, Risk, ITAR, Blocked)
- **LLM Provider Selector**: Switch between Ollama/Groq/Anthropic with radio buttons
- **Live Mode Toggle**: Use real LLMs or mock responses
- Works without API key (demo mode with mock responses)

## Agents

### Core Agents (10)

| # | Agent | Purpose |
|---|-------|---------|
| 1 | **Orchestrator** | Central coordinator, routes requests |
| 2 | **Intent Classifier** | Classifies intents, extracts entities |
| 3 | **Supplier Search** | Finds and ranks suppliers |
| 4 | **Compliance Validation** | Verifies certifications (Nadcap, AS9100, ITAR) |
| 5 | **Supplier Comparison** | Multi-dimension supplier comparison |
| 6 | **Oracle Fusion Integration** | ERP data gateway |
| 7 | **Process Expertise** | Technical SME for surface finishing |
| 8 | **Risk Assessment** | 6-dimension risk scoring |
| 9 | **Response Generation** | Natural language formatting |
| 10 | **Memory & Context** | Conversation state management |

### Infrastructure Agents (5)

| # | Agent | Purpose |
|---|-------|---------|
| 11 | **Guardrails** | 4-layer defense (PII, injection, ITAR) |
| 12 | **HITL** | Human-in-the-loop with LangGraph interrupt() |
| 13 | **Fallback** | Circuit breaker, graceful degradation |
| 14 | **Evaluation** | LLM-as-Judge quality assessment |
| 15 | **Observability** | Tracing, metrics, logging |

## Project Structure

```
valerie-chatbot/
├── src/valerie/
│   ├── core/                   # Multi-domain framework (v3.0)
│   │   ├── domain/            # BaseDomain, DomainRegistry
│   │   └── state/             # CoreState, CompositeState
│   ├── domains/                # Pluggable business domains
│   │   └── supplier/          # Supplier domain implementation
│   │       ├── domain.py      # SupplierDomain class
│   │       ├── intents.py     # SupplierIntent enum
│   │       └── state.py       # SupplierStateExtension
│   ├── agents/                 # 10 core agents
│   ├── infrastructure/         # 5 infrastructure agents
│   ├── graph/                  # LangGraph graph builder
│   │   ├── builder.py         # Legacy single-domain
│   │   └── multi_domain.py    # Multi-domain aware graph
│   ├── models/                 # Pydantic models
│   │   └── config.py          # ModelRegistry class
│   ├── llm/                    # LLM provider abstraction (7 providers)
│   │   ├── factory.py         # Provider factory with fallback
│   │   ├── ollama.py          # Ollama (local, free)
│   │   ├── groq.py            # Groq (cloud, free)
│   │   ├── gemini.py          # Google Gemini (cloud, free)
│   │   ├── anthropic.py       # Anthropic Claude (cloud, paid)
│   │   ├── bedrock.py         # AWS Bedrock (cloud, paid)
│   │   ├── azure_openai.py    # Azure OpenAI (cloud, paid)
│   │   └── lightllm.py        # LightLLM (on-premise)
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # App factory
│   │   ├── schemas.py         # Request/response schemas
│   │   ├── websocket.py       # WebSocket support
│   │   └── routes/            # API routes
│   └── cli.py                 # Typer CLI
├── demo/                       # Streamlit demo UI
│   ├── app.py                 # Main UI with provider selector
│   ├── mock_responses.py
│   └── data/
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── api/                   # API tests
├── docs/
│   ├── multi-domain-architecture.md  # How to add new domains
│   ├── system-architecture.md
│   └── ...
├── config/
│   └── model-registry.yaml    # CENTRAL MODEL REGISTRY
├── scripts/                   # Deployment scripts
├── .github/workflows/         # CI/CD pipelines
├── Dockerfile                 # Production image
└── docker-compose.yml         # Container orchestration
```

## Testing

```bash
# Run all tests (609 tests)
PYTHONPATH=src pytest tests/ -v

# Run only unit tests
PYTHONPATH=src pytest tests/unit/ -v

# Run only API tests
PYTHONPATH=src pytest tests/api/ -v

# With coverage
PYTHONPATH=src pytest tests/ --cov=src --cov-report=term-missing
```

## Configuration

Environment variables (prefix: `VALERIE_`):

### LLM Provider Settings

All model names are defined in `config/model-registry.yaml`. Environment variables override the registry defaults.

| Variable | Description | Default |
|----------|-------------|---------|
| `VALERIE_LLM_PROVIDER` | Provider (ollama/groq/gemini/anthropic/bedrock/azure_openai/lightllm) | ollama |
| `VALERIE_LLM_FALLBACK` | Fallback chain (comma-separated) | ollama,groq,gemini,anthropic |
| `VALERIE_OLLAMA_BASE_URL` | Ollama server URL | http://localhost:11434 |
| `VALERIE_GROQ_API_KEY` | Groq API key | (required for groq) |
| `VALERIE_GEMINI_API_KEY` | Gemini API key | (required for gemini) |
| `VALERIE_ANTHROPIC_API_KEY` | Anthropic API key | (required for anthropic) |
| `AWS_ACCESS_KEY_ID` | AWS credentials for Bedrock | (required for bedrock) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | (required for azure) |
| `VALERIE_LIGHTLLM_BASE_URL` | LightLLM server URL | http://localhost:8080 |

### Model Registry Configuration

The `config/model-registry.yaml` file defines:
- **Provider models**: Which models each provider uses for each tier
- **Agent assignments**: Which agents use which tier (quality/default/fast/evaluation)
- **Model parameters**: Temperature, max_tokens, timeout for each tier
- **Agent overrides**: Custom parameters for specific agents
- **Environment configs**: Different settings for dev/staging/production

To change models globally, edit `config/model-registry.yaml` instead of environment variables.

### Other Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `VALERIE_TEMPERATURE` | LLM temperature | 0.1 |
| `VALERIE_MAX_TOKENS` | Max tokens per request | 4096 |
| `VALERIE_REDIS_URL` | Redis URL | redis://localhost:6379 |
| `VALERIE_ORACLE_BASE_URL` | Oracle mock URL | http://localhost:3000 |

## Deployment

### Docker Compose

```bash
# Production
docker-compose up -d

# Development (with hot reload)
docker-compose -f docker-compose.dev.yml up
```

### Deploy Script

```bash
./scripts/deploy.sh production
```

## Version History

- **v1.0.0** - First public release
  - 7 LLM providers (Ollama, Groq, Gemini, Anthropic, Bedrock, Azure, LightLLM)
  - Multi-domain architecture with pluggable domains
  - 15 specialized agents (10 core + 5 infrastructure)
  - Enterprise features: JWT auth, rate limiting, Redis sessions
  - Observability: Structlog, Prometheus, LangSmith/Langfuse
  - 609 tests with Codecov coverage tracking
  - CI/CD with GitHub Actions
  - Railway deployment ready

## License

MIT License - Ismael Dosil
