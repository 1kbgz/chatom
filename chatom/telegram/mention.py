"""Telegram-specific mention utilities.

This module registers Telegram-specific mention formatting.
Telegram uses HTML-style mentions: <a href="tg://user?id=123">Name</a>
or @username for public usernames.
"""

from chatom.base import mention_channel, mention_user

from .channel import TelegramChannel
from .user import TelegramUser

__all__ = ("mention_user", "mention_channel")


@mention_user.register
def _mention_telegram_user(user: TelegramUser) -> str:
    """Generate a Telegram mention string for a user.

    Uses @username if available, otherwise uses an HTML mention link.

    Args:
        user: The Telegram user to mention.

    Returns:
        str: The Telegram mention format.
    """
    if user.username:
        return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.display_name}</a>'


@mention_channel.register
def _mention_telegram_channel(channel: TelegramChannel) -> str:
    """Generate a Telegram mention string for a channel/chat.

    Telegram doesn't have native channel mentions in the same way as
    Slack/Discord. We use the channel name with a # prefix.

    Args:
        channel: The Telegram channel to mention.

    Returns:
        str: The channel reference.
    """
    return f"#{channel.name}" if channel.name else f"#{channel.id}"
