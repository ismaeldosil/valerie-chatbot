# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-21

### Added

#### LLM Providers (7 total)
- **Ollama** - Local inference, free, unlimited usage
- **Groq** - Cloud inference, free tier (30 req/min, 14,400 req/day)
- **Gemini** - Google AI, free tier (15 req/min, 2M context window)
- **Anthropic** - Claude models, paid (200K context)
- **AWS Bedrock** - Enterprise AWS integration, paid
- **Azure OpenAI** - Enterprise Azure integration, paid (128K context)
- **LightLLM** - On-premise GPU clusters, self-hosted

#### Multi-Domain Architecture
- Pluggable domain system for multiple business areas
- BaseDomain, DomainRegistry, and CoreState abstractions
- Supplier Domain as first implementation (aerospace supplier management)
- Extensible design for adding new domains

#### 15 Specialized Agents
- **Core Agents (10)**: Orchestrator, Intent Classifier, Supplier Search, Compliance Validation, Supplier Comparison, Oracle Fusion, Process Expertise, Risk Assessment, Response Generation, Memory & Context
- **Infrastructure Agents (5)**: Guardrails, HITL, Fallback, Evaluation, Observability

#### Enterprise Features
- JWT authentication middleware
- Rate limiting per tenant (Redis/Memory backends)
- Redis session persistence
- Structured logging with Structlog
- Prometheus metrics with Grafana dashboards
- LangSmith (dev) / Langfuse (prod) tracing support
- Codecov integration for coverage tracking

#### Testing & Quality
- 609 tests with 79% code coverage
- Unit, integration, and API tests
- GitHub Actions CI/CD pipeline
- Codecov coverage reporting

#### Deployment
- Docker and Docker Compose support (dev + prod)
- Railway deployment ready
- Kubernetes/Helm charts for enterprise deployments
- Terraform modules for AWS infrastructure

### Technical Details

- Python 3.11+
- FastAPI for REST API
- WebSocket support for streaming
- LangGraph for orchestration
- Pydantic v2 for data validation
- Ruff for code formatting and linting
- Mypy for type checking

## License

MIT License - Ismael Dosil
