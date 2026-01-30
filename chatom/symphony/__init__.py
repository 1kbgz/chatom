"""Symphony backend for chatom.

This module provides Symphony-specific models and utilities.
"""

from .backend import SymphonyBackend
from .channel import SymphonyChannel, SymphonyRoom, SymphonyStreamType
from .config import SymphonyConfig, SymphonyRoomMapper
from .mention import (
    format_cashtag,
    format_hashtag,
    mention_user,
    mention_user_by_email,
    mention_user_by_uid,
)
from .message import SymphonyMessage, SymphonyMessageFormat
from .presence import SymphonyPresence, SymphonyPresenceStatus
from .testing import MockSymphonyBackend
from .user import SymphonyUser

__all__ = (
    "SymphonyBackend",
    "SymphonyConfig",
    "SymphonyRoomMapper",
    "SymphonyUser",
    "SymphonyChannel",
    "SymphonyRoom",
    "SymphonyStreamType",
    "SymphonyMessage",
    "SymphonyMessageFormat",
    "SymphonyPresence",
    "SymphonyPresenceStatus",
    "MockSymphonyBackend",
    "mention_user",
    "mention_user_by_email",
    "mention_user_by_uid",
    "format_hashtag",
    "format_cashtag",
)
