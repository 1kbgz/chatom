"""Discord backend for chatom.

This module provides Discord-specific models and utilities.
"""

from .backend import DiscordBackend
from .channel import DiscordChannel, DiscordChannelType
from .config import DiscordConfig
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
    "DiscordBackend",
    "DiscordConfig",
    "DiscordUser",
    "DiscordChannel",
    "DiscordChannelType",
    "DiscordMessage",
    "DiscordMessageType",
    "DiscordMessageFlags",
    "DiscordPresence",
    "DiscordActivity",
    "DiscordActivityType",
    "MockDiscordBackend",
    "mention_user",
    "mention_channel",
    "mention_role",
    "mention_everyone",
    "mention_here",
)
