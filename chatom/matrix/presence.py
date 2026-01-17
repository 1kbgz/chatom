"""Matrix-specific Presence model.

This module provides the Matrix-specific Presence class.
"""

from enum import Enum
from typing import Optional

from chatom.base import Field, Presence, PresenceStatus

__all__ = ("MatrixPresence", "MatrixPresenceStatus")


class MatrixPresenceStatus(str, Enum):
    """Matrix presence states as defined by the spec."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNAVAILABLE = "unavailable"


class MatrixPresence(Presence):
    """Matrix-specific presence.

    Attributes:
        matrix_presence: Matrix-specific presence state.
        currently_active: Whether the user is currently active.
        last_active_ago: Milliseconds since user was last active.
        status_msg: User's status message.
    """

    matrix_presence: MatrixPresenceStatus = Field(
        default=MatrixPresenceStatus.OFFLINE,
        description="Matrix-specific presence state.",
    )
    currently_active: bool = Field(
        default=False,
        description="Whether the user is currently active.",
    )
    last_active_ago: Optional[int] = Field(
        default=None,
        description="Milliseconds since user was last active.",
    )
    status_msg: str = Field(
        default="",
        description="User's status message.",
    )

    @property
    def generic_status(self) -> PresenceStatus:
        """Convert Matrix presence to generic status.

        Returns:
            PresenceStatus: The generic presence status.
        """
        status_map = {
            MatrixPresenceStatus.ONLINE: PresenceStatus.ONLINE,
            MatrixPresenceStatus.UNAVAILABLE: PresenceStatus.IDLE,
            MatrixPresenceStatus.OFFLINE: PresenceStatus.OFFLINE,
        }
        return status_map.get(self.matrix_presence, PresenceStatus.UNKNOWN)
