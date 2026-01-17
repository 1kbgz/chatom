"""Discord-specific mention utilities.

This module registers Discord-specific mention formatting.
"""

from chatom.base import mention_channel, mention_user

from .channel import DiscordChannel
from .user import DiscordUser

__all__ = ("mention_user", "mention_channel")


@mention_user.register
def _mention_discord_user(user: DiscordUser) -> str:
    """Generate a Discord mention string for a user.

    Args:
        user: The Discord user to mention.

    Returns:
        str: The Discord mention format <@user_id>.
    """
    return f"<@{user.id}>"


@mention_channel.register
def _mention_discord_channel(channel: DiscordChannel) -> str:
    """Generate a Discord mention string for a channel.

    Args:
        channel: The Discord channel to mention.

    Returns:
        str: The Discord mention format <#channel_id>.
    """
    return f"<#{channel.id}>"


def mention_role(role_id: str) -> str:
    """Generate a Discord mention string for a role.

    Args:
        role_id: The role ID to mention.

    Returns:
        str: The Discord role mention format <@&role_id>.
    """
    return f"<@&{role_id}>"


def mention_everyone() -> str:
    """Generate a Discord @everyone mention.

    Returns:
        str: The @everyone mention.
    """
    return "@everyone"


def mention_here() -> str:
    """Generate a Discord @here mention.

    Returns:
        str: The @here mention.
    """
    return "@here"
