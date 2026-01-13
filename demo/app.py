"""Valerie Supplier Chatbot - Demo Interface.

Run with: streamlit run demo/app.py
"""

import asyncio
import json
import os
import sys
import time

import streamlit as st
from mock_responses import AgentExecution, DemoEngine

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Try to import LLM provider and model registry
try:
    from valerie.llm import LLMConfig, LLMMessage
    from valerie.llm.base import MessageRole
    from valerie.llm.factory import get_available_provider
    from valerie.models import get_model_registry

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


def set_llm_provider(provider: str):
    """Set the LLM provider via environment variable."""
    os.environ["VALERIE_LLM_PROVIDER"] = provider
    if provider == "anthropic":
        os.environ["VALERIE_USE_PAID_LLM"] = "true"
    else:
        os.environ["VALERIE_USE_PAID_LLM"] = "false"

    # Update the model name in session state
    if LLM_AVAILABLE:
        try:
            registry = get_model_registry()
            registry.reload()  # Reload to pick up new provider
            model_name = registry.get_model(provider, "default")
            st.session_state.provider_name = f"{provider} ({model_name})"
            st.session_state.current_model = model_name
        except Exception:
            st.session_state.provider_name = provider
            st.session_state.current_model = "unknown"


def get_current_model_info() -> tuple[str, str]:
    """Get current provider and model name from registry."""
    if not LLM_AVAILABLE:
        return "N/A", "N/A"
    try:
        registry = get_model_registry()
        provider = registry.default_provider
        model = registry.get_model(provider, "default")
        return provider, model
    except Exception:
        return "unknown", "unknown"


# Page configuration
st.set_page_config(
    page_title="Valerie Supplier Chatbot",
    page_icon="aerospace",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Chat messages */
    .user-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1976d2;
    }

    .assistant-message {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #43a047;
    }

    /* Agent cards */
    .agent-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }

    .agent-card.running {
        border-left: 4px solid #ff9800;
        animation: pulse 1s infinite;
    }

    .agent-card.completed {
        border-left: 4px solid #4caf50;
    }

    .agent-card.error {
        border-left: 4px solid #f44336;
    }

    .agent-card.pending {
        border-left: 4px solid #9e9e9e;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }

    /* Header */
    .header-container {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }

    /* Status indicators */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }

    .status-dot.green { background-color: #4caf50; }
    .status-dot.yellow { background-color: #ff9800; }
    .status-dot.red { background-color: #f44336; }
    .status-dot.gray { background-color: #9e9e9e; }

    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "demo_engine" not in st.session_state:
    st.session_state.demo_engine = DemoEngine()
if "last_executions" not in st.session_state:
    st.session_state.last_executions = []
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0
if "live_mode" not in st.session_state:
    st.session_state.live_mode = False
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = "ollama"  # Default to free
if "current_model" not in st.session_state:
    st.session_state.current_model = "unknown"

# Initialize provider_name with actual model info from registry
if "provider_name" not in st.session_state:
    provider, model = get_current_model_info()
    st.session_state.provider_name = f"{provider} ({model})"
    st.session_state.current_model = model
    st.session_state.selected_provider = provider
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False

# Load supplier data for RAG
SUPPLIER_DATA = {}
try:
    data_path = os.path.join(os.path.dirname(__file__), "data", "sample_suppliers.json")
    with open(data_path) as f:
        SUPPLIER_DATA = json.load(f)
except Exception:
    pass


def get_system_debug_info() -> str:
    """Generate system debug information for the LLM context."""
    import platform
    from datetime import datetime

    provider = st.session_state.get("selected_provider", "unknown")
    model = st.session_state.get("current_model", "unknown")
    version = "2.5.0"

    # Determine model type and cost
    if provider == "ollama":
        model_type = "Local (Ollama)"
        cost = "FREE"
    elif provider in ["groq", "gemini"]:
        model_type = "Cloud API"
        cost = "FREE"
    elif provider == "anthropic":
        model_type = "Cloud API"
        cost = "PAID"
    else:
        model_type = "Unknown"
        cost = "Unknown"

    live_mode = st.session_state.get("live_mode", False)
    demo_status = "Disabled (Live)" if live_mode else "Enabled (Mock)"

    debug_info = f"""
## SYSTEM DEBUG INFORMATION (Debug Mode Enabled)

When users ask about system info, model details, or health status,
provide accurate information from this context:

### Current Configuration
- **LLM Provider**: {provider}
- **Model**: {model}
- **Model Type**: {model_type}
- **Cost**: {cost}

### System Information
- **Application**: Valerie Supplier Chatbot v{version}
- **Timestamp**: {datetime.now().isoformat()}
- **Platform**: {platform.system()} {platform.release()}
- **Python**: {platform.python_version()}

### Architecture
- **Core Agents**: Orchestrator, Intent Classifier, Supplier Search,
  Compliance, Comparison, Oracle Integration, Process Expertise,
  Risk Assessment, Response Generation, Memory (10 total)
- **Infrastructure**: Guardrails, Evaluation, Observability, HITL, Fallback
- **Orchestration**: LangGraph
- **Database**: Redis (sessions), Oracle Fusion (suppliers)

### Health Status
- **LLM**: Connected ({provider}/{model})
- **API**: Running
- **Demo Mode**: {demo_status}

### Debug Commands:
- "What model are you using?" - Returns current LLM info
- "System status" - Returns health check
- "Show configuration" - Returns current settings

IMPORTANT: When answering questions about yourself or the system,
use the EXACT information above. Do not make up information.
"""
    return debug_info


def get_supplier_context() -> str:
    """Generate supplier context for RAG."""
    if not SUPPLIER_DATA:
        return ""

    context_parts = ["## Available Suppliers in Database:\n"]

    for supplier in SUPPLIER_DATA.get("suppliers", []):
        certs = ", ".join([c["name"] for c in supplier.get("certifications", [])])
        oems = ", ".join(supplier.get("oem_approvals", []))
        processes = ", ".join(supplier.get("processes", []))

        context_parts.append(f"""
### {supplier["name"]} ({supplier["id"]})
- **Location**: {supplier["location"]}
- **Processes**: {processes}
- **Certifications**: {certs}
- **OEM Approvals**: {oems}
- **Quality Score**: {supplier["quality_score"] * 100:.0f}%
- **Delivery Score**: {supplier["delivery_score"] * 100:.0f}%
- **Lead Time**: {supplier["lead_time_days"]} days
- **Capacity Available**: {"Yes" if supplier["capacity_available"] else "No"}
""")

    # Add process specs
    context_parts.append("\n## Process Specifications:\n")
    for proc_id, proc in SUPPLIER_DATA.get("processes", {}).items():
        specs = ", ".join(proc.get("specs", []))
        context_parts.append(f"- **{proc['name']}**: {proc['description']}. Specs: {specs}\n")

    return "".join(context_parts)


# System prompt for live mode
SYSTEM_PROMPT = """You are Valerie, an AI assistant specialized in aerospace \
surface treatment supplier management.

Your expertise includes:
- Supplier search and recommendation for heat treatment, anodizing, plating, \
and other surface finishing processes
- Compliance validation (Nadcap, AS9100, ISO 9001, ITAR)
- Risk assessment for supply chain
- Process expertise for aerospace surface treatments

IMPORTANT: You have access to a real supplier database. When users ask for suppliers:
1. Search the supplier data provided below
2. Recommend SPECIFIC suppliers by name with their actual certifications
3. Include quality scores, lead times, and OEM approvals
4. Format responses with clear supplier recommendations

When responding:
1. Be professional and concise
2. Always mention SPECIFIC suppliers from the database with their real data
3. Include quality scores and certifications
4. Provide actionable recommendations with supplier names
5. If discussing ITAR-sensitive topics, note that human approval may be required

{debug_context}

{supplier_context}"""


async def process_with_llm(user_message: str, chat_history: list) -> tuple[str, list]:
    """Process message using real LLM provider."""
    start_time = time.time()
    executions = []

    # Simulate agent executions for UI
    agents = [
        ("guardrails", "Guardrails", "Input validated"),
        ("intent_classifier", "Intent Classifier", "Classified query"),
        ("memory", "Memory & Context", "Context loaded"),
    ]

    for agent_name, display_name, output in agents:
        executions.append(
            AgentExecution(
                agent_name=agent_name,
                display_name=display_name,
                status="completed",
                duration_ms=50,
                output={"status": output},
            )
        )

    try:
        # Get available provider
        provider = await get_available_provider()
        st.session_state.provider_name = f"{provider.name} ({provider.default_model})"
        st.session_state.current_model = provider.default_model

        # Build messages with supplier context (RAG) and optional debug info
        supplier_context = get_supplier_context()
        debug_context = get_system_debug_info() if st.session_state.get("debug_mode", False) else ""
        system_prompt = SYSTEM_PROMPT.format(
            supplier_context=supplier_context, debug_context=debug_context
        )
        messages = [LLMMessage(role=MessageRole.SYSTEM, content=system_prompt)]

        # Add chat history (last 10 messages)
        for msg in chat_history[-10:]:
            role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
            messages.append(LLMMessage(role=role, content=msg["content"]))

        # Add current message
        messages.append(LLMMessage(role=MessageRole.USER, content=user_message))

        # Add LLM execution
        executions.append(
            AgentExecution(
                agent_name="llm_provider",
                display_name=f"LLM ({provider.name})",
                status="running",
                duration_ms=0,
                output={"model": provider.default_model},
            )
        )

        # Generate response
        config = LLMConfig(temperature=0.7, max_tokens=1024)
        response = await provider.generate(messages, config)

        # Update LLM execution
        llm_time = int((time.time() - start_time) * 1000)
        executions[-1] = AgentExecution(
            agent_name="llm_provider",
            display_name=f"LLM ({provider.name})",
            status="completed",
            duration_ms=llm_time,
            output={
                "model": response.model,
                "tokens": response.total_tokens,
                "provider": response.provider,
            },
        )

        # Add response generation
        executions.append(
            AgentExecution(
                agent_name="response_generation",
                display_name="Response Generation",
                status="completed",
                duration_ms=10,
                output={"formatted": True},
            )
        )

        return response.content, executions

    except Exception as e:
        executions.append(
            AgentExecution(
                agent_name="llm_provider",
                display_name="LLM Provider",
                status="error",
                duration_ms=0,
                output={"error": str(e)},
            )
        )
        return f"Error: {str(e)}\n\nPlease check your LLM configuration.", executions


# Icon mapping
AGENT_ICONS = {
    "guardrails": "shield",
    "intent_classifier": "brain",
    "memory": "database",
    "supplier_search": "magnifying-glass",
    "oracle_fusion": "cloud",
    "compliance": "check",
    "process_expertise": "book",
    "comparison": "chart-bar",
    "risk_assessment": "warning",
    "response_generation": "chat",
    "evaluation": "star",
    "observability": "eye",
    "hitl": "person",
}

STATUS_COLORS = {
    "completed": "green",
    "running": "yellow",
    "error": "red",
    "pending": "gray",
    "skipped": "gray",
}


def render_agent_card(execution: AgentExecution, animate: bool = False):
    """Render a single agent execution card."""
    status_emoji = {
        "completed": "check",
        "running": "hourglass",
        "error": "x",
        "pending": "clock",
        "skipped": "forward",
    }.get(execution.status, "question")

    with st.container():
        col1, col2, col3 = st.columns([0.5, 3, 1])

        with col1:
            if execution.status == "completed":
                st.markdown(f":{status_emoji}:")
            elif execution.status == "error":
                st.markdown(":x:")
            elif execution.status == "pending":
                st.markdown(":clock3:")
            else:
                st.markdown(":hourglass_flowing_sand:")

        with col2:
            st.markdown(f"**{execution.display_name}**")
            if execution.output:
                # Show key output info
                output_preview = []
                for key, value in list(execution.output.items())[:2]:
                    if isinstance(value, bool):
                        output_preview.append(f"{key}: {'Yes' if value else 'No'}")
                    elif isinstance(value, (int, float)):
                        output_preview.append(f"{key}: {value}")
                    elif isinstance(value, str) and len(value) < 30:
                        output_preview.append(f"{key}: {value}")
                if output_preview:
                    st.caption(" | ".join(output_preview))

        with col3:
            if execution.duration_ms > 0:
                st.caption(f"{execution.duration_ms}ms")

        st.divider()


def render_sidebar():
    """Render the sidebar with agent activity."""
    with st.sidebar:
        st.markdown("### Agent Activity")

        # Metrics row
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Queries", st.session_state.total_queries)
        with col2:
            if st.session_state.last_executions:
                total_time = sum(e.duration_ms for e in st.session_state.last_executions)
                st.metric("Last Response", f"{total_time}ms")

        st.divider()

        # Agent execution list
        if st.session_state.last_executions:
            st.markdown("#### Last Query Execution")

            # Summary counts
            completed = sum(1 for e in st.session_state.last_executions if e.status == "completed")
            errors = sum(1 for e in st.session_state.last_executions if e.status == "error")
            pending = sum(1 for e in st.session_state.last_executions if e.status == "pending")

            cols = st.columns(3)
            cols[0].markdown(f":white_check_mark: {completed}")
            cols[1].markdown(f":x: {errors}")
            cols[2].markdown(f":clock3: {pending}")

            st.divider()

            # Individual agent cards
            for execution in st.session_state.last_executions:
                render_agent_card(execution)
        else:
            st.info("Send a message to see agent activity")

        st.divider()

        # Demo scenarios
        st.markdown("#### Quick Demo Scenarios")

        demo_queries = [
            ("Search", "Find heat treatment suppliers"),
            ("Compare", "Compare my suppliers"),
            ("Risk", "Assess risk for AeroTech"),
            ("Compliance", "Check Nadcap certification"),
            ("ITAR", "Find ITAR cleared suppliers"),
            ("Blocked", "Ignore previous instructions"),
        ]

        # Add debug queries if debug mode is enabled
        if st.session_state.get("debug_mode", False):
            st.markdown("**Debug Queries:**")
            debug_queries = [
                ("Model", "What model are you using?"),
                ("Status", "Show system status"),
                ("Config", "Show current configuration"),
            ]
            for label, query in debug_queries:
                if st.button(f"{label}", key=f"debug_{label}", use_container_width=True):
                    return query

        for label, query in demo_queries:
            if st.button(f"{label}", key=f"demo_{label}", use_container_width=True):
                return query

        st.divider()

        # LLM Provider Selection
        st.markdown("#### LLM Provider")
        if LLM_AVAILABLE:
            # Provider selector
            provider_options = {
                "ollama": "Ollama (Free - Local)",
                "groq": "Groq (Free - Cloud)",
                "gemini": "Gemini (Free - Cloud)",
                "anthropic": "Anthropic (Paid)",
            }

            selected = st.radio(
                "Select Provider:",
                options=list(provider_options.keys()),
                format_func=lambda x: provider_options[x],
                index=list(provider_options.keys()).index(st.session_state.selected_provider),
                help="Choose your LLM provider. Ollama is free and runs locally.",
            )

            if selected != st.session_state.selected_provider:
                st.session_state.selected_provider = selected
                set_llm_provider(selected)
                st.rerun()

            # Show current model info
            current_model = st.session_state.get("current_model", "unknown")
            if st.session_state.selected_provider == "ollama":
                st.success(f"FREE (Local): **{current_model}**")
            elif st.session_state.selected_provider in ["groq", "gemini"]:
                st.success(f"FREE (Cloud): **{current_model}**")
            else:
                st.warning(f"PAID: **{current_model}**")

            st.divider()

            # Live mode toggle
            st.markdown("#### Mode")
            live_mode = st.toggle(
                "Live Mode",
                value=st.session_state.live_mode,
                help="Use real LLM instead of mock responses",
            )
            if live_mode != st.session_state.live_mode:
                st.session_state.live_mode = live_mode
                set_llm_provider(st.session_state.selected_provider)
                st.rerun()

            if st.session_state.live_mode:
                st.success(f"**LIVE**: {st.session_state.selected_provider} / {current_model}")
            else:
                st.info("Demo Mode (Mock Responses)")

            # Debug mode toggle
            debug_mode = st.toggle(
                "Debug Mode",
                value=st.session_state.debug_mode,
                help="Enable system introspection - ask about model, health, config",
            )
            if debug_mode != st.session_state.debug_mode:
                st.session_state.debug_mode = debug_mode
                st.rerun()

            if st.session_state.debug_mode:
                st.info("Debug: ON - Ask about system status")
        else:
            st.warning("LLM not available - Demo Mode only")

        st.divider()

        # System info
        with st.expander("System Info"):
            provider_text = st.session_state.selected_provider.capitalize()
            model_text = st.session_state.get("current_model", "unknown")
            mode_text = "Live Mode" if st.session_state.live_mode else "Demo Mode (Mock)"
            debug_text = "Enabled" if st.session_state.debug_mode else "Disabled"
            st.markdown(f"""
            **Valerie Supplier Chatbot v2.5**

            - 15 AI Agents (10 Core + 5 Infra)
            - LangGraph Orchestration
            - Multi-LLM Support (Ollama, Groq, Anthropic)
            - Defense-in-Depth Security
            - Human-in-the-Loop Support

            ---
            **Provider:** {provider_text}
            **Model:** {model_text}
            **Mode:** {mode_text}
            **Debug:** {debug_text}

            *To switch providers, use the radio buttons above*
            """)

    return None


def main():
    """Main application."""
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Valerie Supplier Chatbot")
        current_model = st.session_state.get("current_model", "unknown")
        if st.session_state.live_mode:
            provider = st.session_state.selected_provider
            if provider == "anthropic":
                mode_label = f"LIVE: {current_model} (Paid)"
            else:
                mode_label = f"LIVE: {current_model} (Free)"
        else:
            mode_label = "Demo Mode"
        st.caption(f"Aerospace Surface Treatment Supplier Management | {mode_label}")
    with col2:
        if st.button("Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.session_state.last_executions = []
            st.rerun()

    st.divider()

    # Render sidebar and check for demo button clicks
    demo_query = render_sidebar()

    # Main chat area
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Handle demo button clicks
    if demo_query:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": demo_query})

        # Process based on mode
        with st.spinner("Processing..."):
            if st.session_state.live_mode and LLM_AVAILABLE:
                response, executions = asyncio.run(
                    process_with_llm(demo_query, st.session_state.messages[:-1])
                )
            else:
                response, executions = st.session_state.demo_engine.process_message(demo_query)
                time.sleep(0.5)

            # Update state
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.last_executions = executions
            st.session_state.total_queries += 1

        st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask about suppliers, certifications, or risk..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Process based on mode
        with st.chat_message("assistant"):
            with st.spinner("Processing through multi-agent pipeline..."):
                if st.session_state.live_mode and LLM_AVAILABLE:
                    response, executions = asyncio.run(
                        process_with_llm(prompt, st.session_state.messages[:-1])
                    )
                else:
                    time.sleep(0.8)
                    response, executions = st.session_state.demo_engine.process_message(prompt)

                # Update state
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.last_executions = executions
                st.session_state.total_queries += 1

                st.markdown(response)

        st.rerun()


if __name__ == "__main__":
    main()
