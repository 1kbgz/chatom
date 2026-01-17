"""Thread model for chatom.

This module provides the Thread class representing a message thread.
"""

from datetime import datetime
from typing import Optional

from .base import Field, Identifiable
from .channel import Channel

__all__ = ("Thread",)


class Thread(Identifiable):
    """Represents a thread within a channel.

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the thread.
        parent_channel: The channel this thread belongs to.
        parent_message_id: ID of the message that started the thread.
        message_count: Number of messages in the thread.
        is_locked: Whether the thread is locked from new messages.
        created_at: When the thread was created.
        last_message_at: When the last message was posted.
    """

    parent_channel: Optional[Channel] = Field(
        default=None,
        description="The channel this thread belongs to.",
    )
    parent_message_id: str = Field(
        default="",
        description="ID of the message that started the thread.",
    )
    message_count: int = Field(
        default=0,
        description="Number of messages in the thread.",
    )
    is_locked: bool = Field(
        default=False,
        description="Whether the thread is locked from new messages.",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the thread was created.",
    )
    last_message_at: Optional[datetime] = Field(
        default=None,
        description="When the last message was posted.",
    )
