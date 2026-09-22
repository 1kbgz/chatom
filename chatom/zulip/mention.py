"""Zulip mention formatting."""

from ..base import mention_channel, mention_user
from .channel import ZulipChannel
from .user import ZulipUser

__all__ = ("mention_channel", "mention_user")


@mention_user.register
def _mention_zulip_user(user: ZulipUser) -> str:
    name = user.mention_name
    return f"@**{name}|{user.id}**" if user.id else f"@**{name}**"


@mention_channel.register
def _mention_zulip_channel(channel: ZulipChannel) -> str:
    return f"#**{channel.name}**"
