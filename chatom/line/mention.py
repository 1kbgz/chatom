"""LINE mention fallbacks."""

from ..base import mention_channel, mention_user
from .channel import LineChannel
from .user import LineUser

__all__ = ("mention_channel", "mention_user")


@mention_user.register
def _mention_line_user(user: LineUser) -> str:
    return f"@{user.best_display_name}"


@mention_channel.register
def _mention_line_channel(channel: LineChannel) -> str:
    return f"#{channel.name or channel.id}"
