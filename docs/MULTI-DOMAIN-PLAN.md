# Plan: Valerie Multi-Domain Architecture

## Resumen Ejecutivo

Transformar **valerie-chatbot** en **valerie-chatbot**: una plataforma multi-dominio que soporte Suppliers, Clients, y futuros dominios (Products, Inventory, Logistics).

---

## Análisis del Estado Actual

### Código Específico de Suppliers (12 áreas identificadas)

| Área | Archivos | Cambios Requeridos |
|------|----------|-------------------|
| **Data Models** | `models/state.py` | Supplier, Certification, ComplianceInfo, RiskScore |
| **Intents** | `models/state.py:13-23` | Intent enum hardcodeado (SUPPLIER_SEARCH, etc.) |
| **Intent Classifier** | `agents/intent_classifier.py` | Prompt específico aerospace |
| **Agents (6)** | `agents/supplier_search.py`, `compliance.py`, etc. | Prompts y lógica supplier-specific |
| **Oracle Integration** | `agents/oracle_integration.py` | Endpoints `/suppliers`, `/purchaseOrders` |
| **API Endpoints** | `api/routes/chat.py` | `/suppliers/search`, sample data |
| **Graph Routing** | `graph/builder.py` | Rutas hardcodeadas a supplier agents |
| **CLI** | `cli.py` | "Aerospace Supplier Recommendation System" |
| **Guardrails** | `infrastructure/guardrails.py` | ITAR detection (aerospace-specific) |
| **HITL** | `infrastructure/hitl.py` | Supplier approval triggers |
| **Config** | `config/agent-registry.yaml` | Descripciones supplier-focused |
| **Sample Data** | `api/routes/chat.py:30-94` | Aerospace supplier mock data |

### Agentes: Genéricos vs Específicos

```
GENÉRICOS (Reutilizables)          ESPECÍFICOS (Supplier-Only)
─────────────────────────          ──────────────────────────
✓ IntentClassifier (framework)     ✗ SupplierSearchAgent
✓ MemoryContextAgent               ✗ ComplianceAgent
✓ ResponseGenerationAgent          ✗ ComparisonAgent
✓ GuardrailsAgent                  ✗ RiskAssessmentAgent
✓ HITLAgent                        ✗ ProcessExpertiseAgent
✓ FallbackAgent                    ✗ OracleIntegrationAgent
✓ EvaluationAgent                  ✗ Orchestrator (routing logic)
✓ ObservabilityManager
```

---

## Arquitectura Propuesta

### Nueva Estructura de Directorios

```
valerie-chatbot/
├── src/valerie/
│   ├── core/                      # Framework genérico
│   │   ├── agents/
│   │   │   ├── base.py            # BaseAgent con domain awareness
│   │   │   └── registry.py        # AgentRegistry
│   │   ├── domain/
│   │   │   ├── base.py            # BaseDomain abstract class
│   │   │   ├── registry.py        # DomainRegistry singleton
│   │   │   └── router.py          # Cross-domain routing
│   │   ├── state/
│   │   │   ├── base.py            # CoreState (domain-agnostic)
│   │   │   └── composite.py       # CompositeState con extensions
│   │   ├── intents/
│   │   │   └── classifier.py      # Multi-domain classifier
│   │   └── graph/
│   │       └── composer.py        # Dynamic graph builder
│   │
│   ├── infrastructure/            # Shared (sin cambios)
│   │   ├── guardrails.py
│   │   ├── hitl.py
│   │   ├── fallback.py
│   │   └── ...
│   │
│   ├── domains/                   # Dominios pluggables
│   │   ├── supplier/              # Dominio actual (migrado)
│   │   │   ├── domain.py          # SupplierDomain class
│   │   │   ├── agents/            # Search, Compliance, etc.
│   │   │   ├── intents.py         # SupplierIntent enum
│   │   │   ├── state.py           # SupplierState extension
│   │   │   ├── models.py          # Supplier, Certification
│   │   │   └── config.yaml
│   │   │
│   │   ├── client/                # Nuevo dominio
│   │   │   ├── domain.py          # ClientDomain class
│   │   │   ├── agents/            # Search, Sales, Contracts
│   │   │   ├── intents.py         # ClientIntent enum
│   │   │   ├── state.py           # ClientState extension
│   │   │   ├── models.py          # Client, Contract, Opportunity
│   │   │   └── config.yaml
│   │   │
│   │   └── _template/             # Template para nuevos dominios
│   │
│   └── api/
│       ├── routes/
│       │   ├── chat.py            # Unified /chat endpoint
│       │   └── domain_router.py   # Dynamic domain routes
│       └── schemas/
│           ├── common.py
│           └── {domain}_schemas.py
│
└── config/
    ├── domains/
    │   ├── supplier.yaml
    │   └── client.yaml
    └── domain-registry.yaml       # Master config
```

### Abstracciones Clave

#### 1. BaseDomain Interface

```python
class BaseDomain(ABC):
    @property
    def name(self) -> str: ...           # "supplier", "client"
    @property
    def display_name(self) -> str: ...   # "Supplier Management"
    @property
    def intent_enum(self) -> Type[Enum]: ...
    @property
    def state_extension(self) -> Type: ...

    def get_agents(self) -> Dict[str, BaseAgent]: ...
    def get_graph_config(self) -> Dict: ...
    def get_intent_keywords(self) -> Dict[str, List[str]]: ...
```

#### 2. CoreState + Domain Extensions

```python
class CoreState(BaseModel):
    """Domain-agnostic."""
    messages: list
    session_id: str
    active_domain: Optional[str]      # "supplier" | "client"
    intent_raw: str
    entities: dict
    guardrails_passed: bool
    final_response: str
    agent_outputs: dict

class CompositeState(CoreState):
    """Con extensions por dominio."""
    domain_state: Dict[str, Any]      # {"supplier": SupplierState, ...}
```

#### 3. Two-Phase Classification

```
User: "Find me heat treatment suppliers"
              │
              ▼
┌─────────────────────────┐
│   Domain Classifier     │ → domain: "supplier" (0.95)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Intent Classifier     │ → intent: "supplier_search" (0.92)
│   (Supplier Domain)     │   entities: {processes: ["heat_treatment"]}
└─────────────────────────┘
```

---

## Estructura de API

```
/api/v1/chat                          # Unified (auto-routes to domain)
/api/v1/domains                       # List domains [{name, display_name}]
/api/v1/domains/{domain}/intents      # List domain intents

/api/v1/supplier/search               # Supplier-specific
/api/v1/supplier/compare
/api/v1/supplier/{id}/compliance

/api/v1/client/search                 # Client-specific
/api/v1/client/{id}/contracts
/api/v1/client/opportunities
```

---

## Roadmap de Migración

### Fase 1: Renombrado y Setup (1-2 días)
- [ ] Renombrar `valerie-chatbot` → `valerie-chatbot`
- [ ] Renombrar paquete `valerie` → `valerie`
- [ ] Actualizar imports, configs, y documentación
- [ ] Push a GitHub

### Fase 2: Core Framework (1-2 semanas)
- [ ] Crear `/src/valerie/core/domain/` con BaseDomain y DomainRegistry
- [ ] Crear `/src/valerie/core/state/` con CoreState y CompositeState
- [ ] Crear `/src/valerie/core/intents/` con MultiDomainClassifier
- [ ] Crear `/src/valerie/core/graph/composer.py`
- [ ] Mover infrastructure a `/src/valerie/infrastructure/`

### Fase 3: Migrar Supplier Domain (1 semana)
- [ ] Crear `/src/valerie/domains/supplier/`
- [ ] Implementar `SupplierDomain` class
- [ ] Mover agents existentes preservando lógica
- [ ] Crear `SupplierIntent` enum separado
- [ ] Crear `SupplierState` extension
- [ ] Crear `config/domains/supplier.yaml`

### Fase 4: Client Domain (2 semanas)
- [ ] Crear `/src/valerie/domains/client/`
- [ ] Implementar `ClientDomain` class
- [ ] Crear agents: ClientSearchAgent, SalesAgent, ContractAgent
- [ ] Definir `ClientIntent` enum
- [ ] Crear `ClientState` extension
- [ ] Integrar con Oracle Fusion Customer APIs

### Fase 5: Testing y Documentación (1 semana)
- [ ] Tests de clasificación cross-domain
- [ ] Tests de cambio de dominio mid-conversation
- [ ] Crear template `_template/` para nuevos dominios
- [ ] Documentar proceso de creación de dominios

---

## Client Domain: Agentes Propuestos

| Agente | Propósito | Oracle Fusion APIs |
|--------|-----------|-------------------|
| **ClientSearchAgent** | Buscar clientes por industria, tier, región | `/accounts`, `/customers` |
| **SalesAgent** | Gestionar oportunidades y pipeline | `/opportunities`, `/leads` |
| **ContractAgent** | Validar contratos y términos | `/contracts`, `/agreements` |
| **CreditCheckAgent** | Verificar crédito y riesgo financiero | `/creditProfiles` |
| **RelationshipAgent** | Historial de interacciones | `/activities`, `/contacts` |

### Client Intents

```python
class ClientIntent(str, Enum):
    CLIENT_SEARCH = "client_search"
    CLIENT_DETAILS = "client_details"
    OPPORTUNITY_STATUS = "opportunity_status"
    CONTRACT_CHECK = "contract_check"
    CREDIT_ASSESSMENT = "credit_assessment"
    RELATIONSHIP_HISTORY = "relationship_history"
```

---

## Decisiones de Arquitectura

| Decisión | Elección | Razón |
|----------|----------|-------|
| **Domain Discovery** | Auto-discovery via `pkgutil` | Plug-and-play sin config manual |
| **State Pattern** | Composite State + Extensions | Evita state bloat, type-safe |
| **Classification** | Two-phase (domain → intent) | Mejor accuracy, escalable |
| **API Structure** | Domain-prefixed routes | Claridad, documentación automática |
| **Config Format** | YAML por dominio | Familiar, fácil de editar |
| **Graph Building** | Dynamic from registry | No hardcoding, hot-reload posible |

---

## Próximos Pasos Inmediatos

1. **Aprobar este plan**
2. **Renombrar repositorio y paquete** a `valerie-chatbot` / `valerie`
3. **Comenzar Fase 2** (Core Framework)

¿Procedo con el renombramiento?
