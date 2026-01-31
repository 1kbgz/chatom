"""Slack-specific Presence model.

This module provides the Slack-specific Presence class.
"""

from enum import Enum
from typing import Optional

from chatom.base import Field, Presence, PresenceStatus

__all__ = ("SlackPresence", "SlackPresenceStatus")


class SlackPresenceStatus(str, Enum):
    """Slack-specific presence statuses."""

    ACTIVE = "active"
    AWAY = "away"
    AUTO = "auto"

    @classmethod
    def from_base(cls, status: PresenceStatus) -> "SlackPresenceStatus":
        """Convert a base PresenceStatus to SlackPresenceStatus.

        Args:
            status: The base PresenceStatus to convert.

        Returns:
            The corresponding SlackPresenceStatus.

        Example:
            >>> slack_status = SlackPresenceStatus.from_base(PresenceStatus.ONLINE)
            >>> print(slack_status)  # SlackPresenceStatus.ACTIVE
        """
        status_map = {
            PresenceStatus.ONLINE: cls.ACTIVE,
            PresenceStatus.IDLE: cls.AWAY,
            PresenceStatus.DND: cls.AWAY,
            PresenceStatus.INVISIBLE: cls.AWAY,
            PresenceStatus.OFFLINE: cls.AWAY,
            PresenceStatus.UNKNOWN: cls.AUTO,
        }
        return status_map.get(status, cls.AUTO)


class SlackPresence(Presence):
    """Slack-specific presence.

    Attributes:
        slack_presence: Slack-specific presence (active/away).
        auto_away: Whether user was automatically marked away.
        manual_away: Whether user manually set away.
        connection_count: Number of active connections.
        last_activity: Timestamp of last activity.
    """

    slack_presence: SlackPresenceStatus = Field(
        default=SlackPresenceStatus.AWAY,
        description="Slack-specific presence.",
    )
    auto_away: bool = Field(
        default=False,
        description="Whether user was automatically marked away.",
    )
    manual_away: bool = Field(
        default=False,
        description="Whether user manually set away.",
    )
    connection_count: int = Field(
        default=0,
        description="Number of active connections.",
    )
    last_activity: Optional[int] = Field(
        default=None,
        description="Timestamp of last activity.",
    )

    @property
    def generic_status(self) -> PresenceStatus:
        """Convert Slack presence to generic status.

        Returns:
            PresenceStatus: The generic presence status.
        """
        if self.slack_presence == SlackPresenceStatus.ACTIVE:
            return PresenceStatus.ONLINE
        return PresenceStatus.IDLE
