"""Discord-specific Presence model.

This module provides the Discord-specific Presence class.
"""

from enum import Enum

from chatom.base import Activity, Field, Presence, PresenceStatus

__all__ = ("DiscordPresence", "DiscordActivityType")


class DiscordActivityType(str, Enum):
    """Discord-specific activity types."""

    PLAYING = "playing"
    STREAMING = "streaming"
    LISTENING = "listening"
    WATCHING = "watching"
    CUSTOM = "custom"
    COMPETING = "competing"


class DiscordActivity(Activity):
    """Discord-specific activity.

    Attributes:
        state: The user's current party status.
        details: What the player is currently doing.
        application_id: Application ID for the game.
        large_image: Large image asset key.
        large_text: Text displayed when hovering over large image.
        small_image: Small image asset key.
        small_text: Text displayed when hovering over small image.
    """

    state: str = Field(
        default="",
        description="The user's current party status.",
    )
    details: str = Field(
        default="",
        description="What the player is currently doing.",
    )
    application_id: str = Field(
        default="",
        description="Application ID for the game.",
    )
    large_image: str = Field(
        default="",
        description="Large image asset key.",
    )
    large_text: str = Field(
        default="",
        description="Text displayed when hovering over large image.",
    )
    small_image: str = Field(
        default="",
        description="Small image asset key.",
    )
    small_text: str = Field(
        default="",
        description="Text displayed when hovering over small image.",
    )


class DiscordPresence(Presence):
    """Discord-specific presence.

    Attributes:
        activities: List of activities the user is engaged in.
        client_status: Status per client (desktop, mobile, web).
    """

    activities: list = Field(
        default_factory=list,
        description="List of activities the user is engaged in.",
    )
    desktop_status: PresenceStatus = Field(
        default=PresenceStatus.OFFLINE,
        description="Status on desktop client.",
    )
    mobile_status: PresenceStatus = Field(
        default=PresenceStatus.OFFLINE,
        description="Status on mobile client.",
    )
    web_status: PresenceStatus = Field(
        default=PresenceStatus.OFFLINE,
        description="Status on web client.",
    )
