"""Zulip backend, models, mentions, and testing helpers."""

from ..base import Channel, Message, Presence, User, register_backend_type
from .backend import ZULIP_CAPABILITIES, ZulipBackend
from .channel import ZulipChannel
from .config import ZulipConfig
from .mention import mention_channel, mention_user
from .message import ZulipMessage
from .presence import ZulipPresence, ZulipPresenceStatus
from .testing import MockZulipBackend
from .user import ZulipUser

register_backend_type("zulip", User, ZulipUser)
register_backend_type("zulip", Channel, ZulipChannel)
register_backend_type("zulip", Message, ZulipMessage)
register_backend_type("zulip", Presence, ZulipPresence)

__all__ = (
    "ZULIP_CAPABILITIES",
    "MockZulipBackend",
    "ZulipBackend",
    "ZulipChannel",
    "ZulipConfig",
    "ZulipMessage",
    "ZulipPresence",
    "ZulipPresenceStatus",
    "ZulipUser",
    "mention_channel",
    "mention_user",
)
