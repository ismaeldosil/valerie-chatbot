# Valerie Chatbot - Portability Guide

This document describes how to move the Valerie Chatbot project to a new location and continue development.

## What's Included in valerie-chatbot/

The `valerie-chatbot/` folder is self-contained with:

| Folder/File | Purpose |
|-------------|---------|
| `src/valerie/` | All source code |
| `tests/` | 609 tests |
| `config/` | Model registry, Grafana, Prometheus |
| `docker/` | Docker Compose files |
| `demo/` | Streamlit demo UI |
| `docs/` | Documentation |
| `AI_CONTEXT.md` | AI assistant context |
| `pyproject.toml` | Dependencies |

## External Dependencies (Sibling Folders)

These are outside `valerie-chatbot/` at the same level:

### 1. valerie-docs/
**Location**: `../valerie-docs/`

Development documentation, agent prompts, templates for new domains. Not part of the deployable product.

### 2. valerie-infrastructure/
**Location**: `../valerie-infrastructure/`

Contains Terraform, Kubernetes, Helm for enterprise deployments.

### 3. Oracle Fusion Mock Server
**Location**: `../oracle-fusion-mock-server/`

Mock server for Oracle API testing.

## Moving the Project

### Option 1: Copy valerie-chatbot Only (Minimal)

```bash
# Copy just the chatbot
cp -r valerie-chatbot /new/location/

# Install and run
cd /new/location/valerie-chatbot
uv sync
uv run python -m valerie.cli chat
```

### Option 2: Copy with Templates (Recommended)

```bash
# Create destination
mkdir -p /new/location/valerie-chatbot

# Copy chatbot
cp -r valerie-chatbot/* /new/location/valerie-chatbot/

# Copy development docs (optional, for domain customization)
cp -r valerie-docs /new/location/valerie-docs

# Install and run
cd /new/location/valerie-chatbot
uv sync
```

### Option 3: Copy Everything (Full Project)

```bash
# Copy entire project
cp -r suplier-chatbots /new/location/

# Navigate and install
cd /new/location/suplier-chatbots/valerie-chatbot
uv sync
```

## After Moving

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Verify Installation
```bash
# Run tests
uv run pytest tests/ -v

# Start CLI
uv run python -m valerie.cli chat
```

### 4. Start Development
```bash
# API server
uv run uvicorn valerie.api.main:app --reload

# Demo UI
uv run streamlit run demo/app.py
```

## Git Repository

If moving to a new git repository:

```bash
cd /new/location/valerie-chatbot

# Initialize new repo
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit - Valerie Chatbot v1.0.0"

# Add remote
git remote add origin https://github.com/your-org/valerie-chatbot.git
git push -u origin main
```

## Environment Variables Quick Reference

### Minimum Required (Free Development)
```bash
VALERIE_LLM_PROVIDER=ollama
VALERIE_OLLAMA_BASE_URL=http://localhost:11434
```

### Production
```bash
VALERIE_LLM_PROVIDER=anthropic
VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx
JWT_SECRET_KEY=your-secret-key
VALERIE_REDIS_URL=redis://localhost:6379
```

## Project Stats at Time of Export

- **Version**: 1.0.0
- **Tests**: 609 (79% coverage)
- **LLM Providers**: 7 (Ollama, Groq, Gemini, Anthropic, Bedrock, Azure, LightLLM)
- **Agents**: 15 (10 core + 5 infrastructure)
- **Python**: 3.11+
- **Last Updated**: 2025-12-22
