"""Zulip-specific message model."""

from typing import Any

from ..base import Field, Message

__all__ = ("ZulipMessage",)


class ZulipMessage(Message):
    """Message fields specific to Zulip's topic-oriented API."""

    topic: str = Field(default="", description="Topic for a channel message.")
    recipient_id: int | None = Field(default=None, description="Zulip recipient ID.")
    sender_email: str = Field(default="", description="Sender's Zulip API email.")
    client: str = Field(default="", description="Client that sent the message.")
    flags: list[str] = Field(default_factory=list, description="Per-user Zulip message flags.")
    zulip_reactions: list[dict[str, Any]] = Field(default_factory=list, description="Raw Zulip reaction objects.")

    @property
    def subject(self) -> str:
        """Legacy Zulip name for topic."""
        return self.topic
