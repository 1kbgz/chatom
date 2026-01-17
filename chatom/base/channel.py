"""Channel model for chatom.

This module provides the base Channel class representing a chat channel or room.
"""

from enum import Enum
from typing import Optional

from .base import Field, Identifiable

__all__ = ("Channel", "ChannelType")


class ChannelType(str, Enum):
    """Types of chat channels."""

    PUBLIC = "public"
    """A public channel visible to all members."""

    PRIVATE = "private"
    """A private channel with restricted access."""

    DIRECT = "direct"
    """A direct message between two users."""

    GROUP = "group"
    """A group direct message between multiple users."""

    THREAD = "thread"
    """A thread within another channel."""

    FORUM = "forum"
    """A forum channel for organized discussions."""

    ANNOUNCEMENT = "announcement"
    """An announcement or broadcast channel."""

    UNKNOWN = "unknown"
    """Unknown channel type."""


class Channel(Identifiable):
    """Represents a channel or room on a chat platform.

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the channel.
        topic: Channel topic or description.
        channel_type: Type of the channel (public, private, etc.).
        is_archived: Whether the channel is archived.
        member_count: Number of members in the channel.
        parent_id: ID of the parent channel (for threads/subchanels).
    """

    topic: str = Field(
        default="",
        description="Channel topic or description.",
    )
    channel_type: ChannelType = Field(
        default=ChannelType.UNKNOWN,
        description="Type of the channel.",
    )
    is_archived: bool = Field(
        default=False,
        description="Whether the channel is archived.",
    )
    member_count: Optional[int] = Field(
        default=None,
        description="Number of members in the channel.",
    )
    parent_id: str = Field(
        default="",
        description="ID of the parent channel (for threads/subchannels).",
    )

    @property
    def is_thread(self) -> bool:
        """Check if this channel is a thread.

        Returns:
            bool: True if this is a thread channel.
        """
        return self.channel_type == ChannelType.THREAD

    @property
    def is_direct_message(self) -> bool:
        """Check if this channel is a direct message.

        Returns:
            bool: True if this is a DM or group DM.
        """
        return self.channel_type in (ChannelType.DIRECT, ChannelType.GROUP)

    @property
    def is_dm(self) -> bool:
        """Alias for is_direct_message.

        Returns:
            bool: True if this is a DM or group DM.
        """
        return self.is_direct_message

    @property
    def is_public(self) -> bool:
        """Check if this channel is public.

        Returns:
            bool: True if this is a public channel.
        """
        return self.channel_type == ChannelType.PUBLIC

    @property
    def is_private(self) -> bool:
        """Check if this channel is private.

        Returns:
            bool: True if this is a private channel.
        """
        return self.channel_type == ChannelType.PRIVATE
