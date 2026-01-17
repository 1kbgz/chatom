"""Reaction model for chatom.

This module provides the Reaction class representing an emoji reaction.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from .base import BaseModel, Field
from .user import User

__all__ = ("Reaction", "Emoji", "ReactionEvent", "ReactionEventType")


class Emoji(BaseModel):
    """Represents an emoji that can be used in reactions.

    Attributes:
        name: The name of the emoji (e.g., 'thumbsup', 'smile').
        id: Platform-specific ID for custom emojis.
        unicode: Unicode representation for standard emojis.
        is_custom: Whether this is a custom emoji.
        url: URL of the emoji image for custom emojis.
    """

    name: str = Field(
        default="",
        description="The name of the emoji.",
    )
    id: str = Field(
        default="",
        description="Platform-specific ID for custom emojis.",
    )
    unicode: str = Field(
        default="",
        description="Unicode representation for standard emojis.",
    )
    is_custom: bool = Field(
        default=False,
        description="Whether this is a custom emoji.",
    )
    url: str = Field(
        default="",
        description="URL of the emoji image for custom emojis.",
    )

    def __str__(self) -> str:
        """Return string representation of the emoji.

        Returns:
            str: Unicode character or :name: format.
        """
        if self.unicode:
            return self.unicode
        return f":{self.name}:"


class Reaction(BaseModel):
    """Represents a reaction to a message.

    Attributes:
        emoji: The emoji used in the reaction.
        count: Number of times this reaction was added.
        users: List of users who added this reaction.
        me: Whether the current user added this reaction.
    """

    emoji: Emoji = Field(
        description="The emoji used in the reaction.",
    )
    count: int = Field(
        default=1,
        description="Number of times this reaction was added.",
    )
    users: List[User] = Field(
        default_factory=list,
        description="List of users who added this reaction.",
    )
    me: bool = Field(
        default=False,
        description="Whether the current user added this reaction.",
    )


class ReactionEventType(str, Enum):
    """Types of reaction events."""

    ADDED = "added"
    """A reaction was added to a message."""

    REMOVED = "removed"
    """A reaction was removed from a message."""


class ReactionEvent(BaseModel):
    """Represents a reaction event (add or remove) on a message.

    This model is used for handling incoming reaction events from backends.
    It provides the information needed to track who reacted to which message
    and with what emoji.

    Attributes:
        message_id: ID of the message the reaction is on.
        channel_id: ID of the channel containing the message.
        user_id: ID of the user who added/removed the reaction.
        user: The user who added/removed the reaction, if available.
        emoji: The emoji that was added/removed.
        event_type: Whether the reaction was added or removed.
        timestamp: When the reaction event occurred.

    Example:
        >>> # Handle a reaction event in a bot
        >>> async def on_reaction(event: ReactionEvent):
        ...     if event.event_type == ReactionEventType.ADDED:
        ...         print(f"User {event.user_id} added {event.emoji}")
    """

    message_id: str = Field(
        description="ID of the message the reaction is on.",
    )
    channel_id: str = Field(
        description="ID of the channel containing the message.",
    )
    user_id: str = Field(
        description="ID of the user who added/removed the reaction.",
    )
    user: Optional[User] = Field(
        default=None,
        description="The user who added/removed the reaction, if available.",
    )
    emoji: Emoji = Field(
        description="The emoji that was added/removed.",
    )
    event_type: ReactionEventType = Field(
        description="Whether the reaction was added or removed.",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the reaction event occurred.",
    )
    guild_id: str = Field(
        default="",
        description="ID of the guild/server, if applicable (Discord).",
    )
