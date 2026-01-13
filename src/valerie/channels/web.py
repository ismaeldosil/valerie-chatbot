"""Web channel handler - no restrictions, full markdown support."""

from .base import BaseChannelHandler, ChannelConfig, FormattedResponse


class WebHandler(BaseChannelHandler):
    """Handler for web/API channel - no restrictions.

    The web channel supports full markdown, unlimited message length,
    and all interactive features.
    """

    @property
    def name(self) -> str:
        return "web"

    @property
    def config(self) -> ChannelConfig:
        return ChannelConfig(
            max_chars=50000,  # Effectively unlimited
            supports_markdown=True,
            supports_buttons=True,
            supports_media=True,
            supports_threading=True,
        )

    def format_response(self, response: str, **kwargs) -> FormattedResponse:
        """Format response for web - pass through unchanged.

        The web channel supports everything, so we don't modify the response.
        """
        buttons = kwargs.get("buttons")
        media = kwargs.get("media")
        thread_id = kwargs.get("thread_id")

        return FormattedResponse(
            messages=[response],
            buttons=buttons,
            media=media,
            thread_id=thread_id,
        )

    def parse_incoming(self, payload: dict) -> dict:
        """Parse incoming web request.

        Web requests are expected to be in our standard API format.
        """
        return {
            "user_id": payload.get("user_id", "anonymous"),
            "message": payload.get("message", ""),
            "session_id": payload.get("session_id"),
            "channel_id": "web",
            "thread_id": payload.get("thread_id"),
            "metadata": payload.get("metadata", {}),
        }
