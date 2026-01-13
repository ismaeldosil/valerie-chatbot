"""WebSocket support for real-time chat streaming."""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(tags=["WebSocket"])


class WSEventType(str, Enum):
    """WebSocket event types."""

    CONNECTED = "connected"
    MESSAGE = "message"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WSEvent(BaseModel):
    """WebSocket event structure."""

    type: WSEventType
    data: dict[str, Any] = {}
    timestamp: str = ""

    def __init__(self, **data):
        if "timestamp" not in data or not data["timestamp"]:
            data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store a new connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """Remove a connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_event(self, session_id: str, event: WSEvent):
        """Send an event to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(event.model_dump())

    async def broadcast(self, event: WSEvent):
        """Broadcast an event to all connections."""
        for session_id in self.active_connections:
            await self.send_event(session_id, event)


# Global connection manager
manager = ConnectionManager()


# Demo data for streaming simulation
DEMO_RESPONSES = {
    "supplier_search": {
        "chunks": [
            "Based on your search criteria, ",
            "I found **3 qualified suppliers** ",
            "for heat treatment:\n\n",
            "### 1. AeroTech Surface Solutions\n",
            "- Location: Phoenix, AZ\n",
            "- Quality Score: 95%\n",
            "- Lead Time: 5 days\n\n",
            "### 2. PrecisionCoat Industries\n",
            "- Location: Los Angeles, CA\n",
            "- Quality Score: 91%\n",
            "- Lead Time: 7 days\n\n",
            "### 3. MetalTreat Aerospace\n",
            "- Location: Seattle, WA\n",
            "- Quality Score: 97%\n",
            "- Lead Time: 10 days\n\n",
            "Would you like me to compare these suppliers?",
        ],
        "agents": [
            ("guardrails", "Guardrails", 35),
            ("intent_classifier", "Intent Classifier", 120),
            ("memory", "Memory & Context", 25),
            ("supplier_search", "Supplier Search", 245),
            ("oracle_fusion", "Oracle Fusion", 312),
            ("compliance", "Compliance Validation", 189),
            ("response_generation", "Response Generation", 234),
        ],
    },
    "greeting": {
        "chunks": [
            "Hello! ",
            "I'm the Valerie Supplier Chatbot. ",
            "I can help you with:\n\n",
            "- **Finding suppliers** for specific processes\n",
            "- **Checking compliance** and certifications\n",
            "- **Comparing suppliers** side-by-side\n",
            "- **Assessing risk** profiles\n\n",
            "How can I assist you today?",
        ],
        "agents": [
            ("guardrails", "Guardrails", 28),
            ("intent_classifier", "Intent Classifier", 89),
            ("response_generation", "Response Generation", 156),
        ],
    },
    "blocked": {
        "chunks": [
            "I'm unable to process that request.\n\n",
            "Your message was flagged by our security system. ",
            "Please rephrase your question focusing on supplier-related queries.",
        ],
        "agents": [
            ("guardrails", "Guardrails", 42),
        ],
    },
}


def detect_scenario(message: str) -> str:
    """Detect which demo scenario matches the input."""
    message_lower = message.lower()

    if any(kw in message_lower for kw in ["ignore", "system:", "<script"]):
        return "blocked"
    if any(kw in message_lower for kw in ["hello", "hi", "hey", "help"]):
        return "greeting"
    return "supplier_search"


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str | None = None):
    """
    WebSocket endpoint for real-time chat.

    Events sent to client:
    - connected: Connection established
    - agent_start: Agent begins processing
    - agent_end: Agent completes processing
    - stream_start: Response streaming begins
    - stream_chunk: Partial response chunk
    - stream_end: Response streaming complete
    - error: Error occurred

    Events received from client:
    - message: User message to process
    - ping: Keep-alive ping
    """
    # Generate session ID if not provided
    if not session_id or session_id == "new":
        session_id = f"ws-{uuid.uuid4().hex[:12]}"

    await manager.connect(websocket, session_id)

    # Send connected event
    await manager.send_event(
        session_id,
        WSEvent(
            type=WSEventType.CONNECTED,
            data={"session_id": session_id, "message": "Connected to Valerie Chatbot"},
        ),
    )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            event_type = data.get("type", "message")

            # Handle ping
            if event_type == "ping":
                await manager.send_event(
                    session_id,
                    WSEvent(type=WSEventType.PONG, data={"timestamp": datetime.now().isoformat()}),
                )
                continue

            # Handle message
            if event_type == "message":
                message = data.get("content", "")
                if not message:
                    await manager.send_event(
                        session_id, WSEvent(type=WSEventType.ERROR, data={"error": "Empty message"})
                    )
                    continue

                # Process message with streaming
                await process_message_streaming(session_id, message)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_event(
            session_id, WSEvent(type=WSEventType.ERROR, data={"error": str(e)})
        )
        manager.disconnect(session_id)


async def process_message_streaming(session_id: str, message: str):
    """Process a message and stream the response."""
    # Detect scenario
    scenario = detect_scenario(message)
    response_data = DEMO_RESPONSES.get(scenario, DEMO_RESPONSES["supplier_search"])

    # Stream agent executions
    for agent_name, display_name, duration_ms in response_data["agents"]:
        # Agent start
        await manager.send_event(
            session_id,
            WSEvent(
                type=WSEventType.AGENT_START,
                data={"agent_name": agent_name, "display_name": display_name},
            ),
        )

        # Simulate processing time
        await asyncio.sleep(duration_ms / 1000)

        # Agent end
        is_blocked = scenario == "blocked" and agent_name == "guardrails"
        status = "error" if is_blocked else "completed"
        await manager.send_event(
            session_id,
            WSEvent(
                type=WSEventType.AGENT_END,
                data={
                    "agent_name": agent_name,
                    "display_name": display_name,
                    "duration_ms": duration_ms,
                    "status": status,
                },
            ),
        )

    # Stream response chunks
    await manager.send_event(
        session_id,
        WSEvent(type=WSEventType.STREAM_START, data={"message_id": f"msg-{uuid.uuid4().hex[:8]}"}),
    )

    full_response = ""
    for chunk in response_data["chunks"]:
        full_response += chunk
        await manager.send_event(
            session_id,
            WSEvent(
                type=WSEventType.STREAM_CHUNK, data={"chunk": chunk, "accumulated": full_response}
            ),
        )
        # Simulate typing delay
        await asyncio.sleep(0.05)

    await manager.send_event(
        session_id, WSEvent(type=WSEventType.STREAM_END, data={"full_response": full_response})
    )


# Include router in main app
def include_websocket_router(app):
    """Include WebSocket router in the FastAPI app."""
    app.include_router(router)
