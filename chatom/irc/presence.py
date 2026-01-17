"""IRC-specific Presence model.

This module provides the IRC-specific Presence class.
"""

from chatom.base import Field, Presence, PresenceStatus

__all__ = ("IRCPresence",)


class IRCPresence(Presence):
    """IRC-specific presence.

    IRC presence is simpler than modern chat platforms,
    primarily consisting of away status.

    Attributes:
        is_away: Whether the user is marked as away.
        away_message: The user's away message.
        idle_time: Seconds since user's last activity.
        signon_time: Unix timestamp when user connected.
        server: The server the user is connected to.
        channels: List of channels the user is in.
    """

    is_away: bool = Field(
        default=False,
        description="Whether the user is marked as away.",
    )
    away_message: str = Field(
        default="",
        description="The user's away message.",
    )
    idle_time: int = Field(
        default=0,
        description="Seconds since user's last activity.",
    )
    signon_time: int = Field(
        default=0,
        description="Unix timestamp when user connected.",
    )
    server: str = Field(
        default="",
        description="The server the user is connected to.",
    )
    channels: list = Field(
        default_factory=list,
        description="List of channels the user is in.",
    )

    @property
    def generic_status(self) -> PresenceStatus:
        """Convert IRC presence to generic status.

        Returns:
            PresenceStatus: The generic presence status.
        """
        if self.is_away:
            return PresenceStatus.IDLE
        return PresenceStatus.ONLINE
