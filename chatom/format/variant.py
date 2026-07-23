"""Format variant definitions for chatom.

This module defines the different output formats supported by chatom.
"""

from enum import Enum
from typing import Literal, Union

__all__ = (
    "DISCORD_MARKDOWN",
    "FORMAT",
    "HTML",
    "MARKDOWN",
    "PLAINTEXT",
    "SLACK_MARKDOWN",
    "SYMPHONY_MESSAGEML",
    "TELEGRAM_HTML",
    "Format",
)

# String constants for backwards compatibility
PLAINTEXT = "plaintext"
MARKDOWN = "markdown"
SLACK_MARKDOWN = "slack-markdown"
DISCORD_MARKDOWN = "discord-markdown"
HTML = "html"
TELEGRAM_HTML = "telegram-html"
SYMPHONY_MESSAGEML = "symphony-messageml"
# Alias for backwards compatibility
SYMPHONY_HTML = SYMPHONY_MESSAGEML


class Format(str, Enum):
    """Supported output formats."""

    PLAINTEXT = "plaintext"
    """Plain text with no formatting."""

    MARKDOWN = "markdown"
    """Standard CommonMark Markdown."""

    SLACK_MARKDOWN = "slack-markdown"
    """Slack's mrkdwn format (differs from standard Markdown)."""

    DISCORD_MARKDOWN = "discord-markdown"
    """Discord's flavor of Markdown."""

    HTML = "html"
    """Standard HTML."""

    TELEGRAM_HTML = "telegram-html"
    """Telegram Bot API HTML subset."""

    SYMPHONY_MESSAGEML = "symphony-messageml"
    """Symphony's MessageML format (XML-based)."""


# Type alias for format specification
FORMAT = Union[Literal["plaintext", "markdown", "slack-markdown", "discord-markdown", "html", "telegram-html", "symphony-messageml"], Format, str]  # noqa: UP007
