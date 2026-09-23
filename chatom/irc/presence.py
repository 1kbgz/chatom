"""IRC-specific presence model."""

from ..base import Field, Presence

__all__ = ("IRCPresence",)


class IRCPresence(Presence):
    """Presence derived from IRC activity and AWAY state."""

    away_message: str = Field(default="")
