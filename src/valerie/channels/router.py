"""Channel router - routes messages to the appropriate channel handler."""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseChannelHandler, FormattedResponse


class Channel(str, Enum):
    """Supported communication channels."""

    WEB = "web"
    SLACK = "slack"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"
    API = "api"


class ChannelRouter:
    """Routes responses to the appropriate channel handler.

    This class manages channel handlers and provides a unified interface
    for formatting responses across different platforms.
    """

    _handlers: dict[Channel, "BaseChannelHandler"] = {}
    _initialized: bool = False

    @classmethod
    def _init_handlers(cls) -> None:
        """Lazily initialize handlers to avoid circular imports."""
        if cls._initialized:
            return

        from .slack import SlackHandler
        from .teams import TeamsHandler
        from .web import WebHandler

        cls._handlers = {
            Channel.WEB: WebHandler(),
            Channel.SLACK: SlackHandler(),
            Channel.TEAMS: TeamsHandler(),
            Channel.API: WebHandler(),  # API uses web handler (no limits)
        }
        cls._initialized = True

    @classmethod
    def get_handler(cls, channel: Channel | str) -> "BaseChannelHandler":
        """Get the handler for a specific channel.

        Args:
            channel: Channel enum or string identifier

        Returns:
            The appropriate channel handler

        Raises:
            ValueError: If channel is not supported
        """
        cls._init_handlers()

        if isinstance(channel, str):
            try:
                channel = Channel(channel.lower())
            except ValueError:
                raise ValueError(f"Unknown channel: {channel}")

        if channel not in cls._handlers:
            raise ValueError(f"No handler registered for channel: {channel}")

        return cls._handlers[channel]

    @classmethod
    def format_response(
        cls,
        response: str,
        channel: Channel | str,
        **kwargs,
    ) -> "FormattedResponse":
        """Format a response for a specific channel.

        Args:
            response: Raw response text
            channel: Target channel
            **kwargs: Additional formatting options

        Returns:
            FormattedResponse adapted for the channel
        """
        handler = cls.get_handler(channel)
        return handler.format_response(response, **kwargs)

    @classmethod
    def parse_incoming(cls, channel: Channel | str, payload: dict) -> dict:
        """Parse an incoming webhook payload.

        Args:
            channel: Source channel
            payload: Raw webhook payload

        Returns:
            Normalized message dict
        """
        handler = cls.get_handler(channel)
        return handler.parse_incoming(payload)

    @classmethod
    def register_handler(cls, channel: Channel, handler: "BaseChannelHandler") -> None:
        """Register a custom handler for a channel.

        Args:
            channel: Channel to register
            handler: Handler instance
        """
        cls._init_handlers()
        cls._handlers[channel] = handler

    @classmethod
    def list_channels(cls) -> list[str]:
        """List all available channels.

        Returns:
            List of channel names
        """
        cls._init_handlers()
        return [c.value for c in cls._handlers.keys()]
