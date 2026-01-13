# Valerie Supplier Chatbot - Component Description

## Table of Contents

1. [Core Agents](#core-agents)
2. [Infrastructure Agents](#infrastructure-agents)
3. [LLM Providers](#llm-providers)
4. [API Layer](#api-layer)
5. [Models](#models)
6. [Utilities](#utilities)

---

## Core Agents

Located in `src/valerie/agents/`

### 1. Orchestrator Agent

**File:** `orchestrator.py`

**Purpose:** Central coordinator that routes requests to appropriate agents based on intent.

**Responsibilities:**
- Receive classified intent from Intent Classifier
- Determine which agents need to be invoked
- Define the processing pipeline for each intent type
- Manage agent execution order

**Input:** ChatState with classified intent
**Output:** ChatState with routing information

**Routing Logic:**

| Intent | Route |
|--------|-------|
| SUPPLIER_SEARCH | search → compliance → response |
| SUPPLIER_COMPARISON | search → compliance → comparison → response |
| RISK_ASSESSMENT | search → compliance → risk → response |
| TECHNICAL_QUESTION | process_expertise → response |
| CLARIFICATION | memory_context → response |
| GREETING/UNKNOWN | response (direct) |

---

### 2. Intent Classifier Agent

**File:** `intent_classifier.py`

**Purpose:** Classifies user intent and extracts entities from natural language input.

**Responsibilities:**
- Analyze user message to determine intent
- Extract relevant entities (processes, certifications, locations, suppliers)
- Provide confidence score for classification
- Handle ambiguous or multi-intent queries

**Supported Intents:**
- `SUPPLIER_SEARCH` - Finding suppliers
- `SUPPLIER_COMPARISON` - Comparing suppliers
- `RISK_ASSESSMENT` - Evaluating supplier risks
- `TECHNICAL_QUESTION` - Process/material questions
- `COMPLIANCE_CHECK` - Certification verification
- `CLARIFICATION` - Follow-up questions
- `GREETING` - Greetings/help
- `UNKNOWN` - Unrecognized intent

**Entity Extraction:**
```python
{
    "processes": ["heat_treatment", "anodizing"],
    "certifications": ["Nadcap", "AS9100"],
    "locations": ["Phoenix, AZ"],
    "suppliers": ["SUP-001", "AeroTech"]
}
```

---

### 3. Supplier Search Agent

**File:** `supplier_search.py`

**Purpose:** Searches and retrieves suppliers based on specified criteria.

**Responsibilities:**
- Query supplier database based on entities
- Filter by process capabilities
- Filter by certifications
- Apply location preferences
- Rank results by relevance

**Search Criteria:**
- Process capabilities (heat treatment, plating, coating, etc.)
- Certifications (Nadcap, AS9100, ITAR, etc.)
- Geographic location
- Quality metrics
- Capacity availability

**Output:** List of `Supplier` objects matching criteria

---

### 4. Compliance Validation Agent

**File:** `compliance.py`

**Purpose:** Validates supplier certifications and compliance status.

**Responsibilities:**
- Verify certification authenticity
- Check expiration dates
- Validate scope matches requirements
- Flag ITAR-registered suppliers
- Identify compliance gaps

**Certification Types:**

| Type | Description |
|------|-------------|
| Nadcap | Aerospace special process certification |
| AS9100 | Aerospace quality management |
| ISO 9001 | General quality management |
| ITAR | International Traffic in Arms Regulations |
| Boeing D6-54551 | Boeing special process approval |
| Airbus AIPS | Airbus process approval |

**Output:** List of `ComplianceInfo` objects with validation results

---

### 5. Supplier Comparison Agent

**File:** `comparison.py`

**Purpose:** Compares multiple suppliers across various dimensions.

**Responsibilities:**
- Multi-dimensional comparison
- Score calculation per dimension
- Identify strengths and weaknesses
- Generate recommendations
- Produce data for visualizations

**Comparison Dimensions:**
1. Quality Rate (%)
2. On-Time Delivery (%)
3. Price Competitiveness
4. Lead Time
5. Certifications
6. Geographic Proximity

**Output:**
```python
{
    "suppliers": [
        {"name": "...", "scores": {...}, "strengths": [...], "weaknesses": [...]}
    ],
    "recommendation": {
        "supplier_name": "...",
        "rationale": "..."
    }
}
```

---

### 6. Risk Assessment Agent

**File:** `risk_assessment.py`

**Purpose:** Evaluates supplier risk across multiple dimensions.

**Responsibilities:**
- Calculate risk scores per dimension
- Aggregate overall risk score
- Identify high-risk factors
- Suggest mitigation strategies
- Flag critical risks for HITL

**Risk Dimensions:**
| Dimension | Weight | Factors |
|-----------|--------|---------|
| Financial | 20% | Credit rating, payment history |
| Quality | 25% | Defect rates, audit results |
| Delivery | 20% | On-time performance, capacity |
| Compliance | 15% | Certification status, audit findings |
| Geographic | 10% | Location risks, logistics |
| Dependency | 10% | Single source risk, alternatives |

**Output:** List of `RiskScore` objects with dimension breakdowns

---

### 7. Process Expertise Agent

**File:** `process_expertise.py`

**Purpose:** Subject Matter Expert (SME) for surface finishing processes.

**Responsibilities:**
- Answer technical questions about processes
- Explain material compatibility
- Reference industry specifications
- Provide process recommendations
- Explain coating properties

**Knowledge Areas:**
- Heat treatment processes
- Plating (cadmium, nickel, chrome, zinc)
- Anodizing (Type I, II, III)
- Passivation
- Painting and primers
- Shot peening
- NDT processes

**Specifications Referenced:**
- MIL-specs (MIL-DTL-5541, MIL-PRF-46010, etc.)
- AMS specifications
- Boeing, Airbus OEM specs

---

### 8. Response Generation Agent

**File:** `response_generation.py`

**Purpose:** Formats agent outputs into natural language responses.

**Responsibilities:**
- Generate human-readable responses
- Format tables and lists
- Adapt tone and detail level
- Handle multiple response types
- Support markdown formatting

**Response Types:**

| Type | Usage |
|------|-------|
| `table` | Supplier lists, comparisons |
| `text` | Technical explanations |
| `error` | Error messages |
| `comparison` | Side-by-side comparisons |

---

### 9. Memory Context Agent

**File:** `memory_context.py`

**Purpose:** Manages conversation context and resolves references.

**Responsibilities:**
- Track conversation history
- Resolve pronouns ("it", "they", "that supplier")
- Maintain entity context across turns
- Handle follow-up questions
- Manage session state

**Reference Resolution:**
```
User: "Find heat treatment suppliers"
Assistant: "Found 3 suppliers..."
User: "Tell me more about the first one"  ← Resolves "first one" to specific supplier
```

---

### 10. Oracle Integration Agent

**File:** `oracle_integration.py`

**Purpose:** Interfaces with Oracle Fusion Cloud ERP for supplier data.

**Responsibilities:**
- OAuth authentication with Oracle
- Fetch supplier master data
- Retrieve purchase order history
- Get agreement information
- Handle pagination and rate limiting

**Oracle APIs Used:**
- `/fscmRestApi/resources/11.13.18.05/suppliers`
- `/fscmRestApi/resources/11.13.18.05/purchaseOrders`
- `/fscmRestApi/resources/11.13.18.05/purchaseAgreements`

**Features:**
- Token caching with auto-refresh
- Circuit breaker for resilience
- Batch queries for efficiency

---

## Infrastructure Agents

Located in `src/valerie/infrastructure/`

### 1. Guardrails Agent

**File:** `guardrails.py`

**Purpose:** Security layer that validates all input before processing.

**Detection Layers:**

1. **Regex Layer** - Fast pattern matching
2. **ML Layer** - Anomaly detection
3. **LLM Layer** - Semantic analysis

**Detections:**

| Type | Examples |
|------|----------|
| PII | SSN, credit cards, emails |
| Injection | Prompt injection, SQL injection |
| XSS | Script tags, event handlers |
| ITAR | Defense-related keywords |

**Output:** `guardrails_passed: bool`, `blocked_reason: str`

---

### 2. HITL Agent (Human-in-the-Loop)

**File:** `hitl.py`

**Purpose:** Manages human approval for critical decisions.

**Triggers:**
- ITAR-related queries
- High-risk suppliers (score > 0.7)
- Low confidence responses (< 70%)
- Supplier debarment decisions

**Decision Options:**
- `approve` - Proceed with action
- `reject` - Cancel and notify user
- `modify` - Adjust parameters and retry
- `escalate` - Send to higher authority

**Priority Levels:**

| Priority | Trigger |
|----------|---------|
| Critical | ITAR decisions |
| Urgent | Risk score > 0.8 |
| High | Risk score > 0.6 |
| Normal | Low confidence |

---

### 3. Fallback Agent

**File:** `fallback.py`

**Purpose:** Error handling and graceful degradation.

**Responsibilities:**
- Catch and classify errors
- Apply recovery strategies
- Generate fallback responses
- Log incidents for review

**Recovery Strategies:**

| Error Type | Strategy |
|------------|----------|
| LLM timeout | Retry with shorter prompt |
| Oracle unavailable | Use cached data |
| Agent failure | Skip and continue |
| Unknown error | Generic fallback response |

**Circuit Breaker:**
- Opens after 5 consecutive failures
- Half-open after 60 seconds
- Closes after successful request

---

### 4. Evaluation Agent

**File:** `evaluation.py`

**Purpose:** LLM-as-Judge quality assessment of responses.

**Evaluation Dimensions:**

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Relevance | 25% | Answer matches query |
| Accuracy | 25% | Factually correct |
| Completeness | 20% | All aspects covered |
| Clarity | 15% | Easy to understand |
| Actionability | 10% | Provides next steps |
| Safety | 5% | No harmful content |

**Sampling:** Evaluates ~10% of responses to reduce cost

**Output:** `evaluation_score: float` (0-100)

---

### 5. Observability Manager

**File:** `observability.py`

**Purpose:** Tracing, metrics, and logging coordination.

**Features:**
- Distributed tracing with span hierarchy
- Metric collection per agent
- Structured logging
- Trace decorator for agents

**Usage:**
```python
@observability.trace_agent("supplier_search")
async def search_suppliers(state):
    # Automatically traced
    ...
```

**Metrics Collected:**
- `agent_latency_ms` - Processing time per agent
- `llm_tokens_used` - Token consumption
- `cache_hit_rate` - Cache effectiveness
- `error_count` - Failures per agent

---

## LLM Providers

Located in `src/valerie/llm/`

### Base Provider

**File:** `base.py`

**Purpose:** Abstract base class for all LLM providers.

**Interface:**
```python
class BaseLLMProvider(ABC):
    async def generate(messages, config) -> LLMResponse
    async def generate_stream(messages, config) -> AsyncIterator[StreamChunk]
    async def is_available() -> bool
    async def health_check() -> dict
```

---

### Provider Summary (7 Providers)

| Provider | Type | Cost | Context | Use Case |
|----------|------|------|---------|----------|
| **Ollama** | Local | Free | Varies | Development, privacy |
| **Groq** | Cloud | Free | 32K | Fast demos, prototypes |
| **Gemini** | Cloud | Free | 2M | Long context, production |
| **Anthropic** | Cloud | Paid | 200K | Production, high quality |
| **Bedrock** | AWS | Paid | Varies | AWS-native deployments |
| **Azure OpenAI** | Azure | Paid | 128K | Azure-native deployments |
| **LightLLM** | On-Premise | Free | Varies | GPU clusters, self-hosted |

---

### Ollama Provider

**File:** `ollama.py`

**Purpose:** Local LLM execution via Ollama.

**Configuration:**
- `VALERIE_OLLAMA_BASE_URL` - Server URL (default: localhost:11434)
- `VALERIE_OLLAMA_MODEL` - Model name (default: llama3.2)

**Supported Models:**
- llama3.2, llama3.1
- mistral, mixtral
- codellama
- Any Ollama-compatible model

---

### Groq Provider

**File:** `groq.py`

**Purpose:** Fast cloud inference via Groq.

**Configuration:**
- `VALERIE_GROQ_API_KEY` - API key (required)

**Supported Models:**
- llama-3.3-70b-versatile
- llama-3.1-70b-versatile
- mixtral-8x7b-32768

**Rate Limits:** 30 req/min, 14,400 req/day (free tier)

---

### Gemini Provider

**File:** `gemini.py`

**Purpose:** Google AI models with massive context window.

**Configuration:**
- `VALERIE_GEMINI_API_KEY` - API key (required)
- `VALERIE_GEMINI_MODEL` - Model (default: gemini-1.5-flash)

**Supported Models:**
- gemini-1.5-flash (fast)
- gemini-1.5-pro (quality, 2M context)

**Rate Limits:** 15 req/min (free tier)

---

### Anthropic Provider

**File:** `anthropic.py`

**Purpose:** Claude models via Anthropic API.

**Configuration:**
- `VALERIE_ANTHROPIC_API_KEY` - API key (required)
- `VALERIE_MODEL_NAME` - Model (default: claude-sonnet-4-20250514)

**Supported Models:**
- claude-sonnet-4-20250514
- claude-opus-4-20250514
- claude-3-5-sonnet-20241022

---

### AWS Bedrock Provider

**File:** `bedrock.py`

**Purpose:** AWS-managed LLM inference.

**Configuration:**
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)
- `VALERIE_BEDROCK_MODEL` - Model ID

**Supported Models:**
- anthropic.claude-3-sonnet-20240229-v1:0
- anthropic.claude-3-haiku-20240307-v1:0
- amazon.titan-text-express-v1
- meta.llama3-70b-instruct-v1:0

---

### Azure OpenAI Provider

**File:** `azure_openai.py`

**Purpose:** Azure-managed OpenAI models.

**Configuration:**
- `AZURE_OPENAI_API_KEY` - API key
- `AZURE_OPENAI_ENDPOINT` - Azure endpoint URL
- `AZURE_OPENAI_DEPLOYMENT` - Deployment name
- `AZURE_OPENAI_API_VERSION` - API version

**Supported Models:**
- gpt-4-turbo
- gpt-4o
- gpt-35-turbo

---

### LightLLM Provider

**File:** `lightllm.py`

**Purpose:** On-premise GPU cluster inference (OpenAI-compatible API).

**Configuration:**
- `VALERIE_LIGHTLLM_BASE_URL` - Server URL
- `VALERIE_LIGHTLLM_MODEL` - Model name

**Features:**
- Tensor parallelism
- Continuous batching
- Token streaming

---

### Provider Factory

**File:** `factory.py`

**Purpose:** Creates and manages LLM provider instances.

**Functions:**
- `get_llm_provider()` - Get default provider
- `get_available_providers()` - List available providers
- `create_provider(name)` - Create specific provider

**Fallback Logic:**
```python
# Tries providers in order until one works
providers = ["ollama", "groq", "gemini", "anthropic", "bedrock", "azure_openai", "lightllm"]
```

---

## API Layer

Located in `src/valerie/api/`

### Main Application

**File:** `main.py`

**Purpose:** FastAPI application factory.

**Endpoints:**
- Health checks (`/health`, `/ready`, `/live`)
- API routes (`/api/v1/...`)
- WebSocket (`/ws/...`)

---

### Chat Routes

**File:** `routes/chat.py`

**Endpoints:**

| Path | Method | Description |
|------|--------|-------------|
| `/api/v1/chat` | POST | Send message |
| `/api/v1/sessions/{id}` | GET | Get session |
| `/api/v1/sessions/{id}` | DELETE | Delete session |

---

### Supplier Routes

**File:** `routes/suppliers.py` (via chat.py)

**Endpoints:**

| Path | Method | Description |
|------|--------|-------------|
| `/api/v1/suppliers/search` | POST | Search suppliers |

---

### WebSocket

**File:** `websocket.py`

**Purpose:** Real-time streaming responses.

**Events:** connected, agent_start, agent_end, stream_chunk, stream_end, error

---

### Schemas

**File:** `schemas.py`

**Purpose:** Pydantic models for API request/response.

**Models:**
- `ChatRequest` - Incoming chat message
- `ChatResponse` - Chat response with metadata
- `SupplierSearchRequest` - Search criteria
- `HealthResponse` - Health check response

---

## Models

Located in `src/valerie/models/`

### State

**File:** `state.py`

**Classes:**
- `ChatState` - Main state object for agent pipeline
- `Supplier` - Supplier data model
- `Certification` - Certification details
- `ComplianceInfo` - Compliance validation result
- `RiskScore` - Risk assessment result
- `AgentOutput` - Standardized agent output
- `Intent` - Intent enumeration

---

### Config

**File:** `config.py`

**Classes:**
- `Settings` - Application configuration (from env vars)

**Key Settings:**
- LLM provider configuration
- Oracle connection settings
- Feature flags (PII detection, ITAR, HITL)
- Logging configuration

---

## Utilities

Located in `src/valerie/utils/`

### Helpers

**File:** `helpers.py`

**Functions:**
- `format_supplier_table()` - Format suppliers as markdown table
- `format_comparison_table()` - Format comparison data
- `truncate_text()` - Safely truncate long text
- `parse_json_response()` - Parse LLM JSON output
- `calculate_weighted_score()` - Weighted scoring utility

---

## Graph Builder

Located in `src/valerie/graph/`

### Builder

**File:** `builder.py`

**Purpose:** Constructs the LangGraph state machine.

**Functions:**
- `build_graph()` - Create StateGraph with nodes/edges
- `get_compiled_graph()` - Get compiled graph with checkpointing

**Node Functions:**
Each agent has a corresponding node function that wraps the agent's `process()` method.

**Routing Functions:**
- `route_after_guardrails()` - Route based on security check
- `route_after_intent()` - Route based on classified intent
- `route_after_search()` - Route after supplier search
- `route_after_compliance()` - Route after compliance check
- `route_after_hitl()` - Route after human decision
