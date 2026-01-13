"""MS Teams channel handler - adapts responses for Teams' format and limits."""

import re

from .base import BaseChannelHandler, ChannelConfig, FormattedResponse


class TeamsHandler(BaseChannelHandler):
    """Handler for Microsoft Teams channel.

    Teams supports:
    - Max 28KB per message (about 28000 chars)
    - Adaptive Cards for rich formatting
    - Markdown (similar to standard but with some differences)
    - Buttons via Adaptive Cards
    - Threading (reply chain)
    - File attachments
    """

    @property
    def name(self) -> str:
        return "teams"

    @property
    def config(self) -> ChannelConfig:
        return ChannelConfig(
            max_chars=25000,  # Safe limit under 28KB
            supports_markdown=True,
            supports_buttons=True,
            supports_media=True,
            supports_threading=True,
            rate_limit_per_minute=60,
        )

    def format_response(self, response: str, **kwargs) -> FormattedResponse:
        """Format response for MS Teams.

        Converts markdown to Teams format and optionally creates
        Adaptive Cards for rich content.
        """
        # Convert markdown to Teams format
        text = self._convert_markdown(response)

        # Chunk if necessary (rare for Teams given high limit)
        messages = self.chunk_message(text)

        # Handle buttons - convert to Adaptive Card format
        buttons = kwargs.get("buttons")
        use_adaptive_card = kwargs.get("use_adaptive_card", bool(buttons))

        adaptive_card = None
        if use_adaptive_card:
            adaptive_card = self._create_adaptive_card(text, buttons)

        return FormattedResponse(
            messages=messages,
            buttons=buttons,
            thread_id=kwargs.get("thread_id"),
            metadata={
                "conversation_id": kwargs.get("conversation_id"),
                "adaptive_card": adaptive_card,
                "type": "message",
            },
        )

    def _convert_markdown(self, text: str) -> str:
        """Convert standard markdown to Teams format.

        Teams uses mostly standard markdown but has some quirks:
        - Headers need blank lines around them
        - Tables have specific formatting requirements
        - Some HTML is supported
        """
        # Headers: ensure blank lines
        text = re.sub(r"(^|\n)(#{1,6}\s*.+)(\n|$)", r"\1\n\2\n\3", text)

        # Bold: **text** is supported
        # Italic: *text* or _text_ is supported

        # Links: [text](url) is supported

        # Code blocks: ``` supported

        # Strikethrough: ~~text~~ -> <s>text</s> (Teams uses HTML)
        text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

        # Clean up excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

    def _create_adaptive_card(
        self,
        text: str,
        buttons: list[dict] | None = None,
    ) -> dict:
        """Create an Adaptive Card for rich Teams messages.

        Adaptive Cards provide rich formatting, buttons, and inputs
        for Teams messages.
        """
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": text[:5000],  # Adaptive Card text limit
                    "wrap": True,
                    "size": "Default",
                }
            ],
        }

        # Add buttons as actions
        if buttons:
            card["actions"] = []
            for btn in buttons[:6]:  # Adaptive Cards allow up to 6 actions
                action = {
                    "type": "Action.Submit",
                    "title": btn.get("label", btn.get("text", "Button"))[:20],
                    "data": {
                        "action": btn.get("value", btn.get("action_id", "")),
                        "label": btn.get("label", ""),
                    },
                }
                card["actions"].append(action)

        return card

    def create_hero_card(
        self,
        title: str,
        subtitle: str | None = None,
        text: str | None = None,
        images: list[str] | None = None,
        buttons: list[dict] | None = None,
    ) -> dict:
        """Create a Hero Card for Teams.

        Hero Cards are simpler than Adaptive Cards and good for
        displaying a single item with optional image and buttons.
        """
        card = {
            "contentType": "application/vnd.microsoft.card.hero",
            "content": {
                "title": title,
            },
        }

        if subtitle:
            card["content"]["subtitle"] = subtitle

        if text:
            card["content"]["text"] = text

        if images:
            card["content"]["images"] = [{"url": img} for img in images[:1]]

        if buttons:
            card["content"]["buttons"] = [
                {
                    "type": "imBack",
                    "title": btn.get("label", btn.get("text", "Button")),
                    "value": btn.get("value", btn.get("label", "")),
                }
                for btn in buttons[:3]  # Hero Cards allow up to 3 buttons
            ]

        return card

    def parse_incoming(self, payload: dict) -> dict:
        """Parse incoming Teams webhook payload.

        Handles Bot Framework activity format.
        """
        # Standard Bot Framework activity
        activity_type = payload.get("type", "message")

        if activity_type == "message":
            return {
                "user_id": payload.get("from", {}).get("id"),
                "user_name": payload.get("from", {}).get("name"),
                "message": payload.get("text", ""),
                "channel_id": payload.get("channelId"),
                "conversation_id": payload.get("conversation", {}).get("id"),
                "thread_id": payload.get("conversation", {}).get("id"),
                "event_type": "message",
                "service_url": payload.get("serviceUrl"),
                "metadata": {
                    "activity_id": payload.get("id"),
                    "timestamp": payload.get("timestamp"),
                    "locale": payload.get("locale"),
                    "tenant_id": payload.get("channelData", {}).get("tenant", {}).get("id"),
                },
            }

        # Adaptive Card action (button click)
        if activity_type == "invoke" or payload.get("value"):
            value = payload.get("value", {})
            return {
                "user_id": payload.get("from", {}).get("id"),
                "user_name": payload.get("from", {}).get("name"),
                "message": value.get("action", "") or str(value),
                "channel_id": payload.get("channelId"),
                "conversation_id": payload.get("conversation", {}).get("id"),
                "thread_id": payload.get("conversation", {}).get("id"),
                "event_type": "action",
                "action_data": value,
                "service_url": payload.get("serviceUrl"),
                "metadata": payload,
            }

        # Conversation update (user joined, etc.)
        if activity_type == "conversationUpdate":
            return {
                "user_id": payload.get("from", {}).get("id"),
                "message": "",
                "channel_id": payload.get("channelId"),
                "conversation_id": payload.get("conversation", {}).get("id"),
                "thread_id": payload.get("conversation", {}).get("id"),
                "event_type": "conversation_update",
                "members_added": payload.get("membersAdded", []),
                "members_removed": payload.get("membersRemoved", []),
                "service_url": payload.get("serviceUrl"),
                "metadata": payload,
            }

        # Unknown activity type
        return {
            "user_id": payload.get("from", {}).get("id"),
            "message": payload.get("text", ""),
            "channel_id": payload.get("channelId"),
            "conversation_id": payload.get("conversation", {}).get("id"),
            "thread_id": payload.get("conversation", {}).get("id"),
            "event_type": activity_type,
            "service_url": payload.get("serviceUrl"),
            "metadata": payload,
        }

    @staticmethod
    def create_teams_response(
        text: str,
        conversation_id: str,
        activity_id: str | None = None,
        attachments: list[dict] | None = None,
    ) -> dict:
        """Create a properly formatted Teams response activity.

        Args:
            text: Response text
            conversation_id: Teams conversation ID
            activity_id: Original activity ID (for replies)
            attachments: List of card attachments

        Returns:
            Bot Framework activity dict
        """
        response = {
            "type": "message",
            "text": text,
            "conversation": {"id": conversation_id},
        }

        if activity_id:
            response["replyToId"] = activity_id

        if attachments:
            response["attachments"] = attachments

        return response
