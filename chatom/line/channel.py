"""LINE-specific channel model."""

from collections.abc import Mapping
from enum import Enum
from typing import Any

from ..base import Channel, ChannelType, Field
from ..base.conversion import register_backend_type

__all__ = ("LineChannel", "LineSourceType")


class LineSourceType(str, Enum):
    """Conversation source types emitted by LINE webhooks."""

    USER = "user"
    GROUP = "group"
    ROOM = "room"


class LineChannel(Channel):
    """LINE one-to-one, group, or legacy room conversation."""

    source_type: LineSourceType = Field(default=LineSourceType.USER)
    picture_url: str = Field(default="")

    @classmethod
    def from_source(cls, source: Mapping[str, Any]) -> "LineChannel":
        """Build a channel from a webhook source object."""
        source_type = LineSourceType(str(source.get("type", "user")))
        id_key = {LineSourceType.USER: "userId", LineSourceType.GROUP: "groupId", LineSourceType.ROOM: "roomId"}[source_type]
        channel_type = ChannelType.DIRECT if source_type == LineSourceType.USER else ChannelType.GROUP
        return cls(id=str(source.get(id_key, "")), source_type=source_type, channel_type=channel_type)

    @classmethod
    def from_group_summary(cls, data: Mapping[str, Any]) -> "LineChannel":
        """Build a group channel from a LINE group-summary response."""
        return cls(
            id=str(data.get("groupId", "")),
            name=str(data.get("groupName", "")),
            source_type=LineSourceType.GROUP,
            channel_type=ChannelType.GROUP,
            picture_url=str(data.get("pictureUrl", "")),
        )


register_backend_type("line", Channel, LineChannel)
