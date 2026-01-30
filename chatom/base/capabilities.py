"""Backend capabilities for chatom.

This module defines the capabilities that different chat backends support.
"""

from enum import Enum
from typing import FrozenSet

from .base import BaseModel, Field

__all__ = (
    "Capability",
    "BackendCapabilities",
    "DISCORD_CAPABILITIES",
    "SLACK_CAPABILITIES",
    "SYMPHONY_CAPABILITIES",
)


class Capability(str, Enum):
    """Capabilities that a chat backend may support."""

    # Text formatting
    PLAINTEXT = "plaintext"
    """Supports plain text messages."""

    MARKDOWN = "markdown"
    """Supports standard Markdown formatting."""

    RICH_TEXT = "rich_text"
    """Supports rich text formatting."""

    HTML = "html"
    """Supports HTML formatting."""

    CODE_BLOCKS = "code_blocks"
    """Supports code blocks with syntax highlighting."""

    # Media
    IMAGES = "images"
    """Supports image attachments."""

    FILES = "files"
    """Supports file attachments."""

    EMBEDS = "embeds"
    """Supports rich embeds."""

    VIDEOS = "videos"
    """Supports video attachments."""

    AUDIO = "audio"
    """Supports audio attachments."""

    # Reactions
    EMOJI_REACTIONS = "emoji_reactions"
    """Supports emoji reactions on messages."""

    CUSTOM_EMOJI = "custom_emoji"
    """Supports custom emoji."""

    # Threading
    THREADS = "threads"
    """Supports message threads."""

    REPLIES = "replies"
    """Supports direct replies to messages."""

    # Mentions
    USER_MENTIONS = "user_mentions"
    """Supports mentioning users."""

    CHANNEL_MENTIONS = "channel_mentions"
    """Supports mentioning channels."""

    EVERYONE_MENTION = "everyone_mention"
    """Supports mentioning everyone/all."""

    ROLE_MENTIONS = "role_mentions"
    """Supports mentioning roles/groups."""

    # Message features
    EDITING = "editing"
    """Supports editing sent messages."""

    DELETING = "deleting"
    """Supports deleting messages."""

    PINNING = "pinning"
    """Supports pinning messages."""

    # Tables
    TABLES = "tables"
    """Supports table rendering."""

    # Presence
    PRESENCE = "presence"
    """Supports user presence/status."""

    TYPING_INDICATORS = "typing_indicators"
    """Supports typing indicators."""

    # Interactive
    BUTTONS = "buttons"
    """Supports interactive buttons."""

    FORMS = "forms"
    """Supports forms/dialogs."""

    SELECT_MENUS = "select_menus"
    """Supports select menus/dropdowns."""

    # Organizations
    ORGANIZATIONS = "organizations"
    """Supports organization/guild/workspace operations."""

    # Search
    MESSAGE_SEARCH = "message_search"
    """Supports searching messages by content."""


class BackendCapabilities(BaseModel):
    """Describes the capabilities of a chat backend.

    Attributes:
        capabilities: Set of supported capabilities.
        max_message_length: Maximum message length in characters.
        max_attachment_size: Maximum attachment size in bytes.
        max_attachments: Maximum number of attachments per message.
        max_embeds: Maximum number of embeds per message.
        max_reactions: Maximum reactions per message.
    """

    capabilities: FrozenSet[Capability] = Field(
        default_factory=frozenset,
        description="Set of supported capabilities.",
    )
    max_message_length: int = Field(
        default=4000,
        description="Maximum message length in characters.",
    )
    max_attachment_size: int = Field(
        default=25 * 1024 * 1024,  # 25 MB
        description="Maximum attachment size in bytes.",
    )
    max_attachments: int = Field(
        default=10,
        description="Maximum number of attachments per message.",
    )
    max_embeds: int = Field(
        default=10,
        description="Maximum number of embeds per message.",
    )
    max_reactions: int = Field(
        default=20,
        description="Maximum reactions per message.",
    )

    def supports(self, capability: Capability) -> bool:
        """Check if a capability is supported.

        Args:
            capability: The capability to check.

        Returns:
            bool: True if the capability is supported.
        """
        return capability in self.capabilities

    def supports_all(self, *capabilities: Capability) -> bool:
        """Check if all capabilities are supported.

        Args:
            *capabilities: Capabilities to check.

        Returns:
            bool: True if all capabilities are supported.
        """
        return all(c in self.capabilities for c in capabilities)

    def supports_any(self, *capabilities: Capability) -> bool:
        """Check if any capability is supported.

        Args:
            *capabilities: Capabilities to check.

        Returns:
            bool: True if any capability is supported.
        """
        return any(c in self.capabilities for c in capabilities)


# Pre-defined capability sets for known backends
DISCORD_CAPABILITIES = BackendCapabilities(
    capabilities=frozenset(
        {
            Capability.PLAINTEXT,
            Capability.MARKDOWN,
            Capability.CODE_BLOCKS,
            Capability.IMAGES,
            Capability.FILES,
            Capability.EMBEDS,
            Capability.VIDEOS,
            Capability.AUDIO,
            Capability.EMOJI_REACTIONS,
            Capability.CUSTOM_EMOJI,
            Capability.THREADS,
            Capability.REPLIES,
            Capability.USER_MENTIONS,
            Capability.CHANNEL_MENTIONS,
            Capability.EVERYONE_MENTION,
            Capability.ROLE_MENTIONS,
            Capability.EDITING,
            Capability.DELETING,
            Capability.PINNING,
            Capability.PRESENCE,
            Capability.TYPING_INDICATORS,
            Capability.BUTTONS,
            Capability.SELECT_MENUS,
            Capability.ORGANIZATIONS,
            Capability.MESSAGE_SEARCH,
        }
    ),
    max_message_length=2000,
    max_attachment_size=25 * 1024 * 1024,
    max_attachments=10,
    max_embeds=10,
    max_reactions=20,
)

SLACK_CAPABILITIES = BackendCapabilities(
    capabilities=frozenset(
        {
            Capability.PLAINTEXT,
            Capability.MARKDOWN,
            Capability.RICH_TEXT,
            Capability.CODE_BLOCKS,
            Capability.IMAGES,
            Capability.FILES,
            Capability.EMBEDS,
            Capability.EMOJI_REACTIONS,
            Capability.CUSTOM_EMOJI,
            Capability.THREADS,
            Capability.REPLIES,
            Capability.USER_MENTIONS,
            Capability.CHANNEL_MENTIONS,
            Capability.EVERYONE_MENTION,
            Capability.EDITING,
            Capability.DELETING,
            Capability.PINNING,
            Capability.PRESENCE,
            Capability.TYPING_INDICATORS,
            Capability.BUTTONS,
            Capability.FORMS,
            Capability.SELECT_MENUS,
            Capability.TABLES,
            Capability.MESSAGE_SEARCH,
        }
    ),
    max_message_length=40000,
    max_attachment_size=1024 * 1024 * 1024,  # 1 GB for paid
    max_attachments=10,
    max_embeds=20,
    max_reactions=23,
)

SYMPHONY_CAPABILITIES = BackendCapabilities(
    capabilities=frozenset(
        {
            Capability.PLAINTEXT,
            Capability.RICH_TEXT,
            Capability.HTML,
            Capability.CODE_BLOCKS,
            Capability.IMAGES,
            Capability.FILES,
            Capability.EMOJI_REACTIONS,
            Capability.USER_MENTIONS,
            Capability.EDITING,
            Capability.DELETING,
            Capability.TABLES,
            Capability.FORMS,
            Capability.MESSAGE_SEARCH,
        }
    ),
    max_message_length=40000,
    max_attachment_size=25 * 1024 * 1024,
)
