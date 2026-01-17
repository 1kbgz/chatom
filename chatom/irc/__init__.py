"""IRC backend for chatom.

This module provides IRC-specific models and utilities.
"""

from .backend import IRCBackend
from .channel import IRCChannel
from .config import IRCConfig
from .mention import highlight_user, mention_user
from .message import IRCMessage, IRCMessageType
from .presence import IRCPresence
from .testing import MockIRCBackend
from .user import IRCUser

__all__ = (
    "IRCBackend",
    "IRCConfig",
    "IRCUser",
    "IRCChannel",
    "IRCMessage",
    "IRCMessageType",
    "IRCPresence",
    "MockIRCBackend",
    "mention_user",
    "highlight_user",
)
