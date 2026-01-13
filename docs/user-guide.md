# Valerie Supplier Chatbot - User Guide

## Overview

Valerie Supplier Chatbot is an AI-powered assistant that helps aerospace procurement teams find, evaluate, and compare surface finishing suppliers. It integrates with Oracle Fusion Cloud ERP to provide real-time supplier data.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An LLM provider (7 options: Ollama, Groq, Gemini, Anthropic, Bedrock, Azure OpenAI, or LightLLM)
- Optional: Oracle Fusion Cloud access for live data

### Installation

```bash
# Clone the repository
cd valerie-chatbot

# Run installation script
./install.sh

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Quick Start with Free LLM (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download a model
ollama pull llama3.2

# Start Ollama server
ollama serve

# Start the chatbot CLI
source venv/bin/activate
python -m valerie.cli chat
```

## Using the Chatbot

### CLI Interface

Start an interactive session:

```bash
python -m valerie.cli chat
```

**Available Commands:**
- `exit` or `quit` - Exit the chatbot
- `clear` - Clear conversation history
- `debug` - Toggle debug mode (shows agent activity)
- `help` - Show available commands

### Example Conversations

**Finding Suppliers:**
```
You: Find heat treatment suppliers with Nadcap certification
Assistant: I found 5 suppliers matching your criteria...
```

**Comparing Suppliers:**
```
You: Compare AeroTech and PrecisionCoat for anodizing
Assistant: Here's a comparison of both suppliers...
```

**Technical Questions:**
```
You: What's the difference between Type II and Type III anodizing?
Assistant: Type II anodizing produces a thinner coating (0.0001-0.001")...
```

**Risk Assessment:**
```
You: What are the risks with supplier SUP-001?
Assistant: Risk assessment for SUP-001 shows...
```

### REST API

Start the API server:

```bash
uvicorn valerie.api.main:app --reload
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat` | POST | Send a chat message |
| `/api/v1/sessions/{id}` | GET | Get session details |
| `/api/v1/suppliers/search` | POST | Direct supplier search |
| `/docs` | GET | API documentation (Swagger UI) |

**Example API Request:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find heat treatment suppliers"}'
```

**Response:**
```json
{
  "session_id": "abc-123",
  "response": "I found 3 qualified suppliers...",
  "intent": "supplier_search",
  "suppliers": [...],
  "metadata": {...}
}
```

### WebSocket Streaming

For real-time streaming responses:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/my-session');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'connected':
      console.log('Connected:', data.data.session_id);
      break;
    case 'agent_start':
      console.log('Agent started:', data.data.display_name);
      break;
    case 'stream_chunk':
      process.stdout.write(data.data.chunk);
      break;
    case 'stream_end':
      console.log('\nComplete!');
      break;
  }
};

// Send a message
ws.send(JSON.stringify({
  type: 'message',
  content: 'Find suppliers for passivation'
}));
```

### Demo UI (Streamlit)

For a visual interface:

```bash
cd demo
streamlit run app.py
```

Access at http://localhost:8501

**Features:**
- Chat interface with message history
- Real-time agent activity panel
- Pre-built demo scenarios
- Works without API key (demo mode)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VALERIE_LLM_PROVIDER` | LLM provider to use | `ollama` |
| `VALERIE_OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `VALERIE_OLLAMA_MODEL` | Ollama model name | `llama3.2` |
| `VALERIE_GROQ_API_KEY` | Groq API key | - |
| `VALERIE_ANTHROPIC_API_KEY` | Anthropic API key | - |
| `VALERIE_ORACLE_BASE_URL` | Oracle Fusion URL | `http://localhost:3000` |

### LLM Provider Options (7 Providers)

**1. Ollama (Free, Local)**
```bash
export VALERIE_LLM_PROVIDER=ollama
export VALERIE_OLLAMA_MODEL=llama3.2
```

**2. Groq (Free Cloud)**
```bash
export VALERIE_LLM_PROVIDER=groq
export VALERIE_GROQ_API_KEY=gsk_xxx...
```

**3. Gemini (Free Cloud, 2M context)**
```bash
export VALERIE_LLM_PROVIDER=gemini
export VALERIE_GEMINI_API_KEY=AIzaSy_xxx...
```

**4. Anthropic Claude (Paid)**
```bash
export VALERIE_LLM_PROVIDER=anthropic
export VALERIE_ANTHROPIC_API_KEY=sk-ant-xxx...
```

**5. AWS Bedrock (Paid)**
```bash
export VALERIE_LLM_PROVIDER=bedrock
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=xxx...
export AWS_DEFAULT_REGION=us-east-1
```

**6. Azure OpenAI (Paid)**
```bash
export VALERIE_LLM_PROVIDER=azure_openai
export AZURE_OPENAI_API_KEY=xxx...
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo
```

**7. LightLLM (On-Premise)**
```bash
export VALERIE_LLM_PROVIDER=lightllm
export VALERIE_LIGHTLLM_BASE_URL=http://localhost:8080
```

## Supported Queries

### Supplier Search
- "Find suppliers for [process]"
- "Show me [certification] certified suppliers"
- "List suppliers in [location]"

### Supplier Comparison
- "Compare [supplier A] and [supplier B]"
- "Which supplier is better for [process]?"
- "Show differences between these suppliers"

### Technical Questions
- "What is [process name]?"
- "Explain the difference between [A] and [B]"
- "What specifications apply to [material]?"

### Risk Assessment
- "Assess risk for [supplier]"
- "What are the risks with [supplier]?"
- "Show risk factors for my suppliers"

### Compliance Checks
- "Check compliance for [supplier]"
- "Verify [certification] for [supplier]"
- "Which suppliers have expiring certifications?"

## Human-in-the-Loop (HITL)

Certain decisions require human approval:

1. **ITAR-related queries** - Any defense/export-controlled items
2. **High-risk suppliers** - Suppliers with risk score > 0.7
3. **Low confidence** - When AI confidence is < 70%

When HITL is triggered, the system will pause and request approval before proceeding.

## Troubleshooting

### Common Issues

**"No LLM provider available"**
- Check that Ollama is running: `ollama serve`
- Verify API keys are set correctly
- Check network connectivity

**"Oracle connection failed"**
- Start the mock server: `cd oracle-fusion-mock-server && npm start`
- Or configure real Oracle credentials

**"Graph compilation failed"**
- Check Python version (3.11+ required)
- Reinstall dependencies: `pip install -r requirements.txt`

### Debug Mode

Enable debug mode for detailed information:

```bash
# CLI
python -m valerie.cli chat --debug

# Or toggle during session
You: debug
Debug mode: enabled
```

### Logs

View application logs:

```bash
# Default log location
tail -f logs/chatbot.log

# Or set log level
export VALERIE_LOG_LEVEL=DEBUG
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/ismaeldosil/valerie-chatbot/issues
- Documentation: See `/docs` folder
