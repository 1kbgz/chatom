"""Zulip-specific channel model."""

from ..base import Channel, ChannelType, Field

__all__ = ("ZulipChannel",)


class ZulipChannel(Channel):
    """A Zulip channel (historically called a stream)."""

    description: str = Field(default="", description="Rendered channel description.")
    invite_only: bool = Field(default=False, description="Whether membership requires an invitation.")
    is_web_public: bool = Field(default=False, description="Whether channel history is publicly available on the web.")
    first_message_id: int | None = Field(default=None, description="First visible message ID in the channel.")

    @classmethod
    def from_api(cls, data: dict) -> "ZulipChannel":
        invite_only = bool(data.get("invite_only", False))
        return cls(
            id=str(data.get("stream_id", data.get("id", ""))),
            name=data.get("name", ""),
            topic=data.get("description", ""),
            description=data.get("description", ""),
            channel_type=ChannelType.PRIVATE if invite_only else ChannelType.PUBLIC,
            is_archived=bool(data.get("is_archived", False)),
            member_count=data.get("subscriber_count"),
            invite_only=invite_only,
            is_web_public=bool(data.get("is_web_public", False)),
            first_message_id=data.get("first_message_id"),
        )
