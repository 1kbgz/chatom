"""Matrix backend for chatom."""

from .backend import MATRIX_CAPABILITIES, MatrixBackend
from .channel import MatrixChannel
from .config import MatrixConfig
from .mention import mention_channel, mention_user
from .message import MatrixMessage
from .presence import MatrixPresence, MatrixPresenceState
from .testing import MockMatrixBackend
from .user import MatrixUser

__all__ = (
    "MATRIX_CAPABILITIES",
    "MatrixBackend",
    "MatrixChannel",
    "MatrixConfig",
    "MatrixMessage",
    "MatrixPresence",
    "MatrixPresenceState",
    "MatrixUser",
    "MockMatrixBackend",
    "mention_channel",
    "mention_user",
)
