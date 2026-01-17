"""Matrix backend for chatom.

This module provides Matrix-specific models and utilities based on the
Matrix Client-Server API and matrix-python-sdk patterns.
"""

from .backend import MatrixBackend
from .channel import (
    MatrixChannel,
    MatrixGuestAccess,
    MatrixJoinRule,
    MatrixRoom,
    MatrixRoomType,
    MatrixRoomVisibility,
)
from .config import MatrixConfig
from .mention import create_pill, mention_room, mention_user
from .message import (
    MatrixEventType,
    MatrixMessage,
    MatrixMessageFormat,
    MatrixMessageType,
    MatrixRelationType,
)
from .presence import MatrixPresence, MatrixPresenceStatus
from .testing import MockMatrixBackend
from .user import MatrixUser

__all__ = (
    # Backend
    "MatrixBackend",
    "MatrixConfig",
    "MockMatrixBackend",
    # User
    "MatrixUser",
    # Channel/Room
    "MatrixChannel",
    "MatrixRoom",
    "MatrixRoomType",
    "MatrixJoinRule",
    "MatrixGuestAccess",
    "MatrixRoomVisibility",
    # Message
    "MatrixMessage",
    "MatrixMessageType",
    "MatrixMessageFormat",
    "MatrixRelationType",
    "MatrixEventType",
    # Presence
    "MatrixPresence",
    "MatrixPresenceStatus",
    # Mention utilities
    "mention_user",
    "mention_room",
    "create_pill",
)
