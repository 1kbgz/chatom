"""Email backend for chatom.

This module provides Email-specific models and utilities.
"""

from .backend import EmailBackend
from .channel import EmailChannel
from .config import EmailConfig
from .mention import mention_user
from .message import EmailMessage, EmailPriority
from .presence import EmailPresence
from .testing import MockEmailBackend
from .user import EmailUser

__all__ = (
    "EmailBackend",
    "EmailConfig",
    "EmailUser",
    "EmailChannel",
    "EmailMessage",
    "EmailPriority",
    "EmailPresence",
    "MockEmailBackend",
    "mention_user",
)
