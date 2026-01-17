"""Symphony-specific Presence model.

This module provides the Symphony-specific Presence class.
"""

from enum import Enum
from typing import Optional

from chatom.base import Field, Presence, PresenceStatus

__all__ = ("SymphonyPresence", "SymphonyPresenceStatus")


class SymphonyPresenceStatus(str, Enum):
    """Symphony-specific presence statuses."""

    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    AWAY = "AWAY"
    ON_THE_PHONE = "ON_THE_PHONE"
    BE_RIGHT_BACK = "BE_RIGHT_BACK"
    IN_A_MEETING = "IN_A_MEETING"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    OFF_WORK = "OFF_WORK"
    OFFLINE = "OFFLINE"


class SymphonyPresence(Presence):
    """Symphony-specific presence.

    Attributes:
        symphony_status: Symphony-specific status enum.
        category: Presence category.
        timestamp: When the presence was last updated.
    """

    symphony_status: SymphonyPresenceStatus = Field(
        default=SymphonyPresenceStatus.OFFLINE,
        description="Symphony-specific status.",
    )
    category: str = Field(
        default="",
        description="Presence category.",
    )
    timestamp: Optional[int] = Field(
        default=None,
        description="When the presence was last updated (epoch ms).",
    )

    @property
    def generic_status(self) -> PresenceStatus:
        """Convert Symphony status to generic status.

        Returns:
            PresenceStatus: The generic presence status.
        """
        status_map = {
            SymphonyPresenceStatus.AVAILABLE: PresenceStatus.ONLINE,
            SymphonyPresenceStatus.BUSY: PresenceStatus.DND,
            SymphonyPresenceStatus.ON_THE_PHONE: PresenceStatus.DND,
            SymphonyPresenceStatus.IN_A_MEETING: PresenceStatus.DND,
            SymphonyPresenceStatus.AWAY: PresenceStatus.IDLE,
            SymphonyPresenceStatus.BE_RIGHT_BACK: PresenceStatus.IDLE,
            SymphonyPresenceStatus.OUT_OF_OFFICE: PresenceStatus.IDLE,
            SymphonyPresenceStatus.OFF_WORK: PresenceStatus.OFFLINE,
            SymphonyPresenceStatus.OFFLINE: PresenceStatus.OFFLINE,
        }
        return status_map.get(self.symphony_status, PresenceStatus.UNKNOWN)
