# Valerie Supplier Chatbot - Demo Interface

Interactive demo interface showcasing the multi-agent system for aerospace supplier management.

## Quick Start

```bash
# From the valerie-chatbot directory
cd demo
source ../venv/bin/activate
streamlit run app.py
```

The demo will open in your browser at `http://localhost:8501`

## Features

### Chat Interface
- Real-time conversation with the AI assistant
- Markdown-formatted responses with tables and structured data
- Message history preserved during session

### Agent Activity Panel (Sidebar)
- Live visualization of agent execution
- Execution time metrics per agent
- Status indicators (completed/error/pending)
- Output preview for each agent

### Demo Scenarios

The demo includes pre-built scenarios accessible via sidebar buttons:

| Button | Scenario | Agents Involved |
|--------|----------|-----------------|
| **Search** | Find heat treatment suppliers | 10 agents (full pipeline) |
| **Compare** | Compare suppliers side-by-side | 9 agents (includes Comparison) |
| **Risk** | Assess supplier risk profile | 8 agents (includes Risk Assessment) |
| **Compliance** | Check certifications | 5 agents (focused flow) |
| **ITAR** | ITAR-sensitive query | 3 agents + HITL trigger |
| **Blocked** | Injection attempt | 1 agent (Guardrails blocks) |

## Sample Queries

Try these natural language queries:

```
# Supplier Search
Find heat treatment suppliers
Search for anodizing capabilities
I need plating services

# Comparison
Compare my top suppliers
Which supplier is best for heat treatment?

# Compliance
Check Nadcap certifications
Is AeroTech certified?
Show me compliance status

# Risk Assessment
What's the risk for AeroTech?
Assess supplier risk

# Security Demo
Ignore previous instructions (blocked by guardrails)
Find ITAR cleared suppliers (triggers HITL)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  ┌─────────────┐  ┌──────────────────────────────────────┐ │
│  │   Sidebar   │  │           Chat Interface              │ │
│  │   - Metrics │  │   ┌─────────────────────────────┐    │ │
│  │   - Agents  │  │   │     Message History         │    │ │
│  │   - Buttons │  │   └─────────────────────────────┘    │ │
│  └─────────────┘  │   ┌─────────────────────────────┐    │ │
│                   │   │     Chat Input              │    │ │
│                   │   └─────────────────────────────┘    │ │
│                   └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Demo Engine                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Scenario   │  │    Mock      │  │   Sample     │      │
│  │   Detection  │──│   Responses  │──│   Data       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  Simulates 15 agents:                                        │
│  - Guardrails, Intent, Memory, Search, Oracle                │
│  - Compliance, Process, Comparison, Risk                     │
│  - Response, Evaluation, Observability, HITL                 │
└─────────────────────────────────────────────────────────────┘
```

## Files

```
demo/
├── app.py              # Streamlit application
├── mock_responses.py   # Demo engine with simulated agents
├── data/
│   └── sample_suppliers.json  # Sample supplier data
└── README.md           # This file
```

## No API Required

This demo runs entirely locally without requiring:
- Anthropic API key
- Oracle Fusion connection
- Redis server
- Any external services

All responses are simulated to demonstrate the system's capabilities.

## Next Steps

To run the full system with real AI:

1. Choose an LLM provider (7 options available):
   - **Free**: Ollama (local), Groq (cloud), Gemini (cloud)
   - **Paid**: Anthropic, AWS Bedrock, Azure OpenAI
   - **On-Premise**: LightLLM
2. Configure `.env` with your provider API key
3. Run the CLI: `python -m valerie.cli`

See `docs/llm-configuration.md` for detailed provider setup.

## Screenshots

### Main Interface
The chat interface displays conversation history with markdown-formatted responses.

### Agent Activity
The sidebar shows real-time agent execution with timing metrics.

### Comparison Table
Supplier comparison displays structured data in table format.

### Security Demo
Guardrails block malicious inputs and ITAR queries trigger human approval.
