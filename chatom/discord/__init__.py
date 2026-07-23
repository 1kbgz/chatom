"""Discord backend for chatom.

This module provides Discord-specific models and utilities.
"""

from .backend import DiscordBackend
from .channel import DiscordChannel, DiscordChannelType
from .config import DiscordConfig
from .guild import DiscordGuild
from .mention import (
    mention_channel,
    mention_everyone,
    mention_here,
    mention_role,
    mention_user,
)
from .message import DiscordMessage, DiscordMessageFlags, DiscordMessageType
from .presence import DiscordActivity, DiscordActivityType, DiscordPresence
from .testing import MockDiscordBackend
from .user import DiscordUser

__all__ = (
    "DiscordActivity",
    "DiscordActivityType",
    "DiscordBackend",
    "DiscordChannel",
    "DiscordChannelType",
    "DiscordConfig",
    "DiscordGuild",
    "DiscordMessage",
    "DiscordMessageFlags",
    "DiscordMessageType",
    "DiscordPresence",
    "DiscordUser",
    "MockDiscordBackend",
    "mention_channel",
    "mention_everyone",
    "mention_here",
    "mention_role",
    "mention_user",
)
