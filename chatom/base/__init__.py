"""Base models for chatom.

This module exports all base model classes that form the foundation
of the chatom framework. These models are platform-agnostic and can
be extended for specific chat backends.
"""

from .attachment import Attachment, AttachmentType, File, Image
from .authorization import (
    AuthorizationPolicy,
    AuthorizationResult,
    Permission,
    SimpleAuthorizationPolicy,
    is_user_authorized,
)
from .base import BaseModel, Field, Identifiable
from .capabilities import (
    DISCORD_CAPABILITIES,
    SLACK_CAPABILITIES,
    SYMPHONY_CAPABILITIES,
    BackendCapabilities,
    Capability,
)
from .channel import Channel, ChannelType
from .connection import (
    ChannelRegistry,
    Connection,
    LookupError,
    UserRegistry,
)
from .conversion import (
    BackendNotFoundError,
    ConversionError,
    ValidationResult,
    can_promote,
    demote,
    get_backend_type,
    get_base_type,
    list_backends_for_type,
    promote,
    register_backend_type,
    validate_for_backend,
)
from .embed import Embed, EmbedAuthor, EmbedField, EmbedFooter, EmbedMedia
from .mention import (
    MentionMatch,
    mention_channel,
    mention_channel_for_backend,
    mention_user,
    mention_user_for_backend,
    parse_mentions,
)
from .message import Message, MessageReference, MessageType
from .organization import Organization
from .presence import Activity, ActivityType, Presence, PresenceStatus
from .reaction import Emoji, Reaction, ReactionEvent, ReactionEventType

# Testing utilities (available but not part of public API)
from .testing import MockBackendMixin, MockDataStore
from .thread import Thread
from .user import User

# Rebuild ReactionEvent to resolve forward reference to Message
ReactionEvent.model_rebuild()

__all__ = (
    # Base
    "BaseModel",
    "Field",
    "Identifiable",
    # User
    "User",
    # Channel
    "Channel",
    "ChannelType",
    # Thread
    "Thread",
    # Organization
    "Organization",
    # Message
    "Message",
    "MessageReference",
    "MessageType",
    # Attachment
    "Attachment",
    "AttachmentType",
    "File",
    "Image",
    # Embed
    "Embed",
    "EmbedAuthor",
    "EmbedField",
    "EmbedFooter",
    "EmbedMedia",
    # Reaction
    "Emoji",
    "Reaction",
    "ReactionEvent",
    "ReactionEventType",
    # Presence
    "Activity",
    "ActivityType",
    "Presence",
    "PresenceStatus",
    # Capabilities
    "BackendCapabilities",
    "Capability",
    "DISCORD_CAPABILITIES",
    "SLACK_CAPABILITIES",
    "SYMPHONY_CAPABILITIES",
    # Conversion utilities
    "BackendNotFoundError",
    "ConversionError",
    "ValidationResult",
    "can_promote",
    "demote",
    "get_backend_type",
    "get_base_type",
    "list_backends_for_type",
    "promote",
    "register_backend_type",
    "validate_for_backend",
    # Mention utilities
    "mention_channel",
    "mention_user",
    "mention_channel_for_backend",
    "mention_user_for_backend",
    "parse_mentions",
    "MentionMatch",
    # Authorization
    "AuthorizationPolicy",
    "AuthorizationResult",
    "Permission",
    "SimpleAuthorizationPolicy",
    "is_user_authorized",
    # Connection and registries
    "Connection",
    "UserRegistry",
    "ChannelRegistry",
    "LookupError",
)
