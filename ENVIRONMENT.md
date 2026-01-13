# Valerie Chatbot - Environment Variables

Este documento contiene todas las variables de entorno necesarias para desplegar Valerie Chatbot.

## GitHub Secrets (para CI/CD)

| Variable | Descripción | Cómo obtener |
|----------|-------------|--------------|
| `RAILWAY_TOKEN` | Token de Railway para deploys | Railway Dashboard → Account Settings → Tokens → Create Token |

---

## Variables de Entorno - Railway Services

### Servicio: `valerie` (API)

#### Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `VALERIE_ANTHROPIC_API_KEY` | API key de Anthropic para Claude | `sk-ant-api03-xxx...` |

#### Opcionales (tienen defaults)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VALERIE_LLM_PROVIDER` | `ollama` | Provider por defecto: `anthropic`, `groq`, `gemini`, `ollama` |
| `VALERIE_LLM_FALLBACK` | `ollama,lightllm,groq,gemini,anthropic` | Cadena de fallback (comma-separated) |
| `VALERIE_GROQ_API_KEY` | - | API key de Groq (gratis) |
| `VALERIE_GEMINI_API_KEY` | - | API key de Google Gemini (gratis con limits) |
| `VALERIE_REDIS_URL` | `redis://localhost:6379` | URL de Redis para sesiones |
| `VALERIE_ORACLE_BASE_URL` | `http://localhost:3000` | URL del Oracle Fusion Mock |

---

### Servicio: `valerie-ui` (Streamlit Demo)

#### Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `VALERIE_ANTHROPIC_API_KEY` | API key de Anthropic para Claude | `sk-ant-api03-xxx...` |
| `VALERIE_LLM_PROVIDER` | Provider por defecto | `anthropic` |
| `VALERIE_LLM_FALLBACK` | Cadena de fallback | `groq,anthropic` |

#### Opcionales

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VALERIE_GROQ_API_KEY` | - | API key de Groq (gratis) |
| `VALERIE_GEMINI_API_KEY` | - | API key de Google Gemini (gratis con limits) |

---

## Configuración Recomendada para Producción

### API (`valerie`)

```env
# LLM Configuration
VALERIE_LLM_PROVIDER=anthropic
VALERIE_LLM_FALLBACK=gemini,groq,anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Optional: Free providers as fallback
VALERIE_GROQ_API_KEY=gsk_xxxxx
VALERIE_GEMINI_API_KEY=AIzaSy_xxxxx

# Redis (if using sessions)
VALERIE_REDIS_URL=redis://your-redis-url:6379

# Oracle Fusion
VALERIE_ORACLE_BASE_URL=https://your-oracle-instance.oraclecloud.com
```

### UI (`valerie-ui`)

```env
# LLM Configuration (same keys as API)
VALERIE_LLM_PROVIDER=anthropic
VALERIE_LLM_FALLBACK=gemini,groq,anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Optional: Free providers as fallback
VALERIE_GROQ_API_KEY=gsk_xxxxx
VALERIE_GEMINI_API_KEY=AIzaSy_xxxxx
```

---

## Obtener API Keys

### Anthropic (Claude)
1. Ir a https://console.anthropic.com/
2. Crear cuenta o iniciar sesión
3. Settings → API Keys → Create Key
4. **Costo**: ~$3 por millón de tokens (Claude 3.5 Sonnet)

### Groq (Gratis)
1. Ir a https://console.groq.com/
2. Crear cuenta con GitHub/Google
3. API Keys → Create API Key
4. **Costo**: GRATIS (30 req/min, 14,400 req/día)

### Google Gemini (Gratis)
1. Ir a https://aistudio.google.com/app/apikey
2. Crear cuenta con Google
3. Get API Key → Create API Key in new project
4. **Costo**: GRATIS (15 req/min, 1M tokens/min)
5. **Modelos**: gemini-1.5-flash (rápido), gemini-1.5-pro (mejor calidad, 2M context)

### Railway Token
1. Ir a https://railway.app/
2. Account Settings → Tokens
3. Create New Token
4. Copiar y agregar como GitHub Secret

---

## URLs de Producción

| Servicio | URL | Descripción |
|----------|-----|-------------|
| API | https://web-production-d82d.up.railway.app | REST API + WebSocket |
| API Docs | https://web-production-d82d.up.railway.app/docs | Swagger UI |
| API Health | https://web-production-d82d.up.railway.app/health | Health check |
| UI | (configurar en Railway) | Streamlit Demo |

---

## Notas Importantes

1. **NO commitear API keys** - Usar Railway Variables o GitHub Secrets
2. **Ollama no funciona en Railway** - Solo funciona con servidor local
3. **LightLLM no disponible** - Requiere servidor dedicado
4. **Groq es gratis** - Buena opción para desarrollo/testing (rate limits)
5. **Gemini es gratis** - Excelente opción con 2M context window
6. **Anthropic para producción** - Mejor calidad, costo por uso

## Proveedores LLM Disponibles

| Provider | Tipo | Costo | Contexto | Modelos |
|----------|------|-------|----------|---------|
| Ollama | Local | Gratis | Varía | llama3.2, codellama |
| LightLLM | On-premise | Gratis | Varía | llama-70b |
| Groq | Cloud | Gratis | 32K | llama-3.3-70b, mixtral |
| Gemini | Cloud | Gratis | 2M | gemini-1.5-flash, gemini-1.5-pro |
| Anthropic | Cloud | Pagado | 200K | claude-sonnet-4, claude-opus-4 |
| Bedrock | Cloud (AWS) | Pagado | Varía | Claude, Llama, Titan |
| Azure OpenAI | Cloud (Azure) | Pagado | 128K | gpt-4-turbo, gpt-4o |
