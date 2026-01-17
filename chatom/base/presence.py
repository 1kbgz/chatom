"""Presence model for chatom.

This module provides the Presence class representing a user's online status.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from .base import BaseModel, Field
from .user import User

__all__ = ("Presence", "PresenceStatus", "Activity", "ActivityType")


class PresenceStatus(str, Enum):
    """User presence status."""

    ONLINE = "online"
    """User is online and active."""

    IDLE = "idle"
    """User is online but idle/away."""

    DND = "dnd"
    """User is in do not disturb mode."""

    OFFLINE = "offline"
    """User is offline."""

    INVISIBLE = "invisible"
    """User is online but appearing offline."""

    UNKNOWN = "unknown"
    """Unknown status."""


class ActivityType(str, Enum):
    """Types of user activities."""

    PLAYING = "playing"
    """Playing a game."""

    STREAMING = "streaming"
    """Streaming content."""

    LISTENING = "listening"
    """Listening to music."""

    WATCHING = "watching"
    """Watching content."""

    CUSTOM = "custom"
    """Custom status."""

    COMPETING = "competing"
    """Competing in something."""


class Activity(BaseModel):
    """Represents a user's current activity.

    Attributes:
        name: Name of the activity.
        activity_type: Type of activity.
        details: Additional details about the activity.
        url: URL associated with the activity (e.g., stream URL).
        started_at: When the activity started.
    """

    name: str = Field(
        default="",
        description="Name of the activity.",
    )
    activity_type: ActivityType = Field(
        default=ActivityType.CUSTOM,
        description="Type of activity.",
    )
    details: str = Field(
        default="",
        description="Additional details about the activity.",
    )
    url: str = Field(
        default="",
        description="URL associated with the activity.",
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="When the activity started.",
    )


class Presence(BaseModel):
    """Represents a user's presence/online status.

    Attributes:
        user: The user this presence belongs to.
        status: Current presence status.
        status_text: Custom status text/message.
        activity: Current activity, if any.
        last_seen: When the user was last active.
        is_mobile: Whether the user is on a mobile device.
    """

    user: Optional[User] = Field(
        default=None,
        description="The user this presence belongs to.",
    )
    status: PresenceStatus = Field(
        default=PresenceStatus.UNKNOWN,
        description="Current presence status.",
    )
    status_text: str = Field(
        default="",
        description="Custom status text/message.",
    )
    activity: Optional[Activity] = Field(
        default=None,
        description="Current activity, if any.",
    )
    last_seen: Optional[datetime] = Field(
        default=None,
        description="When the user was last active.",
    )
    is_mobile: bool = Field(
        default=False,
        description="Whether the user is on a mobile device.",
    )

    @property
    def is_online(self) -> bool:
        """Check if user is currently online.

        Returns:
            bool: True if user is online (any non-offline status).
        """
        return self.status in (
            PresenceStatus.ONLINE,
            PresenceStatus.IDLE,
            PresenceStatus.DND,
        )

    @property
    def is_available(self) -> bool:
        """Check if user is available for messaging.

        Returns:
            bool: True if user is online and not DND.
        """
        return self.status in (PresenceStatus.ONLINE, PresenceStatus.IDLE)
