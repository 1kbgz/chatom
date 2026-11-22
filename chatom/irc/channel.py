"""IRC-specific channel model."""

from pydantic import model_validator

from ..base import Channel, ChannelType, Field
from ..base.conversion import register_backend_type

__all__ = ("IRCChannel",)


class IRCChannel(Channel):
    """IRC channel or nickname target."""

    modes: list[str] = Field(default_factory=list)
    key_required: bool = False

    @model_validator(mode="after")
    def _infer_channel_type(self) -> "IRCChannel":
        if self.channel_type == ChannelType.UNKNOWN:
            object.__setattr__(
                self,
                "channel_type",
                ChannelType.PUBLIC if self.id.startswith(("#", "&", "+", "!")) else ChannelType.DIRECT,
            )
        return self


register_backend_type("irc", Channel, IRCChannel)
