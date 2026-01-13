# LLM Configuration System

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Model Registry](#model-registry)
4. [Provider Management](#provider-management)
5. [Agent-to-Model Assignments](#agent-to-model-assignments)
6. [Configuration Guide](#configuration-guide)
7. [Adding New Providers](#adding-new-providers)
8. [API Usage Examples](#api-usage-examples)
9. [Environment-Specific Configuration](#environment-specific-configuration)
10. [Best Practices](#best-practices)

---

## Overview

The Valerie Supplier Chatbot uses a centralized LLM configuration system that supports 7 LLM providers and allows fine-grained control over which models are used for different agents and use cases.

### Key Features

- **7 LLM Providers** - Ollama, Groq, Gemini (free) | Anthropic, Bedrock, Azure (paid) | LightLLM (on-premise)
- **Centralized Configuration** - Single source of truth in `config/model-registry.yaml`
- **Agent-Specific Models** - Different agents can use different model tiers
- **Tier-Based Assignment** - Group agents by computational requirements (quality, fast, default, evaluation)
- **Automatic Fallback** - Gracefully falls back to alternative providers if primary is unavailable
- **Environment-Aware** - Different configurations for development, staging, production
- **Parameter Management** - Per-tier and per-agent parameter overrides (temperature, max_tokens, etc.)

### Design Philosophy

The system is designed around these principles:

1. **Configuration as Code** - All model configurations in version-controlled YAML
2. **DRY (Don't Repeat Yourself)** - Change models in one place, affects entire system
3. **Separation of Concerns** - Model selection logic separate from agent implementation
4. **Flexibility** - Support for free and paid providers, local and cloud
5. **Resilience** - Automatic fallback chains for high availability

---

## Architecture

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│         (Agents, API Endpoints, CLI Commands)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   ModelRegistry                             │
│        (Centralized Configuration Manager)                  │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │        config/model-registry.yaml                  │    │
│  │  - Provider definitions                            │    │
│  │  - Model tiers                                     │    │
│  │  - Agent assignments                               │    │
│  │  - Parameters                                      │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Provider Factory                           │
│         (Creates and manages provider instances)            │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐───────────────┐
         ▼               ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Ollama     │  │    Groq      │  │   Gemini     │  │  Anthropic   │
│  (Local)     │  │  (Free)      │  │   (Free)     │  │   (Paid)     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
         ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Bedrock    │  │ Azure OpenAI │  │  LightLLM    │
│   (AWS)      │  │   (Azure)    │  │ (On-Premise) │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Data Flow

```
1. Agent needs LLM
        │
        ▼
2. Agent calls get_model_registry()
        │
        ▼
3. Registry determines:
   - Which provider to use (from environment or defaults)
   - Which tier this agent belongs to (from agent_assignments)
   - Which model for that tier (from provider.models)
   - Which parameters to use (from parameters + agent_overrides)
        │
        ▼
4. Provider Factory creates provider instance
        │
        ▼
5. Agent uses provider to generate response
```

---

## Model Registry

### File Location

```
config/model-registry.yaml
```

### Structure

The registry is organized into several sections:

#### 1. Providers

Defines available LLM providers and their model tiers:

```yaml
providers:
  anthropic:
    enabled: true
    base_url: "https://api.anthropic.com"
    api_key_env: "VALERIE_ANTHROPIC_API_KEY"

    models:
      default: "claude-sonnet-4-20250514"      # Balanced
      fast: "claude-3-5-haiku-20241022"        # Speed
      quality: "claude-opus-4-20250514"        # Quality
      evaluation: "claude-3-5-sonnet-20241022" # LLM-as-Judge
      legacy: "claude-3-5-sonnet-20241022"     # Backward compatibility
```

**Supported Providers:**

| Provider | Type | Cost | Context | Use Case |
|----------|------|------|---------|----------|
| `ollama` | Local | Free | Varies | Development, privacy |
| `groq` | Cloud | Free | 32K | Fast demos, prototypes |
| `gemini` | Cloud | Free | 2M | Long context, production |
| `anthropic` | Cloud | Paid | 200K | Production, high quality |
| `bedrock` | Cloud (AWS) | Paid | Varies | AWS-native deployments |
| `azure_openai` | Cloud (Azure) | Paid | 128K | Azure-native deployments |
| `lightllm` | On-Premise | Free | Varies | GPU clusters, self-hosted |

**Model Tiers:**

| Tier | Purpose | Typical Use |
|------|---------|-------------|
| `default` | Balanced performance/cost | Standard operations |
| `fast` | Low latency | Simple classification, guardrails |
| `quality` | Best reasoning | Complex analysis, critical decisions |
| `evaluation` | LLM-as-Judge | Quality assessment |

#### 2. Defaults

Specifies default provider and fallback chain:

```yaml
defaults:
  provider: "ollama"  # Default (can override with VALERIE_LLM_PROVIDER)
  fallback_chain: ["ollama", "groq", "anthropic"]  # Try in order
```

#### 3. Environments

Environment-specific configurations:

```yaml
environments:
  development:
    provider: "ollama"
    model_tier: "fast"
    description: "Fast local models for development"

  production:
    provider: "anthropic"
    model_tier: "default"
    description: "Production with best balance"
```

#### 4. Agent Assignments

Maps agents to model tiers based on requirements:

```yaml
agent_assignments:
  quality:
    description: "Agents requiring high reasoning capability"
    model_tier: "quality"
    agents:
      - orchestrator
      - risk_assessment
      - compliance_validation
      - supplier_comparison

  fast:
    description: "Agents requiring fast response times"
    model_tier: "fast"
    agents:
      - intent_classifier
      - guardrails
      - memory_context

  standard:
    description: "Agents with balanced requirements"
    model_tier: "default"
    agents:
      - supplier_search
      - process_expertise
      - response_generation
      - oracle_fusion

  evaluation:
    description: "Agents that evaluate/judge other outputs"
    model_tier: "evaluation"
    agents:
      - evaluation
      - dev_supervisor
```

#### 5. Parameters

Default parameters per tier:

```yaml
parameters:
  quality:
    temperature: 0.1
    max_tokens: 4096
    timeout_seconds: 120

  default:
    temperature: 0.1
    max_tokens: 4096
    timeout_seconds: 60

  fast:
    temperature: 0.0
    max_tokens: 1024
    timeout_seconds: 30

  evaluation:
    temperature: 0.0
    max_tokens: 2000
    timeout_seconds: 60
```

#### 6. Agent Overrides

Fine-grained overrides for specific agents:

```yaml
agent_overrides:
  intent_classifier:
    temperature: 0.0
    max_tokens: 512

  response_generation:
    temperature: 0.3    # Higher for more natural responses
    max_tokens: 2048

  process_expertise:
    temperature: 0.2
    max_tokens: 4096
```

---

## Provider Management

### ModelRegistry Class

Located in `src/valerie/models/config.py`

The `ModelRegistry` class is a singleton that loads and manages the model registry configuration.

#### Key Methods

```python
class ModelRegistry:
    """Centralized registry for LLM model configurations."""

    def get_model(
        self,
        provider: str | None = None,
        tier: str = "default"
    ) -> str:
        """Get model name for a provider and tier."""

    def get_model_for_agent(
        self,
        agent_name: str,
        provider: str | None = None
    ) -> str:
        """Get the appropriate model for a specific agent."""

    def get_parameters_for_agent(self, agent_name: str) -> dict[str, Any]:
        """Get model parameters for a specific agent."""

    def get_parameters_for_tier(self, tier: str) -> dict[str, Any]:
        """Get default parameters for a model tier."""

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get full configuration for a provider."""

    def get_fallback_chain(self) -> list[str]:
        """Get the fallback provider chain."""

    def get_environment_config(self, environment: str) -> dict[str, Any]:
        """Get configuration for a specific environment."""
```

#### Provider Selection Logic

The registry determines which provider to use in this order:

1. **Explicit Override** - `VALERIE_LLM_PROVIDER` environment variable
2. **Paid LLM Toggle** - `VALERIE_USE_PAID_LLM=true` uses Anthropic
3. **Registry Default** - `defaults.provider` in model-registry.yaml
4. **Ultimate Fallback** - `ollama`

```python
@property
def default_provider(self) -> str:
    """Get the default provider name."""
    # Check for explicit provider override first
    env_provider = os.getenv("VALERIE_LLM_PROVIDER")

    # Check the paid LLM toggle
    use_paid = os.getenv("VALERIE_USE_PAID_LLM", "false").lower()
    if use_paid in ("true", "1", "yes"):
        return env_provider if env_provider else "anthropic"

    if env_provider:
        return env_provider

    return self._registry.get("defaults", {}).get("provider", "ollama")
```

### Provider Factory

Located in `src/valerie/llm/factory.py`

The factory creates and manages provider instances with automatic fallback.

#### Key Functions

```python
def get_llm_provider(
    provider_type: ProviderType | str | None = None,
    config: dict | None = None,
    use_fallback: bool = True,
) -> BaseLLMProvider:
    """Get an LLM provider instance."""

async def get_available_provider(
    preferred: ProviderType | str | None = None,
) -> BaseLLMProvider:
    """Get the first available provider from the fallback chain."""

async def health_check_all() -> dict[str, dict]:
    """Perform health check on all providers."""

def clear_provider_cache() -> None:
    """Clear cached provider instances."""
```

---

## Agent-to-Model Assignments

### Assignment Strategy

Agents are grouped into tiers based on their computational requirements:

#### Quality Tier

**Model:** Highest quality (e.g., Claude Opus 4, Llama 3.2 70B)

**Agents:**
- `orchestrator` - Central coordination requires strong reasoning
- `risk_assessment` - Complex multi-dimensional analysis
- `compliance_validation` - Critical regulatory decisions
- `supplier_comparison` - Nuanced evaluation of tradeoffs

**Why:** These agents make complex decisions that directly impact business outcomes. Higher quality models reduce errors and improve recommendations.

#### Fast Tier

**Model:** Lightweight, low latency (e.g., Claude Haiku, Llama 3.2 3B)

**Agents:**
- `intent_classifier` - Simple classification task
- `guardrails` - Pattern matching and validation
- `memory_context` - Reference resolution

**Why:** These agents perform simple, well-defined tasks where speed matters more than nuanced reasoning.

#### Standard Tier

**Model:** Balanced (e.g., Claude Sonnet 4, Llama 3.2)

**Agents:**
- `supplier_search` - Search and filtering
- `process_expertise` - Technical Q&A
- `response_generation` - Natural language generation
- `oracle_fusion` - API integration and data handling

**Why:** These agents need good performance but aren't as critical as quality tier. Balanced models provide good quality at reasonable cost.

#### Evaluation Tier

**Model:** Specialized for judging (e.g., Claude 3.5 Sonnet)

**Agents:**
- `evaluation` - LLM-as-Judge quality assessment
- `dev_supervisor` - Development workflow evaluation

**Why:** These agents evaluate the quality of other agents' outputs. They need strong reasoning but can use slightly different models optimized for evaluation tasks.

### How Assignment Works

1. Agent calls `get_model_registry().get_model_for_agent("agent_name")`
2. Registry searches `agent_assignments` to find which tier the agent belongs to
3. Retrieves the `model_tier` for that group (e.g., "quality")
4. Gets the model name for that tier from the current provider
5. Returns the model name

```python
def get_model_for_agent(
    self, agent_name: str, provider: str | None = None
) -> str:
    """Get the appropriate model for a specific agent."""
    provider = provider or self.default_provider
    agent_assignments = self._registry.get("agent_assignments", {})

    # Find which tier this agent belongs to
    for tier_name, tier_config in agent_assignments.items():
        agents = tier_config.get("agents", [])
        if agent_name in agents:
            model_tier = tier_config.get("model_tier", "default")
            return self.get_model(provider, model_tier)

    # Default tier if agent not found
    return self.get_model(provider, "default")
```

---

## Configuration Guide

### Environment Variables

#### Provider Selection

```bash
# Choose primary provider (7 options)
VALERIE_LLM_PROVIDER=ollama        # Local, free
VALERIE_LLM_PROVIDER=groq          # Cloud, free
VALERIE_LLM_PROVIDER=gemini        # Cloud, free (2M context)
VALERIE_LLM_PROVIDER=anthropic     # Cloud, paid
VALERIE_LLM_PROVIDER=bedrock       # AWS, paid
VALERIE_LLM_PROVIDER=azure_openai  # Azure, paid
VALERIE_LLM_PROVIDER=lightllm      # On-premise

# Fallback chain if primary fails
VALERIE_LLM_FALLBACK=ollama,groq,gemini,anthropic
```

#### Ollama Configuration

```bash
# Ollama server URL
VALERIE_OLLAMA_BASE_URL=http://localhost:11434

# Override model (optional, uses registry default if not set)
VALERIE_OLLAMA_MODEL=llama3.2:70b
```

#### Groq Configuration

```bash
# API key from https://console.groq.com/
VALERIE_GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# Override model (optional)
VALERIE_GROQ_MODEL=llama-3.3-70b-versatile
```

#### Gemini Configuration

```bash
# API key from https://aistudio.google.com/app/apikey
VALERIE_GEMINI_API_KEY=AIzaSy_xxxxxxxxxxxxx

# Override model (optional)
VALERIE_GEMINI_MODEL=gemini-1.5-pro
```

#### Anthropic Configuration

```bash
# API key from https://console.anthropic.com/
VALERIE_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Override model (optional)
VALERIE_MODEL_NAME=claude-opus-4-20250514
```

#### AWS Bedrock Configuration

```bash
# AWS credentials
AWS_ACCESS_KEY_ID=AKIA_xxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxx
AWS_DEFAULT_REGION=us-east-1

# Override model (optional)
VALERIE_BEDROCK_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

#### Azure OpenAI Configuration

```bash
# Azure OpenAI credentials
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo

# API version
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

#### LightLLM Configuration

```bash
# LightLLM server URL (OpenAI-compatible)
VALERIE_LIGHTLLM_BASE_URL=http://localhost:8080

# Override model (optional)
VALERIE_LIGHTLLM_MODEL=llama-70b
```

#### Generation Parameters

```bash
# Default temperature (0.0 = deterministic, 1.0 = creative)
VALERIE_TEMPERATURE=0.1

# Maximum tokens to generate
VALERIE_MAX_TOKENS=4096
```

### Changing Models Globally

To change which models are used across the entire system:

1. Edit `config/model-registry.yaml`
2. Update the model names under the relevant provider and tier
3. No code changes required - changes take effect immediately

**Example:** Switch to newer Claude models

```yaml
providers:
  anthropic:
    models:
      default: "claude-sonnet-4-20250514"   # Updated
      quality: "claude-opus-4-20250514"     # Updated
      fast: "claude-3-5-haiku-20241022"     # Same
```

### Adding New Tiers

1. Add tier to provider models:

```yaml
providers:
  anthropic:
    models:
      custom_tier: "claude-specific-model"
```

2. Add tier parameters:

```yaml
parameters:
  custom_tier:
    temperature: 0.15
    max_tokens: 8192
    timeout_seconds: 90
```

3. Create assignment group:

```yaml
agent_assignments:
  custom_group:
    description: "Custom agents"
    model_tier: "custom_tier"
    agents:
      - custom_agent_1
      - custom_agent_2
```

---

## Adding New Providers

### Step 1: Implement Provider Class

Create a new file in `src/valerie/llm/`:

```python
# src/valerie/llm/my_provider.py

from valerie.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
)

class MyProvider(BaseLLMProvider):
    """Custom LLM provider implementation."""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "my_provider"
        # Initialize client, API keys, etc.

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate response from the LLM."""
        # Implementation
        pass

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[str]:
        """Stream response from the LLM."""
        # Implementation
        pass

    async def is_available(self) -> bool:
        """Check if provider is available."""
        # Check API connectivity, model availability, etc.
        pass

    async def health_check(self) -> dict:
        """Perform health check."""
        return {
            "available": await self.is_available(),
            "provider": self._name,
            # Additional health info
        }
```

### Step 2: Register in Factory

Edit `src/valerie/llm/factory.py`:

```python
from valerie.llm.my_provider import MyProvider

class ProviderType(str, Enum):
    """Available LLM providers."""
    OLLAMA = "ollama"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    MY_PROVIDER = "my_provider"  # Add new provider

# Provider registry
PROVIDERS: dict[ProviderType, type[BaseLLMProvider]] = {
    ProviderType.OLLAMA: OllamaProvider,
    ProviderType.GROQ: GroqProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.MY_PROVIDER: MyProvider,  # Add mapping
}
```

### Step 3: Add to Model Registry

Edit `config/model-registry.yaml`:

```yaml
providers:
  # Existing providers...

  my_provider:
    enabled: true
    base_url: "https://api.myprovider.com"
    api_key_env: "VALERIE_MY_PROVIDER_API_KEY"

    models:
      default: "my-model-default"
      fast: "my-model-fast"
      quality: "my-model-quality"
      evaluation: "my-model-eval"
```

### Step 4: Update Environment Template

Edit `.env.example`:

```bash
# --- My Provider ---
VALERIE_MY_PROVIDER_API_KEY=
VALERIE_MY_PROVIDER_MODEL=my-model-default
```

### Step 5: Test Integration

```python
from valerie.llm import get_llm_provider

# Test basic usage
provider = get_llm_provider("my_provider")
response = await provider.generate([
    {"role": "user", "content": "Hello"}
])

# Test availability
is_available = await provider.is_available()

# Test health check
health = await provider.health_check()
```

---

## API Usage Examples

### Basic Usage

```python
from valerie.models import get_model_registry

# Get registry instance (cached)
registry = get_model_registry()

# Get current provider
provider = registry.default_provider  # "ollama", "groq", or "anthropic"

# Get model for a tier
model = registry.get_model(provider="anthropic", tier="quality")
# Returns: "claude-opus-4-20250514"

# Get model for an agent
model = registry.get_model_for_agent("orchestrator")
# Returns appropriate model based on agent's tier assignment

# Get parameters for an agent
params = registry.get_parameters_for_agent("intent_classifier")
# Returns: {"temperature": 0.0, "max_tokens": 512, ...}
```

### Using in Agents

```python
from valerie.models import get_model_registry
from valerie.llm import get_llm_provider
from valerie.llm.base import LLMMessage, LLMConfig

class MyAgent:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        registry = get_model_registry()

        # Get model for this agent
        self.model_name = registry.get_model_for_agent(agent_name)

        # Get parameters for this agent
        self.params = registry.get_parameters_for_agent(agent_name)

    async def process(self, messages: list[str]) -> str:
        # Get provider
        provider = get_llm_provider()

        # Create config with agent parameters
        config = LLMConfig(
            model=self.model_name,
            temperature=self.params["temperature"],
            max_tokens=self.params["max_tokens"],
        )

        # Generate response
        llm_messages = [
            LLMMessage(role="user", content=msg)
            for msg in messages
        ]

        response = await provider.generate(llm_messages, config)
        return response.content
```

### Provider Fallback

```python
from valerie.llm import get_available_provider

async def generate_with_fallback(messages):
    """Automatically uses first available provider from fallback chain."""
    provider = await get_available_provider()
    return await provider.generate(messages)
```

### Health Checks

```python
from valerie.llm import health_check_all

async def check_llm_health():
    """Check health of all configured providers."""
    health = await health_check_all()

    for provider_name, status in health.items():
        if status["available"]:
            print(f"✓ {provider_name}: Available")
        else:
            print(f"✗ {provider_name}: {status.get('error', 'Unavailable')}")
```

### Environment-Specific Configuration

```python
from valerie.models import get_model_registry
import os

registry = get_model_registry()

# Get configuration for current environment
env = os.getenv("ENVIRONMENT", "development")
env_config = registry.get_environment_config(env)

# Use environment-specific settings
provider = env_config.get("provider", "ollama")
model_tier = env_config.get("model_tier", "default")

print(f"Environment: {env}")
print(f"Provider: {provider}")
print(f"Tier: {model_tier}")
```

### Testing Different Models

```python
from valerie.models import get_model_registry

registry = get_model_registry()

# Test all tiers for a provider
provider = "anthropic"
for tier in ["fast", "default", "quality", "evaluation"]:
    model = registry.get_model(provider, tier)
    params = registry.get_parameters_for_tier(tier)
    print(f"{tier}: {model}")
    print(f"  Temperature: {params['temperature']}")
    print(f"  Max tokens: {params['max_tokens']}")
```

---

## Environment-Specific Configuration

### Development

**Goal:** Fast iteration, free resources, no cost

```yaml
environments:
  development:
    provider: "ollama"
    model_tier: "fast"
```

**Environment Variables:**
```bash
VALERIE_LLM_PROVIDER=ollama
VALERIE_OLLAMA_BASE_URL=http://localhost:11434
```

**Typical Models:**
- Fast tier: `llama3.2:3b` (3GB RAM, very fast)
- Default tier: `llama3.2` (8GB RAM, balanced)

### Staging

**Goal:** Production-like testing with cost control

```yaml
environments:
  staging:
    provider: "anthropic"
    model_tier: "default"
```

**Environment Variables:**
```bash
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-staging-xxxxx
```

**Typical Models:**
- Default tier: `claude-sonnet-4-20250514` (balanced)
- Quality tier: `claude-opus-4-20250514` (for critical agents only)

### Production

**Goal:** Best quality, reliability, and performance

```yaml
environments:
  production:
    provider: "anthropic"
    model_tier: "default"
```

**Environment Variables:**
```bash
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-prod-xxxxx
VALERIE_LLM_FALLBACK=anthropic,groq,ollama
```

**Typical Models:**
- Quality tier: `claude-opus-4-20250514` (orchestrator, risk, compliance)
- Default tier: `claude-sonnet-4-20250514` (most agents)
- Fast tier: `claude-3-5-haiku-20241022` (classifiers, guardrails)

### Testing/CI

**Goal:** Fast execution, consistent results, no external dependencies

```yaml
environments:
  testing:
    provider: "ollama"
    model_tier: "fast"
```

**Environment Variables:**
```bash
VALERIE_LLM_PROVIDER=ollama
VALERIE_TEMPERATURE=0.0  # Deterministic
```

---

## Best Practices

### 1. Centralize Configuration

**Do:**
```yaml
# config/model-registry.yaml
providers:
  anthropic:
    models:
      default: "claude-sonnet-4-20250514"
```

**Don't:**
```python
# Hardcoded in agent files (BAD!)
model = "claude-sonnet-4-20250514"
```

### 2. Use Agent-Specific Models

Match model capability to agent requirements:

```yaml
agent_assignments:
  quality:  # Complex reasoning
    agents: [orchestrator, risk_assessment]

  fast:  # Simple tasks
    agents: [intent_classifier, guardrails]
```

### 3. Override Parameters Sparingly

Only override when necessary:

```yaml
# Good: Override for specific need
agent_overrides:
  response_generation:
    temperature: 0.3  # Higher for natural language

# Bad: Overriding just to override
agent_overrides:
  supplier_search:
    temperature: 0.1  # Same as tier default (unnecessary)
```

### 4. Test Across Providers

Ensure your agents work with different providers:

```bash
# Test with free providers
VALERIE_LLM_PROVIDER=ollama pytest   # Local
VALERIE_LLM_PROVIDER=groq pytest     # Fast cloud
VALERIE_LLM_PROVIDER=gemini pytest   # 2M context

# Test with paid providers
VALERIE_LLM_PROVIDER=anthropic pytest     # Production
VALERIE_LLM_PROVIDER=bedrock pytest       # AWS
VALERIE_LLM_PROVIDER=azure_openai pytest  # Azure
```

### 5. Use Fallback Chains

Configure resilient fallback chains:

```yaml
defaults:
  fallback_chain: ["anthropic", "gemini", "groq", "ollama"]
```

This ensures if Anthropic is down, the system falls back to Gemini, then Groq, then Ollama.

### 6. Monitor Model Usage

Track which models are being used and their performance:

```python
from valerie.models import get_model_registry

registry = get_model_registry()

# Log model selection
logger.info(
    f"Agent: {agent_name}, "
    f"Provider: {registry.default_provider}, "
    f"Model: {registry.get_model_for_agent(agent_name)}"
)
```

### 7. Version Your Registry

Commit `model-registry.yaml` to version control and track changes:

```bash
git log -p config/model-registry.yaml
```

This provides an audit trail of model changes over time.

### 8. Document Changes

When updating models, document the rationale:

```yaml
# Updated 2025-01-15: Switched to Claude Opus 4 for better reasoning
providers:
  anthropic:
    models:
      quality: "claude-opus-4-20250514"
```

### 9. Cost Management

For paid providers, balance cost and quality:

- Use quality tier only for critical agents
- Use fast tier for high-volume, simple tasks
- Default tier for most agents
- Monitor token usage and adjust assignments

### 10. Local Development

Use free local models during development:

```bash
# .env.development
VALERIE_LLM_PROVIDER=ollama
VALERIE_OLLAMA_MODEL=llama3.2:3b  # Small, fast model
```

This allows development without API costs or rate limits.

---

## Troubleshooting

### Registry Not Loading

If the registry isn't loading, check:

1. File exists at `config/model-registry.yaml`
2. YAML syntax is valid (use YAML linter)
3. Check logs for loading errors

### Agent Getting Wrong Model

Debug model selection:

```python
from valerie.models import get_model_registry

registry = get_model_registry()
agent_name = "orchestrator"

# Check provider
print(f"Provider: {registry.default_provider}")

# Check tier assignment
assignments = registry._registry.get("agent_assignments", {})
for tier_name, config in assignments.items():
    if agent_name in config.get("agents", []):
        print(f"Tier: {tier_name}")
        print(f"Model Tier: {config['model_tier']}")

# Check final model
model = registry.get_model_for_agent(agent_name)
print(f"Model: {model}")
```

### Provider Not Available

Check provider health:

```python
from valerie.llm import health_check_all

health = await health_check_all()
for provider, status in health.items():
    print(f"{provider}: {status}")
```

Common issues:
- **Ollama:** Server not running (`ollama serve`)
- **Groq:** Invalid API key or rate limit exceeded (30 req/min)
- **Gemini:** Invalid API key or rate limit exceeded (15 req/min)
- **Anthropic:** Invalid API key or insufficient credits
- **Bedrock:** AWS credentials not configured or IAM permissions missing
- **Azure OpenAI:** Invalid endpoint, API key, or deployment name
- **LightLLM:** Server not running or wrong base URL

### Performance Issues

If agents are slow:

1. Check if you're using the right tier (use `fast` for simple tasks)
2. Reduce `max_tokens` if responses are too long
3. Check provider latency (Groq is fastest, local Ollama varies by model)

---

## Migration Guide

### Upgrading from Older Configuration

If you have old hardcoded model names in agent files:

**Before:**
```python
class MyAgent:
    def __init__(self):
        self.model = "claude-3-5-sonnet-20241022"
```

**After:**
```python
from valerie.models import get_model_registry

class MyAgent:
    def __init__(self, agent_name: str):
        registry = get_model_registry()
        self.model = registry.get_model_for_agent(agent_name)
```

### Adding New Agents

When adding a new agent:

1. Add to appropriate tier in `agent_assignments`:

```yaml
agent_assignments:
  standard:
    agents:
      - my_new_agent  # Add here
```

2. (Optional) Add agent-specific overrides:

```yaml
agent_overrides:
  my_new_agent:
    temperature: 0.2
    max_tokens: 2048
```

3. Use registry in agent code:

```python
from valerie.models import get_model_registry

registry = get_model_registry()
model = registry.get_model_for_agent("my_new_agent")
params = registry.get_parameters_for_agent("my_new_agent")
```

---

## Summary

The LLM configuration system provides:

1. **7 Providers** - Ollama, Groq, Gemini (free) | Anthropic, Bedrock, Azure (paid) | LightLLM (on-premise)
2. **Centralized Control** - All models defined in one YAML file
3. **Flexibility** - Support multiple providers and tiers
4. **Granularity** - Per-agent model and parameter control
5. **Resilience** - Automatic fallback chains
6. **Environment Awareness** - Different configs for dev/staging/prod
7. **Cost Optimization** - Right-size models to agent requirements

By following this system, you can:
- Change models globally without code changes
- Optimize costs by using smaller models for simple tasks
- Ensure high quality for critical decisions
- Maintain consistent configuration across environments
- Easily add new providers and models

For questions or issues, see the troubleshooting section or check the source files:
- `config/model-registry.yaml` - Model configuration
- `src/valerie/models/config.py` - ModelRegistry implementation
- `src/valerie/llm/factory.py` - Provider factory
