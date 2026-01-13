# Valerie Chatbot - System Architecture

## Overview

The Valerie Chatbot is a **multi-domain AI platform** built on LangGraph that orchestrates specialized agents across pluggable business domains. The system follows a supervisor pattern where a central orchestrator routes requests to domain-specific agents.

### Key Architectural Concepts (v3.0)

| Concept | Description |
|---------|-------------|
| **Domain** | A pluggable business area (supplier, client, inventory) |
| **DomainRegistry** | Singleton that manages domain discovery and routing |
| **CoreState** | Domain-agnostic state shared across all domains |
| **DomainStateExtension** | Domain-specific state stored in `CoreState.domain_data` |
| **BaseDomain** | Abstract base class that all domains implement |

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  CLI (Typer)│  │ REST API    │  │  WebSocket  │  │  Streamlit  │        │
│  │             │  │  (FastAPI)  │  │  Streaming  │  │  Demo UI    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                                 │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Guardrails  │  │     HITL     │  │   Fallback   │  │ Observability│    │
│  │  (Security)  │  │  (Approval)  │  │  (Recovery)  │  │  (Tracing)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         Evaluation Agent                              │   │
│  │                    (LLM-as-Judge Quality Assessment)                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DOMAIN LAYER (v3.0)                                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         Domain Registry                               │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │   │   Supplier   │  │    Client    │  │  Inventory   │   ...        │   │
│  │   │    Domain    │  │    Domain    │  │    Domain    │              │   │
│  │   │              │  │   (future)   │  │   (future)   │              │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Domain Classifier                                  │   │
│  │               (Routes to appropriate domain)                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LANGGRAPH CORE                                     │
│                                                                              │
│                      ┌──────────────────────┐                               │
│                      │  Intent Classifier   │                               │
│                      │  (Domain-Aware)      │                               │
│                      └──────────┬───────────┘                               │
│                                 │                                            │
│         ┌───────────────────────┼───────────────────────┐                   │
│         │                       │                       │                    │
│         ▼                       ▼                       ▼                    │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐             │
│  │  Supplier   │        │  Compliance │        │   Process   │             │
│  │   Search    │        │  Validation │        │  Expertise  │             │
│  └──────┬──────┘        └──────┬──────┘        └─────────────┘             │
│         │                      │                                             │
│         └───────────┬──────────┘                                            │
│                     ▼                                                        │
│          ┌─────────────────┐        ┌─────────────┐                         │
│          │   Comparison /  │        │   Memory    │                         │
│          │ Risk Assessment │        │   Context   │                         │
│          └────────┬────────┘        └─────────────┘                         │
│                   │                                                          │
│                   ▼                                                          │
│          ┌─────────────────────────────────┐                                │
│          │     Response Generation         │                                │
│          └─────────────────────────────────┘                                │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL INTEGRATIONS                                │
│                                                                              │
│  ┌──────────────────────┐              ┌──────────────────────┐            │
│  │   Oracle Fusion      │              │    LLM Providers (7)  │            │
│  │   Integration        │              │  ┌────────────────┐  │            │
│  │   ┌──────────────┐   │              │  │ Ollama (Local) │  │            │
│  │   │ Suppliers    │   │              │  ├────────────────┤  │            │
│  │   │ Orders       │   │              │  │ Groq (Free)    │  │            │
│  │   │ Agreements   │   │              │  ├────────────────┤  │            │
│  │   └──────────────┘   │              │  │ Gemini (Free)  │  │            │
│  └──────────────────────┘              │  ├────────────────┤  │            │
│                                         │  │ Anthropic      │  │            │
│                                         │  ├────────────────┤  │            │
│                                         │  │ Bedrock (AWS)  │  │            │
│                                         │  ├────────────────┤  │            │
│                                         │  │ Azure OpenAI   │  │            │
│                                         │  ├────────────────┤  │            │
│                                         │  │ LightLLM       │  │            │
│                                         │  └────────────────┘  │            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. Input Processing

```
User Input → Guardrails → Intent Classifier → Orchestrator
```

1. **Guardrails Agent** validates input for:
   - PII detection (SSN, credit cards, etc.)
   - Injection attacks (prompt injection, SQL injection)
   - ITAR/sensitive content detection
   - Content length and format validation

2. **Intent Classifier** determines:
   - Intent type (search, compare, technical, etc.)
   - Confidence score
   - Extracted entities (processes, certifications, locations)

3. **Orchestrator** routes to appropriate agents based on intent

### 2. Agent Routing Logic

```python
Intent Mapping:
├── SUPPLIER_SEARCH     → Supplier Search → Compliance → Response
├── SUPPLIER_COMPARISON → Supplier Search → Compliance → Comparison → Response
├── RISK_ASSESSMENT     → Supplier Search → Compliance → Risk → Response
├── TECHNICAL_QUESTION  → Process Expertise → Response
├── CLARIFICATION       → Memory Context → Response
├── GREETING            → Response (direct)
└── UNKNOWN             → Response (fallback)
```

### 3. Data Processing Pipeline

For supplier-related queries:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Supplier   │───▶│ Compliance  │───▶│  Optional:  │
│   Search    │    │ Validation  │    │ Comparison/ │
│             │    │             │    │    Risk     │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────────────────────────────────────────┐
│              Response Generation                  │
│  (Formats data into natural language response)   │
└──────────────────────────────────────────────────┘
```

### 4. Infrastructure Processing

Every request goes through:

```
Response → Fallback (error handling) → Evaluation → Final Output
```

## State Management

### CoreState (v3.0)

The system uses `CoreState` for domain-agnostic fields and `domain_data` for domain-specific extensions:

```python
class CoreState:
    # Session (shared)
    session_id: str
    messages: list[Message]
    user_id: str | None
    user_role: str

    # Domain routing
    current_domain: str | None  # "supplier", "client", etc.

    # Classification (domain-agnostic)
    intent: str  # String, domain interprets it
    confidence: float
    entities: dict

    # Domain-specific state extensions
    domain_data: dict[str, dict]  # {"supplier": {...}, "client": {...}}

    # Infrastructure (shared)
    guardrails_passed: bool
    requires_human_approval: bool
    agent_outputs: dict[str, AgentOutput]

    # Output
    final_response: str
```

### Domain State Extension

Each domain defines its own state extension stored in `CoreState.domain_data`:

```python
# Supplier domain state (in domain_data["supplier"])
class SupplierStateExtension:
    search_criteria: dict
    suppliers: list[Supplier]
    compliance_results: list[ComplianceInfo]
    risk_results: list[RiskScore]
    itar_flagged: bool
```

### Legacy ChatState

For backward compatibility, the legacy `ChatState` is still supported for single-domain use:

```python
class ChatState:
    # Session
    session_id: str
    messages: list[Message]

    # Classification
    intent: Intent
    confidence: float
    entities: dict

    # Data
    suppliers: list[Supplier]
    compliance_results: list[ComplianceInfo]
    risk_results: list[RiskScore]
    comparison_data: dict

    # Control
    guardrails_passed: bool
    requires_human_approval: bool
    itar_flagged: bool

    # Output
    final_response: str
    agent_outputs: dict[str, AgentOutput]
```

## Multi-Domain Architecture (v3.0)

### Domain Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                      Domain Registry                             │
│                                                                  │
│   register(domain) → Store domain                               │
│   get(domain_id)   → Retrieve domain                            │
│   find_by_keyword  → Match query to domain                      │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  Registered Domains                      │   │
│   │                                                          │   │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│   │  │ Supplier  │  │  Client   │  │ Inventory │  ...      │   │
│   │  │ domain_id │  │ domain_id │  │ domain_id │           │   │
│   │  │ intents   │  │ intents   │  │ intents   │           │   │
│   │  │ state_ext │  │ state_ext │  │ state_ext │           │   │
│   │  │ keywords  │  │ keywords  │  │ keywords  │           │   │
│   │  └───────────┘  └───────────┘  └───────────┘           │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Adding a New Domain

1. **Create domain directory**: `src/valerie/domains/<domain_name>/`
2. **Define intents**: `intents.py` with domain-specific Intent enum
3. **Define state**: `state.py` with DomainStateExtension subclass
4. **Implement domain**: `domain.py` with BaseDomain subclass
5. **Register domain**: Add to DomainRegistry in graph builder

For detailed instructions, see [Multi-Domain Architecture Guide](multi-domain-architecture.md).

## LangGraph Integration

### Graph Structure

```python
graph = StateGraph(ChatState)

# Add nodes
graph.add_node("guardrails", guardrails_node)
graph.add_node("intent_classifier", intent_classifier_node)
graph.add_node("supplier_search", supplier_search_node)
# ... more nodes

# Add edges
graph.add_edge(START, "guardrails")
graph.add_conditional_edges(
    "guardrails",
    route_after_guardrails,
    {"intent_classifier": "intent_classifier", "error_response": "response"}
)
# ... more edges

# Compile with checkpointing
compiled = graph.compile(checkpointer=MemorySaver())
```

### Checkpointing

LangGraph's `MemorySaver` enables:
- Conversation persistence
- HITL interrupt/resume capability
- State recovery after failures

## LLM Provider Abstraction

### Provider Hierarchy (7 Providers)

```
BaseLLMProvider (Abstract)
├── OllamaProvider      (Local, Free)
├── GroqProvider        (Cloud, Free tier)
├── GeminiProvider      (Cloud, Free tier, 2M context)
├── AnthropicProvider   (Cloud, Paid)
├── BedrockProvider     (AWS, Paid)
├── AzureOpenAIProvider (Azure, Paid)
└── LightLLMProvider    (On-Premise, Self-hosted)
```

### Fallback Chain

```python
# Default fallback order
PROVIDERS = ["ollama", "groq", "gemini", "anthropic", "bedrock", "azure_openai", "lightllm"]

# Automatic failover
async def generate_with_fallback(messages):
    for provider in get_available_providers():
        try:
            return await provider.generate(messages)
        except ProviderError:
            continue
    raise NoProvidersAvailable()
```

## API Layer

### FastAPI Application

```
/api/v1/
├── /chat           POST  - Send chat message
├── /sessions/{id}  GET   - Get session
├── /sessions/{id}  DELETE- Delete session
└── /suppliers/
    └── /search     POST  - Direct supplier search

/ws/
└── /chat/{session_id}    - WebSocket streaming

/health             GET   - Health check
/ready              GET   - Readiness probe
/live               GET   - Liveness probe
```

### WebSocket Events

```
Client → Server:
├── message: {type: "message", content: "..."}
└── ping:    {type: "ping"}

Server → Client:
├── connected:    Session established
├── agent_start:  Agent begins processing
├── agent_end:    Agent completes
├── stream_start: Response streaming begins
├── stream_chunk: Partial response
├── stream_end:   Streaming complete
├── error:        Error occurred
└── pong:         Ping response
```

## Security Architecture

### Defense in Depth

```
Layer 1: Regex-based filters (fast, pattern matching)
    ↓
Layer 2: ML-based detection (PII, anomalies)
    ↓
Layer 3: LLM-based validation (semantic analysis)
    ↓
Layer 4: Human review (HITL for critical decisions)
```

### ITAR Handling

```
ITAR Keywords Detected?
    ├── Yes → Flag itar_flagged = True
    │         Set requires_human_approval = True
    │         Route to HITL agent
    └── No  → Continue normal processing
```

## Observability

### Tracing Structure

```
Trace (per session)
├── Span: guardrails
├── Span: intent_classifier
├── Span: supplier_search
│   └── Span: oracle_api_call
├── Span: compliance
└── Span: response_generation
```

### Metrics Collected

- Agent latency (per agent)
- LLM token usage
- Cache hit rates
- Error rates
- HITL trigger rates
- Response quality scores (via Evaluation agent)

## Deployment Architecture

### Docker Compose

```yaml
services:
  chatbot-api:
    build: .
    ports: ["8000:8000"]
    depends_on: [redis, ollama]

  chatbot-demo:
    build: ./demo
    ports: ["8501:8501"]

  redis:
    image: redis:alpine

  ollama:
    image: ollama/ollama
```

### Kubernetes (Production)

```
┌─────────────────────────────────────────────────┐
│                   Ingress                        │
└───────────────────────┬─────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
┌───────────────┐               ┌───────────────┐
│   API Pods    │               │  Demo Pods    │
│   (HPA)       │               │               │
└───────┬───────┘               └───────────────┘
        │
        ▼
┌───────────────┐    ┌───────────────┐
│    Redis      │    │   Ollama      │
│   (Session)   │    │   (LLM)       │
└───────────────┘    └───────────────┘
```

## Performance Considerations

### Caching Strategy

- **Session Cache**: Redis for conversation state
- **Supplier Cache**: TTL-based for Oracle data
- **LLM Response Cache**: Hash-based for identical queries

### Rate Limiting

- API: 100 requests/minute per IP
- WebSocket: 30 messages/minute per session
- LLM: Provider-specific limits with backoff

### Concurrency

- Async/await throughout for I/O operations
- Connection pooling for Oracle API
- Agent parallel execution where dependencies allow
