"""Channel model for chatom.

This module provides the base Channel class representing a chat channel or room.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from pydantic import model_validator

from .base import Field, Identifiable

if TYPE_CHECKING:
    from .user import User

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
        parent: Parent channel (for threads/subchannels).
        parent_id: ID of the parent channel (derived from parent).
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
    parent: Optional["Channel"] = Field(
        default=None,
        description="Parent channel (for threads/subchannels).",
    )
    users: List["User"] = Field(
        default_factory=list,
        description="Users in a DM channel (for DIRECT/GROUP types).",
    )

    @model_validator(mode="after")
    def _validate_dm_users(self) -> "Channel":
        """Validate that users field is appropriate for channel type."""
        if self.users:
            if self.channel_type == ChannelType.DIRECT:
                if len(self.users) != 1:
                    raise ValueError(f"DIRECT channel must have exactly 1 user, got {len(self.users)}")
            elif self.channel_type == ChannelType.GROUP:
                if len(self.users) < 2:
                    raise ValueError(f"GROUP channel must have at least 2 users, got {len(self.users)}")
            # If users are set but type is UNKNOWN, infer the type
            elif self.channel_type == ChannelType.UNKNOWN:
                if len(self.users) == 1:
                    object.__setattr__(self, "channel_type", ChannelType.DIRECT)
                else:
                    object.__setattr__(self, "channel_type", ChannelType.GROUP)
        return self

    @property
    def is_complete(self) -> bool:
        """Check if this channel has all required fields populated.

        A channel is complete if it has an ID. DM channels with users
        but no ID are considered incomplete (need resolution to get/create ID).

        Returns:
            bool: True if the channel is complete.
        """
        # DM channels with users but no ID need resolution
        if self.users and not self.id:
            return False
        return bool(self.id)

    @property
    def parent_id(self) -> str:
        """Get the parent channel's ID.

        Returns:
            str: The parent channel ID or empty string if no parent.
        """
        return self.parent.id if self.parent else ""

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

    @property
    def is_resolvable(self) -> bool:
        """Check if this channel can be resolved by a backend.

        A channel is resolvable if it has an id, name, or users (for DMs).

        Returns:
            bool: True if the channel can potentially be resolved.
        """
        return bool(self.id or self.name or self.users)

    @classmethod
    def dm_to(cls, user: "User") -> "Channel":
        """Create an incomplete DM channel to a user.

        The returned channel is marked incomplete and will be resolved
        by the backend (looking up or creating the DM channel).

        Args:
            user: The user to DM.

        Returns:
            An incomplete Channel that can be resolved to a DM.

        Example:
            >>> dm_channel = Channel.dm_to(user)
            >>> await backend.send_message(dm_channel, "Hello!")
        """
        channel = cls(
            channel_type=ChannelType.DIRECT,
            users=[user],
        )
        channel.mark_incomplete()
        return channel

    @classmethod
    def group_dm_to(cls, users: List["User"]) -> "Channel":
        """Create an incomplete group DM channel to multiple users.

        The returned channel is marked incomplete and will be resolved
        by the backend (looking up or creating the group DM).

        Args:
            users: The users to include in the group DM.

        Returns:
            An incomplete Channel that can be resolved to a group DM.

        Example:
            >>> group = Channel.group_dm_to([user1, user2])
            >>> await backend.send_message(group, "Hello everyone!")
        """
        channel = cls(
            channel_type=ChannelType.GROUP,
            users=users,
        )
        channel.mark_incomplete()
        return channel
