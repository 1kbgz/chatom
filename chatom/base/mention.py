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
    "parse_channel_mentions",
    "extract_mention_ids",
    "extract_channel_ids",
    "MentionMatch",
    "ChannelMentionMatch",
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


class ChannelMentionMatch(NamedTuple):
    """Result of parsing a channel mention from content.

    Attributes:
        channel_id: The extracted channel ID.
        start: Start position in the original string.
        end: End position in the original string.
        raw: The raw mention string as it appeared.
    """

    channel_id: str
    start: int
    end: int
    raw: str


# Backend-specific channel mention patterns
_CHANNEL_MENTION_PATTERNS = {
    # Discord: <#123456789>
    "discord": re.compile(r"<#(\d+)>"),
    # Slack: <#C123ABC456> or <#C123ABC456|channel-name>
    "slack": re.compile(r"<#([A-Z0-9]+)(?:\|[^>]*)?>"),
}


def parse_channel_mentions(content: str, backend: str) -> List[ChannelMentionMatch]:
    """Parse channel mentions from message content.

    Extracts channel mentions from a message based on the backend's
    mention format. Returns a list of ChannelMentionMatch objects containing
    the channel IDs and positions of mentions in the content.

    Args:
        content: The message content to parse.
        backend: The backend platform identifier.

    Returns:
        List[ChannelMentionMatch]: List of channel mention matches found.

    Example:
        >>> # Parse Slack channel mentions
        >>> mentions = parse_channel_mentions("Join <#C123>!", "slack")
        >>> mentions[0].channel_id
        'C123'

        >>> # Parse Discord channel mentions
        >>> mentions = parse_channel_mentions("Check <#987654321>", "discord")
        >>> mentions[0].channel_id
        '987654321'
    """
    backend_lower = backend.lower() if isinstance(backend, str) else backend.lower()

    pattern = _CHANNEL_MENTION_PATTERNS.get(backend_lower)
    if pattern is None:
        # Unknown backend, return empty list
        return []

    matches: List[ChannelMentionMatch] = []

    for match in pattern.finditer(content):
        channel_id = match.group(1)
        matches.append(
            ChannelMentionMatch(
                channel_id=channel_id,
                start=match.start(),
                end=match.end(),
                raw=match.group(0),
            )
        )

    return matches


def extract_channel_ids(content: str, backend: str) -> List[str]:
    """Extract just the channel IDs from mentions in content.

    This is a convenience wrapper around parse_channel_mentions that returns
    only the channel IDs as strings.

    Args:
        content: The message content to parse.
        backend: The backend platform identifier.

    Returns:
        List[str]: List of channel IDs mentioned in the content.

    Example:
        >>> ids = extract_channel_ids("Join <#C123> and <#C456>!", "slack")
        >>> ids
        ['C123', 'C456']
    """
    return [m.channel_id for m in parse_channel_mentions(content, backend)]
