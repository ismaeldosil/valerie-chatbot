# Guía de Customización de Dominio - Valerie Multi-Agent Chatbot

## Resumen Ejecutivo

Este documento permite adaptar el sistema multi-agente Valerie a **cualquier dominio de negocio**. La arquitectura de 15 agentes es genérica y reutilizable - solo necesitas cambiar la configuración del dominio, los prompts, y los datos.

---

## Arquitectura del Sistema (Invariante)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAPA DE INFRAESTRUCTURA                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Guardrails  │  │    HITL     │  │Observability│  │  Fallback   │    │
│  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                      ┌─────────────┐    │
│                                                      │ Evaluation  │    │
│                                                      │   Agent     │    │
│                                                      └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          CAPA DE NEGOCIO                                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      ORCHESTRATOR AGENT                          │   │
│  │              (Coordina todo el flujo de agentes)                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│           ┌────────────────────────┼────────────────────────┐          │
│           ▼                        ▼                        ▼          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│  │ Intent          │    │ Memory &        │    │ Response        │    │
│  │ Classifier      │    │ Context         │    │ Generation      │    │
│  └────────┬────────┘    └─────────────────┘    └─────────────────┘    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│  │ Entity Search   │    │ Validation      │    │ Comparison      │    │
│  │ Agent           │    │ Agent           │    │ Agent           │    │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│  │ External        │    │ Domain          │    │ Risk            │    │
│  │ Integration     │    │ Expertise       │    │ Assessment      │    │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Los 15 Agentes y sus Roles Genéricos

### Capa de Infraestructura (5 agentes) - NO MODIFICAR

| # | Agente | Rol Genérico | Qué hace |
|---|--------|--------------|----------|
| 11 | **Guardrails** | Seguridad | Valida inputs, detecta inyecciones, protege PII |
| 12 | **HITL** | Supervisión Humana | Maneja aprobaciones y escalamientos |
| 13 | **Observability** | Monitoreo | Tracing, métricas, logging |
| 14 | **Fallback** | Resiliencia | Circuit breaker, retry, degradación |
| 15 | **Evaluation** | Calidad | Evalúa respuestas, feedback loop |

### Capa de Negocio (10 agentes) - CUSTOMIZAR

| # | Agente | Rol Genérico | Ejemplo Suppliers | Ejemplo Otro Dominio |
|---|--------|--------------|-------------------|----------------------|
| 01 | **Orchestrator** | Coordinador | Coordina búsqueda de proveedores | Coordina cualquier flujo |
| 02 | **Intent Classifier** | Clasificador | Detecta intención de procurement | Detecta intención del dominio |
| 03 | **Entity Search** | Buscador | Busca proveedores | Busca entidades del dominio |
| 04 | **Validation** | Validador | Valida compliance/certificaciones | Valida reglas del dominio |
| 05 | **Comparison** | Comparador | Compara proveedores | Compara entidades |
| 06 | **External Integration** | Integrador | Oracle Fusion ERP | Cualquier API externa |
| 07 | **Domain Expertise** | Experto | Procesos de tratamiento | Conocimiento del dominio |
| 08 | **Risk Assessment** | Evaluador de Riesgo | Riesgo de proveedores | Riesgo del dominio |
| 09 | **Response Generation** | Generador | Genera respuestas de procurement | Genera respuestas del dominio |
| 10 | **Memory & Context** | Memoria | Contexto de conversación | Contexto de conversación |

---

## Configuración del Nuevo Dominio

### Paso 1: Definir el Dominio

Crea un archivo `config/domain.yaml` con la siguiente estructura:

```yaml
# config/domain.yaml
domain:
  name: "Mi Nuevo Dominio"
  description: "Descripción del problema que resuelve el chatbot"

  # Entidad principal que el chatbot maneja
  primary_entity:
    name: "producto"           # singular
    name_plural: "productos"   # plural
    description: "Productos del catálogo"

  # Intenciones que el chatbot reconoce
  intents:
    - name: search
      description: "Buscar entidades"
      examples:
        - "buscar productos de electrónica"
        - "encuentra artículos baratos"

    - name: compare
      description: "Comparar entidades"
      examples:
        - "compara estos dos productos"
        - "cuál es mejor entre A y B"

    - name: validate
      description: "Validar reglas/compliance"
      examples:
        - "este producto cumple las normas"
        - "verificar certificación"

    - name: risk
      description: "Evaluar riesgos"
      examples:
        - "qué riesgo tiene este proveedor"
        - "análisis de riesgo"

    - name: info
      description: "Información del dominio"
      examples:
        - "cómo funciona X"
        - "explícame el proceso de Y"

    - name: general
      description: "Preguntas generales"
      examples:
        - "hola"
        - "ayuda"

  # Sistema externo a integrar (opcional)
  external_system:
    name: "Mi ERP"
    type: "rest_api"
    base_url_env: "VALERIE_EXTERNAL_API_URL"
    auth_type: "oauth2"  # oauth2 | api_key | basic | none

  # Reglas de validación del dominio
  validation_rules:
    - name: "Certificación ISO"
      field: "certifications"
      required: true
    - name: "Precio mínimo"
      field: "price"
      min_value: 0

  # Campos de riesgo a evaluar
  risk_factors:
    - name: "financial_risk"
      weight: 0.3
    - name: "delivery_risk"
      weight: 0.3
    - name: "quality_risk"
      weight: 0.4

  # Triggers para HITL (Human-in-the-Loop)
  hitl_triggers:
    - condition: "risk_score > 0.8"
      action: "require_approval"
    - condition: "value > 100000"
      action: "require_approval"
```

### Paso 2: Crear el Modelo de Datos

Crea los modelos Pydantic en `src/valerie/domains/{domain}/`:

```python
# src/valerie/domains/my_domain/models.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MyEntity(BaseModel):
    """Entidad principal del dominio"""
    id: str
    name: str
    description: Optional[str] = None
    category: str
    attributes: dict = {}
    created_at: datetime

class SearchCriteria(BaseModel):
    """Criterios de búsqueda"""
    query: Optional[str] = None
    category: Optional[str] = None
    filters: dict = {}
    limit: int = 10

class ValidationResult(BaseModel):
    """Resultado de validación"""
    is_valid: bool
    rules_passed: List[str]
    rules_failed: List[str]
    details: dict = {}

class RiskAssessment(BaseModel):
    """Evaluación de riesgo"""
    entity_id: str
    overall_score: float  # 0.0 - 1.0
    risk_factors: dict
    recommendations: List[str]
```

---

## Archivos a Modificar por Dominio

### Archivos de Configuración

| Archivo | Qué cambiar |
|---------|-------------|
| `config/domain.yaml` | Definición completa del dominio |
| `config/model-registry.yaml` | Modelos LLM por agente (opcional) |
| `config/intents.yaml` | Intenciones y ejemplos |

### Prompts de Agentes (../valerie-docs/prompts/)

| Archivo | Qué cambiar |
|---------|-------------|
| `01-orchestrator-agent.md` | Flujo específico del dominio |
| `02-intent-classifier-agent.md` | Intenciones del dominio |
| `03-entity-search-agent.md` | Lógica de búsqueda |
| `04-validation-agent.md` | Reglas de validación |
| `05-comparison-agent.md` | Criterios de comparación |
| `06-external-integration-agent.md` | API externa a integrar |
| `07-domain-expertise-agent.md` | Conocimiento del dominio |
| `08-risk-assessment-agent.md` | Factores de riesgo |
| `09-response-generation-agent.md` | Tono y formato de respuestas |
| `10-memory-context-agent.md` | Qué recordar del contexto |

### Código Fuente (src/valerie/)

| Archivo | Qué cambiar |
|---------|-------------|
| `domains/{domain}/models.py` | Modelos de datos |
| `domains/{domain}/intents.py` | Enum de intenciones |
| `domains/{domain}/state.py` | Estado específico |
| `agents/*.py` | Lógica de agentes (mínimo) |

---

## Template de Prompt para Nuevo Dominio

Usa esta plantilla para cada agente:

```markdown
# {Nombre del Agente} Agent

## Rol
Eres el **{Nombre del Agente}** para el sistema de {Descripción del Dominio}.

## Objetivo
{Describir el objetivo específico del agente en este dominio}

## Contexto del Dominio
- **Entidad Principal**: {nombre de la entidad}
- **Sistema Externo**: {nombre del sistema}
- **Usuarios**: {tipo de usuarios}

## Input
```json
{
  "query": "string",
  "context": {},
  "domain_specific_field": "value"
}
```

## Output
```json
{
  "result": {},
  "confidence": 0.95,
  "metadata": {}
}
```

## Reglas de Negocio
1. {Regla 1}
2. {Regla 2}
3. {Regla 3}

## Ejemplos
### Ejemplo 1: {Descripción}
**Input**: {ejemplo de input}
**Output**: {ejemplo de output}
```

---

## Ejemplos de Dominios Adaptados

### Ejemplo 1: E-commerce Product Recommendations

```yaml
domain:
  name: "Product Recommendations"
  primary_entity:
    name: "product"
    name_plural: "products"
  intents:
    - search: "buscar productos"
    - compare: "comparar productos"
    - recommend: "recomendar productos"
    - review: "ver reseñas"
  external_system:
    name: "Shopify API"
    type: "rest_api"
```

### Ejemplo 2: HR Recruitment Assistant

```yaml
domain:
  name: "Recruitment Assistant"
  primary_entity:
    name: "candidate"
    name_plural: "candidates"
  intents:
    - search: "buscar candidatos"
    - evaluate: "evaluar candidato"
    - schedule: "agendar entrevista"
    - compare: "comparar candidatos"
  external_system:
    name: "Workday API"
    type: "rest_api"
```

### Ejemplo 3: IT Support Chatbot

```yaml
domain:
  name: "IT Support"
  primary_entity:
    name: "ticket"
    name_plural: "tickets"
  intents:
    - create: "crear ticket"
    - status: "estado de ticket"
    - troubleshoot: "resolver problema"
    - escalate: "escalar a humano"
  external_system:
    name: "ServiceNow API"
    type: "rest_api"
```

### Ejemplo 4: Legal Document Assistant

```yaml
domain:
  name: "Legal Assistant"
  primary_entity:
    name: "document"
    name_plural: "documents"
  intents:
    - search: "buscar documentos"
    - analyze: "analizar contrato"
    - compare: "comparar versiones"
    - validate: "validar compliance"
  external_system:
    name: "Document Management System"
    type: "rest_api"
```

---

## Checklist de Migración a Nuevo Dominio

### Fase 1: Configuración (1-2 días)
- [ ] Crear `config/domain.yaml` con definición del dominio
- [ ] Definir intenciones en `config/intents.yaml`
- [ ] Configurar variables de entorno en `.env`

### Fase 2: Modelos de Datos (1-2 días)
- [ ] Crear modelos Pydantic en `src/valerie/domains/{domain}/`
- [ ] Definir estado del dominio
- [ ] Crear schemas de validación

### Fase 3: Prompts (2-3 días)
- [ ] Adaptar `01-orchestrator-agent.md`
- [ ] Adaptar `02-intent-classifier-agent.md`
- [ ] Adaptar `03-entity-search-agent.md`
- [ ] Adaptar `04-validation-agent.md`
- [ ] Adaptar `05-comparison-agent.md`
- [ ] Adaptar `06-external-integration-agent.md`
- [ ] Adaptar `07-domain-expertise-agent.md`
- [ ] Adaptar `08-risk-assessment-agent.md`
- [ ] Adaptar `09-response-generation-agent.md`
- [ ] Adaptar `10-memory-context-agent.md`

### Fase 4: Integración Externa (2-3 días)
- [ ] Implementar cliente API para sistema externo
- [ ] Configurar autenticación
- [ ] Crear mock server para desarrollo

### Fase 5: Testing (2-3 días)
- [ ] Tests unitarios de agentes
- [ ] Tests de integración
- [ ] Tests end-to-end

### Fase 6: Demo y Documentación (1-2 días)
- [ ] Adaptar demo UI
- [ ] Actualizar documentación
- [ ] Crear datos de ejemplo

---

## Estructura de Carpetas del Proyecto

```
valerie-chatbot/
├── config/
│   ├── domain.yaml              # ⭐ CONFIGURAR PARA TU DOMINIO
│   ├── intents.yaml             # ⭐ DEFINIR INTENCIONES
│   ├── model-registry.yaml      # Modelos LLM
│   └── llm-providers.yaml       # Proveedores LLM
│
├── src/valerie/
│   ├── agents/                  # Agentes genéricos
│   │   ├── base.py
│   │   ├── orchestrator.py
│   │   ├── intent_classifier.py
│   │   └── ...
│   │
│   ├── domains/                 # ⭐ CREAR PARA TU DOMINIO
│   │   └── {my_domain}/
│   │       ├── __init__.py
│   │       ├── models.py        # Modelos de datos
│   │       ├── intents.py       # Enum de intenciones
│   │       ├── state.py         # Estado del dominio
│   │       └── integration.py   # Cliente API externa
│   │
│   ├── infrastructure/          # NO MODIFICAR
│   │   ├── guardrails.py
│   │   ├── hitl.py
│   │   ├── observability.py
│   │   └── ...
│   │
│   ├── llm/                     # NO MODIFICAR
│   │   ├── base.py
│   │   ├── ollama.py
│   │   ├── groq.py
│   │   └── ...
│   │
│   └── api/                     # NO MODIFICAR (solo endpoints custom)
│       ├── main.py
│       └── routes/
│
├── ../valerie-docs/              # Carpeta hermana (fuera de valerie-chatbot)
│   ├── prompts/                 # ⭐ ADAPTAR PARA TU DOMINIO
│   │   ├── 01-orchestrator-agent.md
│   │   ├── 02-intent-classifier-agent.md
│   │   └── ...
│   │
│   └── agents/                  # Especificaciones de agentes
│
└── tests/
    ├── unit/
    └── integration/
```

---

## Variables de Entorno Genéricas

```bash
# === LLM Configuration (NO CAMBIAR) ===
VALERIE_LLM_PROVIDER=ollama
VALERIE_OLLAMA_BASE_URL=http://localhost:11434
VALERIE_GROQ_API_KEY=
VALERIE_ANTHROPIC_API_KEY=

# === Domain Configuration (CONFIGURAR) ===
VALERIE_DOMAIN=my_domain
VALERIE_EXTERNAL_API_URL=https://api.example.com
VALERIE_EXTERNAL_API_KEY=your-api-key

# === Infrastructure (NO CAMBIAR) ===
VALERIE_REDIS_URL=redis://localhost:6379
VALERIE_HITL_ENABLED=true
VALERIE_GUARDRAILS_ENABLED=true
VALERIE_EVALUATION_ENABLED=true
```

---

## Contacto y Soporte

Para preguntas sobre adaptación a nuevos dominios:
- Revisar ejemplos en `../valerie-docs/examples/`
- Consultar documentación en `../valerie-docs/docs/`

---

*Documento generado: Diciembre 2025*
*Versión del Framework: 2.6.0*
