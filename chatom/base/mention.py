"""Mention utilities for chatom.

This module provides a single-dispatch based system for generating
platform-specific mention strings from User objects.
"""

import re
from functools import singledispatch
from typing import TYPE_CHECKING, List, NamedTuple

from .channel import Channel
from .user import User

if TYPE_CHECKING:
    from ..enums import BACKEND

__all__ = (
    "mention_user",
    "mention_channel",
    "mention_user_for_backend",
    "mention_channel_for_backend",
    "parse_mentions",
    "MentionMatch",
)


@singledispatch
def mention_user(user: User) -> str:
    """Generate a mention string for a user.

    This is a single-dispatch function that can be overridden
    for platform-specific user types.

    Args:
        user: The user to mention.

    Returns:
        str: The formatted mention string.

    Example:
        >>> from chatom import User, mention_user
        >>> user = User(name="John", id="123")
        >>> mention_user(user)
        'John'
    """
    # Default to using the user's display name
    return user.display_name


@singledispatch
def mention_channel(channel: Channel) -> str:
    """Generate a mention string for a channel.

    This is a single-dispatch function that can be overridden
    for platform-specific channel types.

    Args:
        channel: The channel to mention.

    Returns:
        str: The formatted channel mention string.

    Example:
        >>> from chatom import Channel, mention_channel
        >>> channel = Channel(name="general", id="456")
        >>> mention_channel(channel)
        '#general'
    """
    if channel.name:
        return f"#{channel.name}"
    return f"#{channel.id}"


def mention_user_for_backend(user: User, backend: "BACKEND") -> str:
    """Generate a mention string for a user based on the backend platform.

    This is a convenience function that dispatches to the appropriate
    backend-specific mention format based on the backend parameter.

    Args:
        user: The user to mention.
        backend: The backend platform identifier.

    Returns:
        str: The formatted mention string for that backend.

    Example:
        >>> from chatom import User, mention_user_for_backend
        >>> user = User(id="123", name="John", email="john@example.com")
        >>> mention_user_for_backend(user, "slack")
        '<@123>'
        >>> mention_user_for_backend(user, "discord")
        '<@123>'
        >>> mention_user_for_backend(user, "symphony")
        '<mention uid="123"/>'
    """
    backend_lower = backend.lower() if isinstance(backend, str) else backend

    if backend_lower == "discord":
        if user.id:
            return f"<@{user.id}>"
        return user.display_name

    elif backend_lower == "slack":
        if user.id:
            return f"<@{user.id}>"
        return user.display_name

    elif backend_lower == "symphony":
        if user.id:
            return f'<mention uid="{user.id}"/>'
        elif user.email:
            return f'<mention email="{user.email}"/>'
        return f"@{user.display_name}"

    elif backend_lower == "matrix":
        if hasattr(user, "user_id") and user.user_id:
            return user.user_id
        if user.handle:
            homeserver = getattr(user, "homeserver", "matrix.org")
            return f"@{user.handle}:{homeserver}"
        return user.display_name

    elif backend_lower == "irc":
        return getattr(user, "nick", None) or user.handle or user.name

    elif backend_lower == "email":
        if user.email:
            name = getattr(user, "full_name", None) or user.name or user.email
            return f"<a href='mailto:{user.email}'>{name}</a>"
        return getattr(user, "full_name", None) or user.name

    else:
        # Fallback to display name
        return user.display_name


def mention_channel_for_backend(channel: Channel, backend: "BACKEND") -> str:
    """Generate a mention string for a channel based on the backend platform.

    Args:
        channel: The channel to mention.
        backend: The backend platform identifier.

    Returns:
        str: The formatted channel mention string for that backend.

    Example:
        >>> from chatom import Channel, mention_channel_for_backend
        >>> channel = Channel(id="C123", name="general")
        >>> mention_channel_for_backend(channel, "slack")
        '<#C123>'
    """
    backend_lower = backend.lower() if isinstance(backend, str) else backend

    if backend_lower in ("discord", "slack"):
        if channel.id:
            return f"<#{channel.id}>"
        return f"#{channel.name}"

    else:
        # Default format
        if channel.name:
            return f"#{channel.name}"
        return f"#{channel.id}"


class MentionMatch(NamedTuple):
    """Represents a mention found in message content.

    Attributes:
        user_id: The extracted user ID.
        start: Start position in the original string.
        end: End position in the original string.
        raw: The raw mention string as it appeared.
    """

    user_id: str
    start: int
    end: int
    raw: str


# Backend-specific mention patterns
_MENTION_PATTERNS = {
    # Discord: <@123456789> or <@!123456789> (nickname mention)
    "discord": re.compile(r"<@!?(\d+)>"),
    # Slack: <@U123ABC456>
    "slack": re.compile(r"<@([A-Z0-9]+)>"),
    # Symphony: <mention uid="123456789"/> or <mention email="user@example.com"/>
    "symphony": re.compile(r'<mention\s+(?:uid="([^"]+)"|email="([^"]+)")\s*/>'),
    # Matrix: @user:homeserver.org (exclude trailing punctuation)
    "matrix": re.compile(r"(@[^:]+:[^\s,!?]+)"),
    # IRC: No standard mention format, but some use nickname references
    "irc": re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_\[\]\\`^{}\-]*)[:,]"),
}


def parse_mentions(content: str, backend: str) -> List[MentionMatch]:
    """Parse user mentions from message content.

    Extracts user mentions from a message based on the backend's
    mention format. Returns a list of MentionMatch objects containing
    the user IDs and positions of mentions in the content.

    Args:
        content: The message content to parse.
        backend: The backend platform identifier.

    Returns:
        List[MentionMatch]: List of mention matches found.

    Example:
        >>> # Parse Slack mentions
        >>> mentions = parse_mentions("Hey <@U123>, check this!", "slack")
        >>> mentions[0].user_id
        'U123'

        >>> # Parse Discord mentions
        >>> mentions = parse_mentions("<@123456789> Hello!", "discord")
        >>> mentions[0].user_id
        '123456789'

        >>> # Parse Symphony mentions
        >>> mentions = parse_mentions('<mention uid="123"/>!', "symphony")
        >>> mentions[0].user_id
        '123'
    """
    backend_lower = backend.lower() if isinstance(backend, str) else backend.lower()

    pattern = _MENTION_PATTERNS.get(backend_lower)
    if pattern is None:
        # Unknown backend, return empty list
        return []

    matches: List[MentionMatch] = []

    for match in pattern.finditer(content):
        if backend_lower == "symphony":
            # Symphony has two capture groups (uid or email)
            user_id = match.group(1) or match.group(2)
        else:
            user_id = match.group(1)

        matches.append(
            MentionMatch(
                user_id=user_id,
                start=match.start(),
                end=match.end(),
                raw=match.group(0),
            )
        )

    return matches


def extract_mention_ids(content: str, backend: str) -> List[str]:
    """Extract just the user IDs from mentions in content.

    This is a convenience wrapper around parse_mentions that returns
    only the user IDs as strings.

    Args:
        content: The message content to parse.
        backend: The backend platform identifier.

    Returns:
        List[str]: List of user IDs mentioned in the content.

    Example:
        >>> ids = extract_mention_ids("Hey <@U123> and <@U456>!", "slack")
        >>> ids
        ['U123', 'U456']
    """
    return [m.user_id for m in parse_mentions(content, backend)]
