# Sprint 16: Docker Production Infrastructure

## Resumen Ejecutivo

Completar la infraestructura Docker para deployment production-ready del Valerie Supplier Chatbot.

**Estado Actual**: Código 100% completo, infraestructura Docker ~60% completa
**Objetivo**: Infraestructura 100% production-ready con observabilidad completa

---

## Tickets

### VSC-167: Actualizar docker-compose.yml con Redis Session Habilitado

**Prioridad**: CRÍTICA | **Esfuerzo**: S | **Dependencias**: Ninguna

**Problema**:
El docker-compose.yml actual NO habilita Redis para sesiones. Las sesiones usan InMemorySessionStore por defecto, lo que significa que se pierden al reiniciar el container.

**Archivos a Modificar**:
- `docker-compose.yml`
- `docker-compose.dev.yml`

**Cambios Requeridos**:
```yaml
environment:
  - VALERIE_SESSION_STORE=redis
  - VALERIE_SESSION_REDIS_URL=redis://redis:6379
  - VALERIE_SESSION_TTL=3600
```

**Criterios de Aceptación**:
- [ ] Variable VALERIE_SESSION_STORE=redis en docker-compose.yml
- [ ] Variable VALERIE_SESSION_REDIS_URL apunta a servicio redis
- [ ] Dependencia explícita de API hacia Redis con healthcheck
- [ ] Sesiones persisten después de reiniciar API container

---

### VSC-168: Crear docker-compose.observability.yml

**Prioridad**: ALTA | **Esfuerzo**: M | **Dependencias**: VSC-167

**Descripción**:
Crear stack de observabilidad con Prometheus y Grafana como servicios Docker separados.

**Archivos a Crear**:
- `docker-compose.observability.yml`

**Servicios a Incluir**:
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    volumes:
      - ./config/grafana:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=valerie123
```

**Criterios de Aceptación**:
- [ ] Prometheus accesible en :9090
- [ ] Grafana accesible en :3001
- [ ] Prometheus scrapeando /metrics de API
- [ ] Datos persistentes en volumes

---

### VSC-169: Crear Configuración Prometheus

**Prioridad**: ALTA | **Esfuerzo**: M | **Dependencias**: VSC-168

**Descripción**:
Crear archivos de configuración para Prometheus incluyendo scrape config y alert rules.

**Archivos a Crear**:
- `config/prometheus/prometheus.yml`
- `config/prometheus/alert-rules.yml`

**Configuración prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'valerie-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics

rule_files:
  - 'alert-rules.yml'
```

**Alert Rules a Incluir**:
- High error rate (>5% en 5min)
- High latency (p95 > 10s)
- LLM provider down
- Redis connection lost

**Criterios de Aceptación**:
- [ ] prometheus.yml válido
- [ ] Alert rules definidas
- [ ] Prometheus carga configuración sin errores

---

### VSC-170: Crear Dashboards Grafana

**Prioridad**: MEDIA | **Esfuerzo**: L | **Dependencias**: VSC-168, VSC-169

**Descripción**:
Crear dashboards JSON para Grafana con métricas del sistema.

**Archivos a Crear**:
- `config/grafana/provisioning/datasources/prometheus.yml`
- `config/grafana/provisioning/dashboards/dashboard.yml`
- `config/grafana/dashboards/valerie-overview.json`
- `config/grafana/dashboards/valerie-llm-providers.json`
- `config/grafana/dashboards/valerie-agents.json`

**Dashboards**:

1. **Overview Dashboard**:
   - Request rate (req/s)
   - Error rate (%)
   - Latency p50/p95/p99
   - Active sessions

2. **LLM Providers Dashboard**:
   - Requests por provider
   - Latency por provider/model
   - Token usage (input/output)
   - Provider availability

3. **Agents Dashboard**:
   - Invocaciones por agente
   - Duration por agente
   - Error rate por agente

**Criterios de Aceptación**:
- [ ] 3 dashboards creados
- [ ] Datasource Prometheus configurado
- [ ] Dashboards se cargan automáticamente
- [ ] Gráficos muestran datos reales

---

### VSC-171: Crear docker-compose.langfuse.yml

**Prioridad**: MEDIA | **Esfuerzo**: M | **Dependencias**: Ninguna

**Descripción**:
Crear configuración para Langfuse self-hosted como alternativa a cloud.

**Archivos a Crear**:
- `docker-compose.langfuse.yml`

**Servicios**:
```yaml
services:
  langfuse-server:
    image: langfuse/langfuse:latest
    ports: ["3002:3000"]
    environment:
      - DATABASE_URL=postgresql://langfuse:langfuse@langfuse-db:5432/langfuse
      - NEXTAUTH_SECRET=your-secret-here
      - NEXTAUTH_URL=http://localhost:3002
    depends_on:
      - langfuse-db

  langfuse-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=langfuse
      - POSTGRES_DB=langfuse
    volumes:
      - langfuse-db-data:/var/lib/postgresql/data
```

**Criterios de Aceptación**:
- [ ] Langfuse UI accesible en :3002
- [ ] Base de datos PostgreSQL funcional
- [ ] API puede enviar traces a Langfuse local
- [ ] Variables LANGFUSE_* documentadas

---

### VSC-172: Actualizar requirements.txt

**Prioridad**: CRÍTICA | **Esfuerzo**: S | **Dependencias**: Ninguna

**Problema**:
El requirements.txt está desactualizado respecto a pyproject.toml. Faltan dependencias de observabilidad.

**Archivo a Modificar**:
- `requirements.txt`

**Dependencias Faltantes**:
```
structlog>=24.0.0
prometheus-client>=0.20.0
langfuse>=2.0.0
pyjwt>=2.8.0
```

**Criterios de Aceptación**:
- [ ] requirements.txt sincronizado con pyproject.toml
- [ ] Docker build exitoso con nuevas dependencias
- [ ] Imports funcionan correctamente

---

### VSC-173: Crear .env.production

**Prioridad**: ALTA | **Esfuerzo**: S | **Dependencias**: Ninguna

**Descripción**:
Crear archivo de variables de entorno para producción con todos los valores necesarios.

**Archivo a Crear**:
- `.env.production`

**Variables a Incluir**:
```bash
# Environment
VALERIE_ENV=production

# LLM Configuration
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-xxx
VALERIE_USE_PAID_LLM=true

# Session Store
VALERIE_SESSION_STORE=redis
VALERIE_SESSION_REDIS_URL=redis://redis:6379
VALERIE_SESSION_TTL=3600

# Observability
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=http://langfuse-server:3000

# Security
JWT_SECRET_KEY=your-256-bit-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

**Criterios de Aceptación**:
- [ ] Todas las variables documentadas
- [ ] Valores placeholder seguros
- [ ] .env.production en .gitignore
- [ ] .env.production.example creado (sin secrets)

---

### VSC-174: Crear docker-compose.prod.yml Unificado

**Prioridad**: ALTA | **Esfuerzo**: M | **Dependencias**: VSC-167 a VSC-173

**Descripción**:
Crear docker-compose de producción que incluya todos los servicios con configuración para escalar.

**Archivo a Crear**:
- `docker-compose.prod.yml`

**Características**:
- API con múltiples réplicas
- Redis con persistencia
- Prometheus + Grafana
- Langfuse (opcional)
- Health checks completos
- Resource limits
- Logging driver configurado

**Estructura**:
```yaml
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Criterios de Aceptación**:
- [ ] 3 réplicas de API funcionando
- [ ] Load balancing entre réplicas
- [ ] Todos los servicios con healthchecks
- [ ] Resource limits definidos
- [ ] Volumes para persistencia

---

### VSC-175: Crear Documentación de Deployment

**Prioridad**: MEDIA | **Esfuerzo**: M | **Dependencias**: VSC-174

**Descripción**:
Crear documentación completa de deployment para operaciones.

**Archivo a Crear**:
- `DEPLOYMENT.md`

**Contenido**:
1. Quick Start (desarrollo)
2. Production Deployment
3. Configuración de LLM Providers
4. Configuración de Observabilidad
5. Scaling y High Availability
6. Troubleshooting
7. Backup y Recovery

**Criterios de Aceptación**:
- [ ] Instrucciones paso a paso
- [ ] Comandos copy-paste
- [ ] Diagramas de arquitectura
- [ ] FAQ común

---

## Resumen de Archivos

| Ticket | Archivos a Crear/Modificar |
|--------|---------------------------|
| VSC-167 | docker-compose.yml, docker-compose.dev.yml |
| VSC-168 | docker-compose.observability.yml |
| VSC-169 | config/prometheus/prometheus.yml, config/prometheus/alert-rules.yml |
| VSC-170 | config/grafana/provisioning/*, config/grafana/dashboards/*.json |
| VSC-171 | docker-compose.langfuse.yml |
| VSC-172 | requirements.txt |
| VSC-173 | .env.production, .env.production.example |
| VSC-174 | docker-compose.prod.yml |
| VSC-175 | DEPLOYMENT.md |

---

## Orden de Ejecución

```
VSC-172 (requirements.txt) ─┐
VSC-173 (.env.production)  ─┼─▶ VSC-167 (docker-compose.yml) ─┐
                            │                                  │
VSC-168 (observability) ────┤                                  ├─▶ VSC-174 (prod.yml) ─▶ VSC-175 (docs)
VSC-169 (prometheus) ───────┤                                  │
VSC-170 (grafana) ──────────┤                                  │
VSC-171 (langfuse) ─────────┘──────────────────────────────────┘
```

**Estimación Total**: ~2 horas de implementación
