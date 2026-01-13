"""Webhook endpoints for external channel integrations (Slack, Teams)."""

import hashlib
import hmac
import logging
import os
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from valerie.channels import Channel, ChannelRouter

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    success: bool
    message: str
    channel: str
    data: dict | None = None


class SlackChallengeResponse(BaseModel):
    """Response for Slack URL verification challenge."""

    challenge: str


# ============================================================================
# Slack Webhook
# ============================================================================


@router.post("/slack", response_model=WebhookResponse | SlackChallengeResponse)
async def slack_webhook(
    request: Request,
    x_slack_request_timestamp: str | None = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_signature: str | None = Header(None, alias="X-Slack-Signature"),
):
    """Handle incoming Slack webhook events.

    Supports:
    - URL verification challenge
    - Event callbacks (messages, mentions)
    - Slash commands
    - Interactive components (buttons, etc.)

    Environment variables required:
    - VALERIE_SLACK_SIGNING_SECRET: Slack app signing secret
    - VALERIE_SLACK_BOT_TOKEN: Bot token for sending responses
    """
    body = await request.body()
    payload = await request.json()

    # Handle URL verification challenge (Slack sends this when setting up)
    if payload.get("type") == "url_verification":
        logger.info("Slack URL verification challenge received")
        return SlackChallengeResponse(challenge=payload.get("challenge", ""))

    # Verify signature in production
    signing_secret = os.getenv("VALERIE_SLACK_SIGNING_SECRET")
    if signing_secret and x_slack_signature and x_slack_request_timestamp:
        if not _verify_slack_signature(
            body, x_slack_request_timestamp, x_slack_signature, signing_secret
        ):
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse the incoming payload
    handler = ChannelRouter.get_handler(Channel.SLACK)
    parsed = handler.parse_incoming(payload)

    # Skip bot messages to avoid loops
    if payload.get("event", {}).get("bot_id"):
        return WebhookResponse(
            success=True,
            message="Bot message ignored",
            channel="slack",
        )

    # Process the message
    user_message = parsed.get("message", "")
    if not user_message:
        return WebhookResponse(
            success=True,
            message="No message to process",
            channel="slack",
        )

    # Generate response using the chat endpoint logic
    response_text, agents = await _process_chat_message(
        message=user_message,
        channel="slack",
        user_id=parsed.get("user_id"),
        thread_id=parsed.get("thread_id"),
    )

    # Format response for Slack
    formatted = handler.format_response(
        response_text,
        thread_id=parsed.get("thread_id"),
        channel_id=parsed.get("channel_id"),
    )

    logger.info(
        "Slack webhook processed",
        extra={
            "user_id": parsed.get("user_id"),
            "channel_id": parsed.get("channel_id"),
            "message_length": len(user_message),
        },
    )

    return WebhookResponse(
        success=True,
        message="Message processed",
        channel="slack",
        data={
            "response": formatted.messages[0] if formatted.messages else "",
            "thread_ts": parsed.get("thread_id"),
            "channel": parsed.get("channel_id"),
            "blocks": formatted.metadata.get("blocks") if formatted.metadata else None,
        },
    )


# ============================================================================
# MS Teams Webhook
# ============================================================================


@router.post("/teams", response_model=WebhookResponse)
async def teams_webhook(
    request: Request,
    authorization: str | None = Header(None),
):
    """Handle incoming MS Teams webhook events.

    Supports:
    - Messages
    - Adaptive Card actions
    - Conversation updates

    Environment variables required:
    - VALERIE_TEAMS_APP_ID: Teams app ID
    - VALERIE_TEAMS_APP_PASSWORD: Teams app password
    """
    payload = await request.json()

    # Parse the incoming payload
    handler = ChannelRouter.get_handler(Channel.TEAMS)
    parsed = handler.parse_incoming(payload)

    activity_type = parsed.get("event_type")

    # Handle conversation updates (e.g., bot added to conversation)
    if activity_type == "conversation_update":
        members_added = parsed.get("members_added", [])
        if members_added:
            logger.info(
                "Teams conversation update",
                extra={"members_added": len(members_added)},
            )
            return WebhookResponse(
                success=True,
                message="Conversation update processed",
                channel="teams",
                data={"type": "conversation_update"},
            )

    # Skip if no message
    user_message = parsed.get("message", "")
    if not user_message:
        return WebhookResponse(
            success=True,
            message="No message to process",
            channel="teams",
        )

    # Process the message
    response_text, agents = await _process_chat_message(
        message=user_message,
        channel="teams",
        user_id=parsed.get("user_id"),
        thread_id=parsed.get("conversation_id"),
    )

    # Format response for Teams
    formatted = handler.format_response(
        response_text,
        thread_id=parsed.get("conversation_id"),
        conversation_id=parsed.get("conversation_id"),
    )

    logger.info(
        "Teams webhook processed",
        extra={
            "user_id": parsed.get("user_id"),
            "conversation_id": parsed.get("conversation_id"),
            "message_length": len(user_message),
        },
    )

    # Build Teams response
    teams_response = {
        "type": "message",
        "text": formatted.messages[0] if formatted.messages else "",
    }

    # Add Adaptive Card if available
    if formatted.metadata and formatted.metadata.get("adaptive_card"):
        teams_response["attachments"] = [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": formatted.metadata["adaptive_card"],
            }
        ]

    return WebhookResponse(
        success=True,
        message="Message processed",
        channel="teams",
        data=teams_response,
    )


# ============================================================================
# Generic Webhook (for custom integrations)
# ============================================================================


@router.post("/generic/{channel_name}", response_model=WebhookResponse)
async def generic_webhook(
    channel_name: str,
    request: Request,
):
    """Generic webhook endpoint for custom channel integrations.

    Args:
        channel_name: Name of the channel (for logging)
        request: Incoming request with JSON body containing 'message' field
    """
    payload = await request.json()

    user_message = payload.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Missing 'message' field")

    # Process using web handler (most permissive)
    handler = ChannelRouter.get_handler(Channel.WEB)
    parsed = handler.parse_incoming(payload)

    response_text, agents = await _process_chat_message(
        message=user_message,
        channel=channel_name,
        user_id=parsed.get("user_id"),
        thread_id=parsed.get("thread_id"),
    )

    formatted = handler.format_response(response_text)

    return WebhookResponse(
        success=True,
        message="Message processed",
        channel=channel_name,
        data={
            "response": formatted.messages[0] if formatted.messages else "",
        },
    )


# ============================================================================
# Health Check for Webhooks
# ============================================================================


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "channels": ChannelRouter.list_channels(),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Helper Functions
# ============================================================================


def _verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str,
) -> bool:
    """Verify Slack request signature."""
    # Check timestamp to prevent replay attacks (5 minute window)
    try:
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    # Create signature base string
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

    # Compute expected signature
    expected_sig = (
        "v0="
        + hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    # Compare signatures (timing-safe)
    return hmac.compare_digest(expected_sig, signature)


async def _process_chat_message(
    message: str,
    channel: str,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Process a chat message using the existing chat logic.

    This reuses the chat endpoint's processing logic to maintain
    consistency across all channels.
    """
    # Import here to avoid circular imports
    from .chat import _detect_intent, _generate_demo_response, _process_with_llm

    # Detect intent
    intent, confidence = _detect_intent(message)

    # Check if real mode is available
    try:
        from valerie.models import get_settings

        settings = get_settings()
        use_real_mode = bool(settings.anthropic_api_key)
    except Exception:
        use_real_mode = False

    if use_real_mode:
        try:
            response_text, agents = await _process_with_llm(message, [], intent)
        except Exception as e:
            logger.error(f"Real mode failed for {channel}: {e}")
            response_text, agents = _generate_demo_response(intent, message)
    else:
        response_text, agents = _generate_demo_response(intent, message)

    return response_text, [a.model_dump() for a in agents]
