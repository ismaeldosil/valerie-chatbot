# Valerie Multi-Domain Architecture

## Overview

Valerie v3.0 introduces a **multi-domain architecture** that allows the chatbot platform to support multiple business domains (suppliers, clients, inventory, etc.) through a pluggable domain system.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOMAIN LAYER                                    │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │    Supplier     │  │     Client      │  │   Inventory     │  ...        │
│  │     Domain      │  │     Domain      │  │     Domain      │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                ▼                                            │
│                     ┌──────────────────────┐                                │
│                     │   Domain Registry    │                                │
│                     │   (Auto-discovery)   │                                │
│                     └──────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE LAYER                                      │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   CoreState     │  │   BaseDomain    │  │ DomainRegistry  │             │
│  │ (Shared State)  │  │  (Interface)    │  │  (Discovery)    │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/valerie/
├── core/                          # Framework core (domain-agnostic)
│   ├── domain/
│   │   ├── base.py               # BaseDomain abstract class
│   │   └── registry.py           # DomainRegistry singleton
│   └── state/
│       ├── core.py               # CoreState (shared fields)
│       └── composite.py          # CompositeState utilities
│
├── domains/                       # Pluggable business domains
│   ├── supplier/                  # Supplier domain (included)
│   │   ├── domain.py             # SupplierDomain implementation
│   │   ├── intents.py            # SupplierIntent enum
│   │   └── state.py              # SupplierStateExtension
│   │
│   └── <new_domain>/             # Your new domain
│       ├── __init__.py
│       ├── domain.py
│       ├── intents.py
│       └── state.py
│
├── agents/                        # Shared and domain-specific agents
├── graph/
│   ├── builder.py                # Legacy single-domain graph
│   └── multi_domain.py           # Multi-domain aware graph
└── ...
```

## Key Concepts

### 1. BaseDomain

Abstract base class that all domains must implement:

```python
from valerie.core import BaseDomain

class MyDomain(BaseDomain):
    domain_id = "my_domain"           # Unique identifier
    display_name = "My Domain"         # Human-readable name
    description = "Description..."     # What this domain does
    version = "1.0.0"
```

### 2. DomainRegistry

Singleton that manages domain discovery and routing:

```python
from valerie.core import DomainRegistry

registry = DomainRegistry()
registry.register(MyDomain())

# Find domain by keyword
domain = registry.find_by_keyword("my_keyword")

# Get all domains
all_domains = registry.get_all()
```

### 3. CoreState

Domain-agnostic state with `domain_data` for extensions:

```python
from valerie.core.state import CoreState

state = CoreState()
state.current_domain = "supplier"
state.domain_data["supplier"] = {"suppliers": [...]}
```

---

## Guide: Adding a New Domain

Follow these 5 steps to add a new business domain.

### Step 1: Create Domain Directory

```bash
mkdir -p src/valerie/domains/<domain_name>
touch src/valerie/domains/<domain_name>/__init__.py
touch src/valerie/domains/<domain_name>/domain.py
touch src/valerie/domains/<domain_name>/intents.py
touch src/valerie/domains/<domain_name>/state.py
```

### Step 2: Define Domain Intents

Create `intents.py` with your domain's intent classifications:

```python
# src/valerie/domains/inventory/intents.py
"""Inventory domain intent definitions."""

from enum import Enum


class InventoryIntent(str, Enum):
    """User intent classifications for inventory domain."""

    # Domain-specific intents
    STOCK_CHECK = "stock_check"
    REORDER_RECOMMENDATION = "reorder_recommendation"
    INVENTORY_REPORT = "inventory_report"
    WAREHOUSE_LOOKUP = "warehouse_lookup"

    # Common intents (shared with other domains)
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "InventoryIntent":
        """Convert a string to InventoryIntent."""
        try:
            return cls(value)
        except ValueError:
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
            return cls.UNKNOWN

    def is_domain_specific(self) -> bool:
        """Check if this is an inventory-specific intent."""
        return self in {
            self.STOCK_CHECK,
            self.REORDER_RECOMMENDATION,
            self.INVENTORY_REPORT,
            self.WAREHOUSE_LOOKUP,
        }
```

### Step 3: Define State Extension

Create `state.py` with domain-specific state fields:

```python
# src/valerie/domains/inventory/state.py
"""Inventory domain state extension."""

from pydantic import BaseModel, Field

from valerie.core.domain.base import DomainStateExtension


class InventoryItem(BaseModel):
    """Inventory item model."""

    sku: str
    name: str
    quantity: int
    warehouse_id: str
    reorder_point: int
    unit_cost: float


class StockLevel(BaseModel):
    """Stock level summary."""

    sku: str
    current_quantity: int
    available_quantity: int
    reserved_quantity: int
    status: str  # in_stock, low_stock, out_of_stock


class InventoryStateExtension(DomainStateExtension):
    """Inventory-specific state extension.

    This state is stored in CoreState.domain_data["inventory"].
    """

    # Search criteria
    search_criteria: dict[str, object] = Field(default_factory=dict)

    # Results
    items: list[InventoryItem] = Field(default_factory=list)
    stock_levels: list[StockLevel] = Field(default_factory=list)
    warehouse_data: dict[str, object] = Field(default_factory=dict)

    # Flags
    low_stock_alerts: list[str] = Field(default_factory=list)
```

### Step 4: Implement the Domain Class

Create `domain.py` implementing `BaseDomain`:

```python
# src/valerie/domains/inventory/domain.py
"""Inventory management domain implementation."""

from enum import Enum

from valerie.core.domain.base import (
    BaseDomain,
    DomainAgentConfig,
    DomainStateExtension,
)
from .intents import InventoryIntent
from .state import InventoryStateExtension


class InventoryDomain(BaseDomain):
    """Inventory management domain.

    This domain provides functionality for:
    - Stock level checking
    - Reorder recommendations
    - Inventory reporting
    - Warehouse lookups
    """

    domain_id = "inventory"
    display_name = "Inventory Management"
    description = (
        "Manage inventory levels, check stock, get reorder "
        "recommendations, and generate inventory reports."
    )
    version = "1.0.0"

    # Domain capabilities
    supports_hitl = False  # No human approval needed
    supports_streaming = True
    requires_auth = True  # Requires authentication

    def get_intent_enum(self) -> type[Enum]:
        """Return the InventoryIntent enum."""
        return InventoryIntent

    def get_state_extension(self) -> type[DomainStateExtension]:
        """Return the InventoryStateExtension class."""
        return InventoryStateExtension

    def get_agent_configs(self) -> list[DomainAgentConfig]:
        """Return configuration for inventory domain agents."""
        return [
            DomainAgentConfig(
                agent_class="valerie.domains.inventory.agents.StockCheckAgent",
                name="stock_check",
                description="Checks current stock levels",
                handles_intents=[InventoryIntent.STOCK_CHECK.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.domains.inventory.agents.ReorderAgent",
                name="reorder",
                description="Generates reorder recommendations",
                handles_intents=[InventoryIntent.REORDER_RECOMMENDATION.value],
                priority=50,
            ),
            DomainAgentConfig(
                agent_class="valerie.domains.inventory.agents.ReportAgent",
                name="inventory_report",
                description="Generates inventory reports",
                handles_intents=[InventoryIntent.INVENTORY_REPORT.value],
                priority=50,
            ),
        ]

    def get_keywords(self) -> list[str]:
        """Return keywords that identify the inventory domain."""
        return [
            # Core terms
            "inventory",
            "stock",
            "warehouse",
            "storage",
            # Actions
            "reorder",
            "replenish",
            "count",
            "level",
            # Items
            "sku",
            "parts",
            "materials",
            "components",
        ]

    def get_example_queries(self) -> list[str]:
        """Return example queries for the inventory domain."""
        return [
            # Stock checks
            "What's the current stock level for SKU-12345?",
            "How many titanium sheets do we have?",
            "Check inventory in warehouse A",
            # Reorder
            "Which items need to be reordered?",
            "Generate a reorder list for low stock items",
            # Reports
            "Show me the inventory summary",
            "Generate weekly inventory report",
        ]
```

### Step 5: Register the Domain and Export

Create `__init__.py` to export the domain:

```python
# src/valerie/domains/inventory/__init__.py
"""Inventory management domain.

This domain provides functionality for:
- Stock level checking
- Reorder recommendations
- Inventory reporting
- Warehouse lookups
"""

from .domain import InventoryDomain
from .intents import InventoryIntent
from .state import InventoryStateExtension

__all__ = ["InventoryDomain", "InventoryIntent", "InventoryStateExtension"]
```

Update `src/valerie/domains/__init__.py`:

```python
"""Business domains for the Valerie chatbot platform."""

from .supplier import SupplierDomain
from .inventory import InventoryDomain  # Add new domain

__all__ = ["SupplierDomain", "InventoryDomain"]
```

---

## Integrating with the Graph

### Option 1: Auto-Registration (Recommended)

Update `graph/multi_domain.py` to register your domain:

```python
def _get_domain_registry() -> DomainRegistry:
    """Get the initialized domain registry."""
    registry = DomainRegistry()

    if "supplier" not in registry:
        registry.register(SupplierDomain())

    # Add your new domain
    if "inventory" not in registry:
        from ..domains.inventory import InventoryDomain
        registry.register(InventoryDomain())

    return registry
```

### Option 2: Dynamic Registration

For runtime registration (e.g., based on config):

```python
from valerie.core import DomainRegistry
from valerie.domains.inventory import InventoryDomain

# At application startup
registry = DomainRegistry()

if settings.inventory_enabled:
    registry.register(InventoryDomain())
```

### Adding Domain-Specific Routing

Update the routing functions in `graph/multi_domain.py`:

```python
def route_after_intent(state: ChatState) -> str:
    """Route based on classified intent."""
    domain = state.entities.get("_domain", "supplier")
    intent = state.intent

    # Supplier domain routing
    if domain == "supplier":
        # ... existing supplier routing
        pass

    # NEW: Inventory domain routing
    elif domain == "inventory":
        if intent == "stock_check":
            return "stock_check_node"
        elif intent == "reorder_recommendation":
            return "reorder_node"
        elif intent == "inventory_report":
            return "report_node"

    return "response_generation"
```

---

## Creating Domain-Specific Agents

If your domain needs specialized agents:

```python
# src/valerie/domains/inventory/agents/stock_check.py
"""Stock check agent for inventory domain."""

from valerie.agents.base import BaseAgent
from valerie.models import ChatState


class StockCheckAgent(BaseAgent):
    """Agent that checks stock levels."""

    name = "stock_check"
    use_provider = True  # Use new LLM provider system

    def get_system_prompt(self) -> str:
        return """You are an inventory specialist...

        Given an SKU or item name, provide:
        1. Current stock level
        2. Availability status
        3. Location in warehouse
        """

    async def process(self, state: ChatState) -> ChatState:
        # Get domain-specific state
        from ..state import InventoryStateExtension
        from valerie.core.state import CompositeState
        from ..domain import InventoryDomain

        domain = InventoryDomain()
        inv_state = CompositeState.get_domain_state(
            state, domain, InventoryStateExtension
        )

        # Process query and update state
        # ... agent logic ...

        # Save domain state back
        CompositeState.set_domain_state(state, domain, inv_state)

        return state
```

---

## Testing Your Domain

### Unit Tests

```python
# tests/unit/domains/test_inventory_domain.py
import pytest
from valerie.domains.inventory import (
    InventoryDomain,
    InventoryIntent,
    InventoryStateExtension,
)
from valerie.core import DomainRegistry


class TestInventoryDomain:
    def test_domain_initialization(self):
        domain = InventoryDomain()
        assert domain.domain_id == "inventory"
        assert domain.display_name == "Inventory Management"

    def test_intent_enum(self):
        domain = InventoryDomain()
        intent_enum = domain.get_intent_enum()
        assert intent_enum.STOCK_CHECK.value == "stock_check"

    def test_keywords(self):
        domain = InventoryDomain()
        keywords = domain.get_keywords()
        assert "inventory" in keywords
        assert "stock" in keywords

    def test_registry_integration(self):
        registry = DomainRegistry()
        registry.clear()  # Start fresh

        domain = InventoryDomain()
        registry.register(domain)

        # Find by keyword
        found = registry.find_by_keyword("inventory")
        assert found is not None
        assert found.domain_id == "inventory"

    def test_state_extension(self):
        state = InventoryStateExtension()
        assert state.items == []
        assert state.stock_levels == []
```

### Integration Tests

```python
# tests/integration/test_inventory_routing.py
import pytest
from valerie.graph import get_multi_domain_graph
from valerie.models import ChatState
from langchain_core.messages import HumanMessage


@pytest.mark.asyncio
async def test_inventory_query_routes_correctly():
    graph = get_multi_domain_graph(checkpointer=False)

    state = ChatState(
        messages=[HumanMessage(content="Check stock for SKU-12345")],
        session_id="test-123",
    )

    result = await graph.ainvoke(state)

    assert result.entities.get("_domain") == "inventory"
```

---

## Checklist for New Domains

- [ ] Created `domains/<name>/` directory
- [ ] Defined `intents.py` with domain intents enum
- [ ] Defined `state.py` with state extension
- [ ] Implemented `domain.py` with BaseDomain subclass
- [ ] Created `__init__.py` with exports
- [ ] Updated `domains/__init__.py` to export new domain
- [ ] Registered domain in `graph/multi_domain.py`
- [ ] Added domain-specific routing (if needed)
- [ ] Created domain-specific agents (if needed)
- [ ] Added unit tests for domain
- [ ] Added integration tests for routing
- [ ] Updated documentation

---

## Architecture Diagrams

### Domain Classification Flow

```
User Message
     │
     ▼
┌─────────────┐
│  Guardrails │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Domain Classifier  │  ← Keyword matching
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│Supplier │ │Inventory│ ...
│ Domain  │ │ Domain  │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────────────────┐
│  Intent Classifier  │  ← Domain-aware
└──────────┬──────────┘
           │
           ▼
   Domain-Specific
      Routing
```

### State Composition

```
┌─────────────────────────────────────────────────┐
│                   CoreState                      │
├─────────────────────────────────────────────────┤
│  messages: [...]                                │
│  session_id: "abc123"                           │
│  intent: "stock_check"                          │
│  current_domain: "inventory"                    │
│                                                 │
│  domain_data: {                                 │
│    "supplier": {                                │
│      "suppliers": [...],                        │
│      "compliance_results": [...]                │
│    },                                           │
│    "inventory": {          ← Domain Extension   │
│      "items": [...],                            │
│      "stock_levels": [...],                     │
│      "warehouse_data": {...}                    │
│    }                                            │
│  }                                              │
└─────────────────────────────────────────────────┘
```

---

## Best Practices

1. **Keep domains independent**: Domains should not import from each other
2. **Use type-safe state access**: Use `CompositeState.get_domain_state()` with typed extensions
3. **Define clear keywords**: Ensure keywords don't overlap significantly between domains
4. **Version your domains**: Use semantic versioning for breaking changes
5. **Test in isolation**: Each domain should have its own test suite
6. **Document intents**: Each intent should have a clear description and examples
