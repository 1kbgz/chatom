"""Symphony-specific Channel model.

This module provides the Symphony-specific Channel class.
In Symphony, channels are called "streams" or "rooms".
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import model_validator

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

    @model_validator(mode="after")
    def _sync_channel_type(self) -> "SymphonyChannel":
        """Sync channel_type from Symphony stream_type."""
        # Only update if not already set to a meaningful value
        if self.channel_type == ChannelType.UNKNOWN:
            object.__setattr__(self, "channel_type", self.generic_channel_type)
        return self

    @property
    def stream_id(self) -> str:
        """Alias for id - Symphony uses stream_id terminology.

        Returns:
            str: The stream/channel ID.
        """
        return self.id


# Alias for backwards compatibility
SymphonyRoom = SymphonyChannel
