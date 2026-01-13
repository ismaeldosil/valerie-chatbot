"""Base channel handler - abstract interface for all channel adapters."""

import re
from abc import ABC, abstractmethod

from pydantic import BaseModel


class ChannelConfig(BaseModel):
    """Configuration for a channel's capabilities and limits."""

    max_chars: int = 4096
    supports_markdown: bool = True
    supports_buttons: bool = True
    supports_media: bool = True
    supports_threading: bool = False
    rate_limit_per_minute: int | None = None


class FormattedResponse(BaseModel):
    """Response formatted for a specific channel."""

    messages: list[str]  # Can be multiple messages if chunked
    buttons: list[dict] | None = None
    media: list[str] | None = None
    thread_id: str | None = None
    metadata: dict | None = None


class BaseChannelHandler(ABC):
    """Abstract base class for channel handlers.

    Each channel (Slack, Teams, Web, etc.) implements this interface
    to adapt chatbot responses to their specific format and limitations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name identifier."""
        pass

    @property
    @abstractmethod
    def config(self) -> ChannelConfig:
        """Channel configuration with capabilities and limits."""
        pass

    @abstractmethod
    def format_response(self, response: str, **kwargs) -> FormattedResponse:
        """Format a response for this channel.

        Args:
            response: Raw response text from the chatbot
            **kwargs: Additional channel-specific options

        Returns:
            FormattedResponse adapted for this channel
        """
        pass

    @abstractmethod
    def parse_incoming(self, payload: dict) -> dict:
        """Parse incoming webhook payload from this channel.

        Args:
            payload: Raw webhook payload

        Returns:
            Normalized message dict with: user_id, message, channel_id, thread_id, etc.
        """
        pass

    def chunk_message(self, text: str, max_chars: int | None = None) -> list[str]:
        """Split a long message into chunks that fit the channel's limit.

        Args:
            text: Text to chunk
            max_chars: Override for max characters (uses config if not provided)

        Returns:
            List of message chunks
        """
        limit = max_chars or self.config.max_chars

        if len(text) <= limit:
            return [text]

        chunks = []
        current = ""

        # Split by paragraphs first
        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            # If single paragraph is too long, split by sentences
            if len(paragraph) > limit:
                sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                for sentence in sentences:
                    if len(current) + len(sentence) + 1 <= limit:
                        current += sentence + " "
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = sentence + " "
            elif len(current) + len(paragraph) + 2 <= limit:
                current += paragraph + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = paragraph + "\n\n"

        if current:
            chunks.append(current.strip())

        return chunks

    def strip_markdown(self, text: str) -> str:
        """Remove markdown formatting from text.

        Args:
            text: Text with markdown

        Returns:
            Plain text without markdown
        """
        # Bold and italic
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)

        # Links [text](url) -> text
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)

        # Headers
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

        # Code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`(.+?)`", r"\1", text)

        # Lists - convert to plain text
        text = re.sub(r"^\s*[-*+]\s+", "- ", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        return text.strip()

    def convert_buttons_to_text(self, buttons: list[dict]) -> str:
        """Convert interactive buttons to numbered text options.

        Args:
            buttons: List of button dicts with 'label' and 'value' keys

        Returns:
            Formatted text with numbered options
        """
        if not buttons:
            return ""

        lines = ["\nOptions:"]
        for i, btn in enumerate(buttons, 1):
            label = btn.get("label", btn.get("text", f"Option {i}"))
            lines.append(f"{i}. {label}")
        lines.append("\nReply with the number of your choice.")

        return "\n".join(lines)
