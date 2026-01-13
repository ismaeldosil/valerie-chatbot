"""Channel adapters for multi-platform chatbot integration.

This module implements the Channel Adapter Pattern for adapting chatbot responses
to different communication platforms (Slack, MS Teams, Web, etc.).
"""

from .base import BaseChannelHandler, ChannelConfig, FormattedResponse
from .router import Channel, ChannelRouter
from .slack import SlackHandler
from .teams import TeamsHandler
from .web import WebHandler

__all__ = [
    "BaseChannelHandler",
    "ChannelConfig",
    "FormattedResponse",
    "Channel",
    "ChannelRouter",
    "SlackHandler",
    "TeamsHandler",
    "WebHandler",
]
