"""IRC-specific mention utilities.

This module registers IRC-specific mention formatting.
"""

from chatom.base import mention_user

from .user import IRCUser

__all__ = ("mention_user",)


@mention_user.register
def _mention_irc_user(user: IRCUser) -> str:
    """Generate an IRC mention string for a user.

    IRC doesn't have formal mentions, but conventionally
    typing a nick will highlight that user.

    Args:
        user: The IRC user to mention.

    Returns:
        str: The user's nickname.
    """
    return user.nick or user.handle or user.name


def highlight_user(nick: str, message: str) -> str:
    """Create a message that highlights a user.

    Args:
        nick: The nickname to highlight.
        message: The message to send.

    Returns:
        str: Message prefixed with nick.
    """
    return f"{nick}: {message}"
