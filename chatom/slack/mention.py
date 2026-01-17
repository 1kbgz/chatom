"""Slack-specific mention utilities.

This module registers Slack-specific mention formatting.
"""

from chatom.base import mention_channel, mention_user

from .channel import SlackChannel
from .user import SlackUser

__all__ = ("mention_user", "mention_channel")


@mention_user.register
def _mention_slack_user(user: SlackUser) -> str:
    """Generate a Slack mention string for a user.

    Args:
        user: The Slack user to mention.

    Returns:
        str: The Slack mention format <@user_id>.
    """
    return f"<@{user.id}>"


@mention_channel.register
def _mention_slack_channel(channel: SlackChannel) -> str:
    """Generate a Slack mention string for a channel.

    Args:
        channel: The Slack channel to mention.

    Returns:
        str: The Slack mention format <#channel_id>.
    """
    return f"<#{channel.id}>"


def mention_user_group(usergroup_id: str) -> str:
    """Generate a Slack mention string for a user group.

    Args:
        usergroup_id: The user group ID to mention.

    Returns:
        str: The Slack user group mention format <!subteam^ID>.
    """
    return f"<!subteam^{usergroup_id}>"


def mention_here() -> str:
    """Generate a Slack @here mention.

    Returns:
        str: The @here mention.
    """
    return "<!here>"


def mention_channel_all() -> str:
    """Generate a Slack @channel mention.

    Returns:
        str: The @channel mention.
    """
    return "<!channel>"


def mention_everyone() -> str:
    """Generate a Slack @everyone mention.

    Returns:
        str: The @everyone mention.
    """
    return "<!everyone>"
