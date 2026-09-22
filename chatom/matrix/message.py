"""Matrix-specific message model."""

from typing import Any

from chatom.base import Field, Message

__all__ = ("MatrixMessage",)


class MatrixMessage(Message):
    """A Matrix room message event."""

    msgtype: str = Field(default="m.text", description="Matrix message type.")
    event_type: str = Field(default="m.room.message", description="Matrix event type.")
    transaction_id: str = Field(default="", description="Client transaction ID when available.")
    relates_to: dict[str, Any] = Field(default_factory=dict, description="Matrix relation data.")

    @property
    def event_id(self) -> str:
        """Return Matrix event ID."""
        return self.id

    @property
    def room_id(self) -> str:
        """Return containing room ID."""
        return self.channel.id if self.channel else ""
