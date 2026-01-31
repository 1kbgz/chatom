"""Thread model for chatom.

This module provides the Thread class representing a message thread.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .base import Field, Identifiable
from .channel import Channel

if TYPE_CHECKING:
    from .message import Message

__all__ = ("Thread",)


class Thread(Identifiable):
    """Represents a thread within a channel.

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the thread.
        parent_channel: The channel this thread belongs to.
        parent_message: The message that started the thread.
        message_count: Number of messages in the thread.
        is_locked: Whether the thread is locked from new messages.
        created_at: When the thread was created.
        last_message_at: When the last message was posted.
    """

    parent_channel: Optional[Channel] = Field(
        default=None,
        description="The channel this thread belongs to.",
    )
    parent_message: Optional["Message"] = Field(
        default=None,
        description="The message that started the thread.",
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

    @property
    def parent_message_id(self) -> str:
        """Get the parent message's ID.

        Returns:
            str: The parent message ID or empty string if no parent message.
        """
        return self.parent_message.id if self.parent_message else ""

    @property
    def is_resolvable(self) -> bool:
        """Check if this thread can be resolved by a backend.

        A thread is resolvable if it has an id or a parent_message.

        Returns:
            bool: True if the thread can potentially be resolved.
        """
        return bool(self.id or self.parent_message)
