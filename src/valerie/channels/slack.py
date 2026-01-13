"""Slack channel handler - adapts responses for Slack's format and limits."""

import hashlib
import hmac
import re
import time

from .base import BaseChannelHandler, ChannelConfig, FormattedResponse


class SlackHandler(BaseChannelHandler):
    """Handler for Slack channel.

    Slack supports:
    - Max 4000 characters per message (3000 recommended)
    - Markdown with some differences (*bold*, _italic_, ~strike~, `code`)
    - Blocks for rich formatting
    - Interactive buttons (up to 25 per message)
    - Threading
    - File attachments
    """

    @property
    def name(self) -> str:
        return "slack"

    @property
    def config(self) -> ChannelConfig:
        return ChannelConfig(
            max_chars=3000,  # Recommended limit (hard limit is 4000)
            supports_markdown=True,
            supports_buttons=True,
            supports_media=True,
            supports_threading=True,
            rate_limit_per_minute=50,  # Slack rate limit
        )

    def format_response(self, response: str, **kwargs) -> FormattedResponse:
        """Format response for Slack.

        Converts standard markdown to Slack's mrkdwn format and chunks
        long messages.
        """
        # Convert markdown to Slack format
        text = self._convert_markdown(response)

        # Chunk if necessary
        messages = self.chunk_message(text)

        # Add continuation indicators for multi-message responses
        if len(messages) > 1:
            for i in range(len(messages) - 1):
                messages[i] = messages[i] + "\n_(continued...)_"

        # Handle buttons - convert to Slack blocks format
        buttons = kwargs.get("buttons")
        slack_buttons = None
        if buttons and self.config.supports_buttons:
            slack_buttons = self._format_buttons(buttons)

        return FormattedResponse(
            messages=messages,
            buttons=slack_buttons,
            thread_id=kwargs.get("thread_id"),
            metadata={
                "channel": kwargs.get("channel_id"),
                "blocks": self._create_blocks(messages[0], slack_buttons) if slack_buttons else None,
            },
        )

    def _convert_markdown(self, text: str) -> str:
        """Convert standard markdown to Slack mrkdwn format.

        Slack uses slightly different markdown:
        - **bold** -> *bold*
        - _italic_ stays the same
        - ~~strike~~ -> ~strike~
        - [link](url) -> <url|link>
        """
        # Bold: **text** -> *text*
        text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

        # Strikethrough: ~~text~~ -> ~text~
        text = re.sub(r"~~(.+?)~~", r"~\1~", text)

        # Links: [text](url) -> <url|text>
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r"<\2|\1>", text)

        # Headers: remove # but keep bold
        text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)

        # Code blocks: keep as is (Slack supports ```)

        return text

    def _format_buttons(self, buttons: list[dict]) -> list[dict]:
        """Convert buttons to Slack action blocks format."""
        slack_buttons = []
        for btn in buttons[:25]:  # Slack limit
            slack_buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": btn.get("label", btn.get("text", "Button"))[:75],  # Slack limit
                },
                "value": btn.get("value", btn.get("label", "")),
                "action_id": btn.get("action_id", f"btn_{len(slack_buttons)}"),
            })
        return slack_buttons

    def _create_blocks(self, text: str, buttons: list[dict] | None) -> list[dict]:
        """Create Slack Block Kit blocks for rich formatting."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text[:3000],  # Block text limit
                },
            }
        ]

        if buttons:
            blocks.append({
                "type": "actions",
                "elements": buttons,
            })

        return blocks

    def parse_incoming(self, payload: dict) -> dict:
        """Parse incoming Slack webhook payload.

        Handles both Events API and Slash Commands.
        """
        # Events API format
        if "event" in payload:
            event = payload["event"]
            return {
                "user_id": event.get("user"),
                "message": event.get("text", ""),
                "channel_id": event.get("channel"),
                "thread_id": event.get("thread_ts") or event.get("ts"),
                "event_type": event.get("type"),
                "team_id": payload.get("team_id"),
                "metadata": {
                    "event_id": payload.get("event_id"),
                    "event_time": payload.get("event_time"),
                },
            }

        # Slash command format
        if "command" in payload:
            return {
                "user_id": payload.get("user_id"),
                "message": payload.get("text", ""),
                "channel_id": payload.get("channel_id"),
                "thread_id": None,
                "event_type": "slash_command",
                "command": payload.get("command"),
                "team_id": payload.get("team_id"),
                "response_url": payload.get("response_url"),
                "metadata": {
                    "trigger_id": payload.get("trigger_id"),
                },
            }

        # Interactive component (button click, etc.)
        if "actions" in payload:
            action = payload["actions"][0] if payload["actions"] else {}
            return {
                "user_id": payload.get("user", {}).get("id"),
                "message": action.get("value", ""),
                "channel_id": payload.get("channel", {}).get("id"),
                "thread_id": payload.get("message", {}).get("thread_ts"),
                "event_type": "interactive",
                "action_id": action.get("action_id"),
                "response_url": payload.get("response_url"),
                "metadata": payload,
            }

        # Unknown format - try to extract basics
        return {
            "user_id": payload.get("user_id") or payload.get("user", {}).get("id"),
            "message": payload.get("text", ""),
            "channel_id": payload.get("channel_id") or payload.get("channel", {}).get("id"),
            "thread_id": payload.get("thread_ts"),
            "metadata": payload,
        }

    @staticmethod
    def verify_signature(
        body: bytes,
        timestamp: str,
        signature: str,
        signing_secret: str,
    ) -> bool:
        """Verify Slack request signature.

        Args:
            body: Raw request body
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header
            signing_secret: Slack app signing secret

        Returns:
            True if signature is valid
        """
        # Check timestamp to prevent replay attacks (5 minute window)
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
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
