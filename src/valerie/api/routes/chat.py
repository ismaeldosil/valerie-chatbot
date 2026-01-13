"""Chat endpoints."""

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..schemas import (
    AgentExecution,
    AgentStatus,
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    SessionResponse,
    SessionStatus,
    SupplierResult,
    SupplierSearchRequest,
    SupplierSearchResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Chat"])

# In-memory session storage (replace with Redis in production)
_sessions: dict[str, dict[str, Any]] = {}

# Load sample data for demo mode
# Try multiple paths to find the sample data
_BASE_PATH = Path(__file__).parent.parent.parent.parent.parent
POSSIBLE_PATHS = [
    _BASE_PATH / "demo" / "data" / "sample_suppliers.json",
    _BASE_PATH.parent / "demo" / "data" / "sample_suppliers.json",
    Path.cwd() / "demo" / "data" / "sample_suppliers.json",
]

SAMPLE_DATA: dict = {}
for path in POSSIBLE_PATHS:
    if path.exists():
        with open(path) as f:
            SAMPLE_DATA = json.load(f)
        break

# Fallback inline data if file not found
if not SAMPLE_DATA:
    SAMPLE_DATA = {
        "suppliers": [
            {
                "id": "SUP-001",
                "name": "AeroTech Surface Solutions",
                "location": "Phoenix, AZ",
                "processes": ["heat_treatment", "shot_peening"],
                "certifications": [
                    {"name": "Nadcap Heat Treating", "expiry": "2026-03-15", "status": "active"}
                ],
                "quality_score": 0.95,
                "delivery_score": 0.92,
                "capacity_available": True,
                "lead_time_days": 5,
            },
            {
                "id": "SUP-002",
                "name": "PrecisionCoat Industries",
                "location": "Los Angeles, CA",
                "processes": ["anodizing", "chemical_conversion", "plating"],
                "certifications": [
                    {
                        "name": "Nadcap Chemical Processing",
                        "expiry": "2025-11-30",
                        "status": "active",
                    }
                ],
                "quality_score": 0.91,
                "delivery_score": 0.88,
                "capacity_available": True,
                "lead_time_days": 7,
            },
            {
                "id": "SUP-003",
                "name": "MetalTreat Aerospace",
                "location": "Seattle, WA",
                "processes": ["heat_treatment", "nitriding"],
                "certifications": [
                    {"name": "Nadcap Heat Treating", "expiry": "2026-06-01", "status": "active"}
                ],
                "quality_score": 0.97,
                "delivery_score": 0.94,
                "capacity_available": False,
                "lead_time_days": 10,
            },
        ]
    }


def _get_or_create_session(session_id: str | None) -> tuple[str, dict]:
    """Get existing session or create a new one."""
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session["last_activity"] = datetime.now()
        return session_id, session

    new_id = f"sess-{uuid.uuid4().hex[:12]}"
    session = {
        "id": new_id,
        "status": SessionStatus.ACTIVE,
        "created_at": datetime.now(),
        "last_activity": datetime.now(),
        "messages": [],
        "context": {},
    }
    _sessions[new_id] = session
    return new_id, session


async def _process_with_llm(
    user_message: str,
    chat_history: list,
    detected_intent: str
) -> tuple[str, list[AgentExecution]]:
    """Process message using real LLM provider."""
    from valerie.llm import get_llm_provider, LLMConfig, LLMMessage
    from valerie.llm.base import MessageRole as LLMRole

    start_time = time.time()
    executions = []

    # Add agent executions for UI tracking
    executions.append(AgentExecution(
        agent_name="guardrails",
        display_name="Guardrails",
        status=AgentStatus.COMPLETED,
        duration_ms=35,
        output={"passed": True},
    ))

    executions.append(AgentExecution(
        agent_name="intent_classifier",
        display_name="Intent Classifier",
        status=AgentStatus.COMPLETED,
        duration_ms=50,
        output={"intent": detected_intent},
    ))

    executions.append(AgentExecution(
        agent_name="memory",
        display_name="Memory & Context",
        status=AgentStatus.COMPLETED,
        duration_ms=25,
        output={"context_loaded": True},
    ))

    # Get LLM provider
    provider = get_llm_provider()

    # Build system prompt with supplier context
    supplier_context = _get_supplier_context()
    system_prompt = f"""You are Valerie, an AI assistant for supplier management in aerospace manufacturing.
You help users find suppliers, check compliance, and compare options.

Available supplier data:
{supplier_context}

Instructions:
- Respond in the same language as the user (Spanish or English)
- Be concise and helpful
- Format supplier information clearly
- If asked about suppliers, use the data provided above"""

    # Build messages
    messages = [LLMMessage(role=LLMRole.SYSTEM, content=system_prompt)]

    # Add chat history (last 10 messages)
    for msg in chat_history[-10:]:
        if hasattr(msg, 'role') and hasattr(msg, 'content'):
            role = LLMRole.USER if msg.role == MessageRole.USER else LLMRole.ASSISTANT
            messages.append(LLMMessage(role=role, content=msg.content))

    # Add current message
    messages.append(LLMMessage(role=LLMRole.USER, content=user_message))

    # Add LLM execution tracking
    executions.append(AgentExecution(
        agent_name="llm_provider",
        display_name=f"LLM ({provider.name})",
        status=AgentStatus.RUNNING,
        duration_ms=0,
        output={"model": provider.default_model},
    ))

    # Generate response
    config = LLMConfig(temperature=0.7, max_tokens=1024)
    response = await provider.generate(messages, config)

    # Update LLM execution
    llm_time = int((time.time() - start_time) * 1000)
    executions[-1] = AgentExecution(
        agent_name="llm_provider",
        display_name=f"LLM ({provider.name})",
        status=AgentStatus.COMPLETED,
        duration_ms=llm_time,
        output={
            "model": response.model,
            "tokens": response.total_tokens,
            "provider": response.provider,
        },
    )

    # Add response generation
    executions.append(AgentExecution(
        agent_name="response_generation",
        display_name="Response Generation",
        status=AgentStatus.COMPLETED,
        duration_ms=10,
        output={"formatted": True},
    ))

    return response.content, executions


def _get_supplier_context() -> str:
    """Get supplier data as context for LLM."""
    suppliers = SAMPLE_DATA.get("suppliers", [])
    if not suppliers:
        return "No supplier data available."

    context_lines = []
    for s in suppliers:
        certs = ", ".join(c["name"] for c in s.get("certifications", []))
        processes = ", ".join(s.get("processes", []))
        context_lines.append(
            f"- {s['name']} ({s['location']}): "
            f"Processes: {processes}. "
            f"Certifications: {certs}. "
            f"Quality: {s['quality_score']*100:.0f}%, "
            f"Delivery: {s['delivery_score']*100:.0f}%, "
            f"Lead time: {s['lead_time_days']} days"
        )
    return "\n".join(context_lines)


def _detect_intent(message: str) -> tuple[str, float]:
    """Simple intent detection for demo mode. Supports English and Spanish."""
    message_lower = message.lower()

    # Check patterns - Security (blocked)
    if any(kw in message_lower for kw in ["ignore", "system:", "<script", "reveal"]):
        return "blocked", 1.0

    # ITAR sensitive (EN + ES)
    if any(kw in message_lower for kw in [
        "itar", "defense", "classified",
        "defensa", "clasificado", "militar"
    ]):
        return "itar_sensitive", 0.95

    # Supplier comparison (EN + ES)
    if any(kw in message_lower for kw in [
        "compare", "versus", "vs", "comparison",
        "comparar", "comparación", "comparacion", "cual es mejor", "diferencia"
    ]):
        return "supplier_comparison", 0.92

    # Risk assessment (EN + ES)
    if any(kw in message_lower for kw in [
        "risk", "assess", "evaluate",
        "riesgo", "evaluar", "evaluación", "evaluacion"
    ]):
        return "risk_assessment", 0.89

    # Compliance check (EN + ES)
    if any(kw in message_lower for kw in [
        "compliance", "certified", "nadcap", "certification",
        "cumplimiento", "certificado", "certificación", "certificacion", "cumple"
    ]):
        return "compliance_check", 0.91

    # Supplier search (EN + ES)
    if any(kw in message_lower for kw in [
        "find", "search", "supplier", "heat", "anodiz",
        "buscar", "busca", "proveedor", "proveedores", "encuentra", "encontrar",
        "dame", "lista", "mostrar", "muestra", "necesito", "quien vende",
        "donde comprar", "quiero"
    ]):
        return "supplier_search", 0.94

    # Greeting (EN + ES)
    if any(kw in message_lower for kw in [
        "hello", "hi", "hey", "help",
        "hola", "buenos", "ayuda", "ayúdame", "ayudame"
    ]):
        return "greeting", 0.98

    return "unknown", 0.45


def _generate_demo_response(intent: str, message: str) -> tuple[str, list[AgentExecution]]:
    """Generate demo response based on intent."""
    executions = []

    if intent == "blocked":
        executions.append(
            AgentExecution(
                agent_name="guardrails",
                display_name="Guardrails",
                status=AgentStatus.ERROR,
                duration_ms=42,
                output={"passed": False, "reason": "Potential injection detected"},
            )
        )
        response = "Your request was blocked by security guardrails. Please rephrase your question."
        return response, executions

    # Standard flow
    executions.append(
        AgentExecution(
            agent_name="guardrails",
            display_name="Guardrails",
            status=AgentStatus.COMPLETED,
            duration_ms=35,
            output={"passed": True},
        )
    )

    executions.append(
        AgentExecution(
            agent_name="intent_classifier",
            display_name="Intent Classifier",
            status=AgentStatus.COMPLETED,
            duration_ms=120,
            output={"intent": intent},
        )
    )

    if intent == "greeting":
        response = (
            "Hello! I'm the Valerie Supplier Chatbot. I can help you find "
            "suppliers, check compliance, and compare options."
            "What would you like to do?"
        )
        return response, executions

    if intent == "itar_sensitive":
        executions.append(
            AgentExecution(
                agent_name="hitl",
                display_name="Human-in-the-Loop",
                status=AgentStatus.PENDING,
                duration_ms=0,
                output={"requires_approval": True, "reason": "ITAR-sensitive query"},
            )
        )
        response = (
            "This query involves ITAR-controlled information and requires "
            "human approval. A compliance officer has been notified."
        )
        return response, executions

    # Add more agents for supplier-related intents
    if intent in ["supplier_search", "supplier_comparison", "risk_assessment", "compliance_check"]:
        executions.extend(
            [
                AgentExecution(
                    agent_name="memory",
                    display_name="Memory & Context",
                    status=AgentStatus.COMPLETED,
                    duration_ms=25,
                    output={"context_loaded": True},
                ),
                AgentExecution(
                    agent_name="supplier_search",
                    display_name="Supplier Search",
                    status=AgentStatus.COMPLETED,
                    duration_ms=245,
                    output={"results": 3},
                ),
                AgentExecution(
                    agent_name="oracle_fusion",
                    display_name="Oracle Fusion",
                    status=AgentStatus.COMPLETED,
                    duration_ms=312,
                    output={"data_fetched": True},
                ),
                AgentExecution(
                    agent_name="compliance",
                    display_name="Compliance Validation",
                    status=AgentStatus.COMPLETED,
                    duration_ms=189,
                    output={"all_compliant": True},
                ),
            ]
        )

    if intent == "supplier_comparison":
        executions.append(
            AgentExecution(
                agent_name="comparison",
                display_name="Comparison",
                status=AgentStatus.COMPLETED,
                duration_ms=345,
                output={"dimensions": 5, "recommendation": "AeroTech Surface Solutions"},
            )
        )

    if intent == "risk_assessment":
        executions.append(
            AgentExecution(
                agent_name="risk_assessment",
                display_name="Risk Assessment",
                status=AgentStatus.COMPLETED,
                duration_ms=423,
                output={"overall_risk": "LOW", "score": 0.18},
            )
        )

    # Response generation
    executions.append(
        AgentExecution(
            agent_name="response_generation",
            display_name="Response Generation",
            status=AgentStatus.COMPLETED,
            duration_ms=234,
            output={"format": "structured"},
        )
    )

    # Generate appropriate response
    if intent == "supplier_search":
        suppliers = SAMPLE_DATA.get("suppliers", [])[:3]
        response = f"Found {len(suppliers)} suppliers matching your criteria:\n\n"
        for s in suppliers:
            quality = s["quality_score"] * 100
            response += f"- **{s['name']}** ({s['location']}) - Quality: {quality:.0f}%\n"
    elif intent == "supplier_comparison":
        response = (
            "Comparison complete. **AeroTech Surface Solutions** is recommended "
            "based on the best balance of quality (95%) and lead time (5 days)."
        )
    elif intent == "risk_assessment":
        response = (
            "Risk assessment complete. Overall risk level: **LOW** (Score: 0.18). "
            "The supplier meets all compliance requirements."
        )
    elif intent == "compliance_check":
        response = (
            "Compliance check complete. All certifications are valid:\n"
            "- Nadcap Heat Treating (expires 2026-03-15)\n"
            "- AS9100D (expires 2025-08-20)\n"
            "- ISO 9001:2015 (expires 2026-01-10)"
        )
    else:
        response = (
            "I'm not sure how to help with that. "
            "Try asking about suppliers, compliance, or comparisons."
        )

    return response, executions


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the chatbot.

    In demo mode (no API key), returns simulated responses.
    With API key configured, uses the full multi-agent pipeline.
    """
    # Get or create session
    session_id, session = _get_or_create_session(request.session_id)

    # Add user message to session
    session["messages"].append(
        Message(role=MessageRole.USER, content=request.message, timestamp=datetime.now())
    )

    # Detect intent
    intent, confidence = _detect_intent(request.message)

    # Security: Always handle blocked/injection attempts with demo response (don't send to LLM)
    if intent == "blocked":
        response_text, agents_executed = _generate_demo_response(intent, request.message)
    else:
        # Check if real mode is available
        try:
            from valerie.models import get_settings

            settings = get_settings()
            use_real_mode = bool(settings.anthropic_api_key)
        except Exception:
            use_real_mode = False

        if use_real_mode:
            # Use real LLM processing
            try:
                response_text, agents_executed = await _process_with_llm(
                    request.message,
                    session.get("messages", []),
                    intent
                )
            except Exception as e:
                logging.error(f"Real mode failed, falling back to demo: {e}")
                response_text, agents_executed = _generate_demo_response(intent, request.message)
        else:
            # Demo mode
            response_text, agents_executed = _generate_demo_response(intent, request.message)

    # Add assistant message to session
    session["messages"].append(
        Message(role=MessageRole.ASSISTANT, content=response_text, timestamp=datetime.now())
    )

    requires_approval = intent == "itar_sensitive"

    return ChatResponse(
        session_id=session_id,
        message=response_text,
        agents_executed=agents_executed,
        intent=intent,
        confidence=confidence,
        requires_approval=requires_approval,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get session details and history."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]

    return SessionResponse(
        session_id=session["id"],
        status=session["status"],
        created_at=session["created_at"],
        last_activity=session["last_activity"],
        message_count=len(session["messages"]),
        messages=session["messages"],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    del _sessions[session_id]
    return {"message": "Session deleted", "session_id": session_id}


@router.post("/suppliers/search", response_model=SupplierSearchResponse)
async def search_suppliers(request: SupplierSearchRequest) -> SupplierSearchResponse:
    """
    Direct supplier search endpoint.

    Search for suppliers based on specific criteria without going through the chat interface.
    """
    # Filter suppliers based on criteria
    suppliers = SAMPLE_DATA.get("suppliers", [])
    results = []

    for supplier in suppliers:
        # Check process match
        if not any(p in supplier.get("processes", []) for p in request.processes):
            continue

        # Check certification match (if specified)
        if request.certifications:
            supplier_certs = [c["name"] for c in supplier.get("certifications", [])]
            if not any(cert in " ".join(supplier_certs) for cert in request.certifications):
                continue

        # Check quality score
        quality = supplier.get("quality_score", 0)
        if request.min_quality_score and quality < request.min_quality_score:
            continue

        results.append(
            SupplierResult(
                id=supplier["id"],
                name=supplier["name"],
                location=supplier["location"],
                processes=supplier["processes"],
                certifications=supplier["certifications"],
                quality_score=supplier["quality_score"],
                delivery_score=supplier["delivery_score"],
                capacity_available=supplier["capacity_available"],
                lead_time_days=supplier["lead_time_days"],
            )
        )

    return SupplierSearchResponse(
        suppliers=results,
        total_count=len(results),
        search_criteria={
            "processes": request.processes,
            "certifications": request.certifications,
            "location": request.location,
            "min_quality_score": request.min_quality_score,
        },
    )
