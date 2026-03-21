"""Telegram backend for chatom.

This module provides Telegram-specific models and utilities.
"""

from .backend import TelegramBackend
from .channel import TelegramChannel, TelegramChatType
from .config import TelegramConfig
from .mention import mention_channel, mention_user
from .message import TelegramMessage
from .presence import TelegramPresence
from .testing import MockTelegramBackend
from .user import TelegramUser

__all__ = (
    "TelegramBackend",
    "TelegramConfig",
    "TelegramUser",
    "TelegramChannel",
    "TelegramChatType",
    "TelegramMessage",
    "TelegramPresence",
    "MockTelegramBackend",
    "mention_user",
    "mention_channel",
)
