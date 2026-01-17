"""Symphony-specific Channel model.

This module provides the Symphony-specific Channel class.
In Symphony, channels are called "streams" or "rooms".
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from chatom.base import Channel, ChannelType, Field

__all__ = ("SymphonyChannel", "SymphonyRoom", "SymphonyStreamType")


class SymphonyStreamType(str, Enum):
    """Symphony stream types."""

    IM = "IM"
    """Instant message (1:1 chat)."""

    MIM = "MIM"
    """Multi-party instant message."""

    ROOM = "ROOM"
    """Chat room."""

    POST = "POST"
    """Wall post."""


class SymphonyChannel(Channel):
    """Symphony-specific channel (stream) with additional Symphony fields.

    Attributes:
        stream_type: The type of Symphony stream.
        external: Whether the stream includes external users.
        cross_pod: Whether the stream is cross-pod.
        active: Whether the stream is active.
        read_only: Whether the stream is read-only.
        public: Whether the stream is public.
        members: List of user IDs in the stream.
        creation_date: When the stream was created.
        last_message_date: When the last message was sent.
    """

    stream_type: SymphonyStreamType = Field(
        default=SymphonyStreamType.ROOM,
        description="The type of Symphony stream.",
    )
    external: bool = Field(
        default=False,
        description="Whether the stream includes external users.",
    )
    cross_pod: bool = Field(
        default=False,
        description="Whether the stream is cross-pod.",
    )
    active: bool = Field(
        default=True,
        description="Whether the stream is active.",
    )
    read_only: bool = Field(
        default=False,
        description="Whether the stream is read-only.",
    )
    public: bool = Field(
        default=False,
        description="Whether the stream is public.",
    )
    members: List[str] = Field(
        default_factory=list,
        description="List of user IDs in the stream.",
    )
    creation_date: Optional[datetime] = Field(
        default=None,
        description="When the stream was created.",
    )
    last_message_date: Optional[datetime] = Field(
        default=None,
        description="When the last message was sent.",
    )

    @property
    def generic_channel_type(self) -> ChannelType:
        """Convert Symphony stream type to generic channel type.

        Returns:
            ChannelType: The generic channel type.
        """
        if self.stream_type == SymphonyStreamType.IM:
            return ChannelType.DIRECT
        elif self.stream_type == SymphonyStreamType.MIM:
            return ChannelType.GROUP
        elif self.public:
            return ChannelType.PUBLIC
        return ChannelType.PRIVATE


# Alias for backwards compatibility
SymphonyRoom = SymphonyChannel
