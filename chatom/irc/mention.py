"""IRC mention utilities."""

from ..base import mention_channel, mention_user
from .channel import IRCChannel
from .user import IRCUser

__all__ = ("mention_channel", "mention_user")


@mention_user.register
def _mention_irc_user(user: IRCUser) -> str:
    return user.nickname or user.handle or user.name or user.id


@mention_channel.register
def _mention_irc_channel(channel: IRCChannel) -> str:
    return channel.id or channel.name
