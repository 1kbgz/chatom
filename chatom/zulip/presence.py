"""Zulip-specific presence model."""

from enum import Enum

from ..base import Field, Presence, PresenceStatus

__all__ = ("ZulipPresence", "ZulipPresenceStatus")


class ZulipPresenceStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"

    @classmethod
    def from_base(cls, status: PresenceStatus) -> "ZulipPresenceStatus":
        if status == PresenceStatus.ONLINE:
            return cls.ACTIVE
        if status in (PresenceStatus.IDLE, PresenceStatus.DND):
            return cls.IDLE
        return cls.OFFLINE

    @property
    def generic(self) -> PresenceStatus:
        if self == self.ACTIVE:
            return PresenceStatus.ONLINE
        if self == self.IDLE:
            return PresenceStatus.IDLE
        return PresenceStatus.OFFLINE


class ZulipPresence(Presence):
    """Presence derived from Zulip's aggregated client status."""

    zulip_status: ZulipPresenceStatus = Field(default=ZulipPresenceStatus.OFFLINE)
    client: str = Field(default="aggregated", description="Zulip client whose presence was selected.")
