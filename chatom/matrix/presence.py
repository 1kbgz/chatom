"""Matrix-specific presence model."""

from enum import Enum

from chatom.base import Field, Presence, PresenceStatus
from chatom.base.conversion import register_backend_type

__all__ = ("MatrixPresence", "MatrixPresenceState")


class MatrixPresenceState(str, Enum):
    """Presence values defined by the Matrix client-server API."""

    ONLINE = "online"
    UNAVAILABLE = "unavailable"
    OFFLINE = "offline"

    @property
    def generic(self) -> PresenceStatus:
        """Convert to chatom presence status."""
        return {
            self.ONLINE: PresenceStatus.ONLINE,
            self.UNAVAILABLE: PresenceStatus.IDLE,
            self.OFFLINE: PresenceStatus.OFFLINE,
        }[self]


class MatrixPresence(Presence):
    """Matrix presence details."""

    matrix_presence: MatrixPresenceState = Field(default=MatrixPresenceState.OFFLINE)
    currently_active: bool = Field(default=False)
    last_active_ago: int = Field(default=0, description="Milliseconds since last activity.")


register_backend_type("matrix", Presence, MatrixPresence)
