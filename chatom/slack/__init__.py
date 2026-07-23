"""Slack backend for chatom.

This module provides Slack-specific models and utilities.
"""

from .backend import SlackBackend
from .channel import SlackChannel
from .config import SlackConfig
from .mention import (
    mention_channel,
    mention_channel_all,
    mention_everyone,
    mention_here,
    mention_user,
    mention_user_group,
)
from .message import SlackMessage, SlackMessageSubtype
from .presence import SlackPresence, SlackPresenceStatus
from .testing import MockSlackBackend
from .user import SlackUser

__all__ = (
    "MockSlackBackend",
    "SlackBackend",
    "SlackChannel",
    "SlackConfig",
    "SlackMessage",
    "SlackMessageSubtype",
    "SlackPresence",
    "SlackPresenceStatus",
    "SlackUser",
    "mention_channel",
    "mention_channel_all",
    "mention_everyone",
    "mention_here",
    "mention_user",
    "mention_user_group",
)
