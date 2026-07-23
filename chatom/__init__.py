"""Chatom - Framework-agnostic chat application representations.

Chatom provides a unified interface for working with chat platforms.
It includes representations for users, channels, threads, messages,
reactions, presence, and more.

Example:
    >>> from chatom import User, Channel, Message, mention_user
    >>> user = User(id="123", name="John Doe", handle="johndoe")
    >>> channel = Channel(id="456", name="general")
    >>> msg = Message(content="Hello, world!", author=user, channel=channel)
    >>> print(mention_user(user))
    John Doe

For platform-specific functionality, import from the backend modules:
    >>> from chatom.discord import DiscordUser, mention_user
    >>> from chatom.slack import SlackUser
    >>> from chatom.symphony import SymphonyUser
"""

from .backend import (
    Backend,
    BackendBase,
    BackendConfig,
    BackendRegistry,
    get_backend,
    get_backend_format,
    list_backends,
    register_backend,
)
from .base import (
    DISCORD_CAPABILITIES,
    SLACK_CAPABILITIES,
    SYMPHONY_CAPABILITIES,
    TELEGRAM_CAPABILITIES,
    # Presence
    Activity,
    ActivityType,
    # Attachment
    Attachment,
    AttachmentType,
    # Capabilities
    BackendCapabilities,
    # Conversion utilities
    BackendNotFoundError,
    # Base classes
    BaseModel,
    Capability,
    # Channel
    Channel,
    ChannelRegistry,
    ChannelType,
    # Connection and registries
    Connection,
    ConversionError,
    # Embed
    Embed,
    EmbedAuthor,
    EmbedField,
    EmbedFooter,
    EmbedMedia,
    # Reaction
    Emoji,
    Field,
    File,
    Identifiable,
    Image,
    # Interaction
    Interaction,
    InteractionType,
    LookupError,
    # Message
    Message,
    MessageReference,
    MessageType,
    # Organization
    Organization,
    Presence,
    PresenceStatus,
    Reaction,
    # Thread
    Thread,
    # User
    User,
    UserRegistry,
    ValidationResult,
    can_promote,
    demote,
    get_backend_type,
    get_base_type,
    list_backends_for_type,
    # Mention utilities
    mention_channel,
    mention_channel_for_backend,
    mention_user,
    mention_user_for_backend,
    promote,
    register_backend_type,
    validate_for_backend,
)
from .bridge import IdentityMapper, MessageBridge
from .enums import (
    ALL_BACKENDS,
    BACKEND,
    DISCORD,
    SLACK,
    SYMPHONY,
    TELEGRAM,
)
from .format import (
    BACKEND_FORMAT_MAP,
    DISCORD_MARKDOWN,
    FORMAT,
    HTML,
    MARKDOWN,
    PLAINTEXT,
    SLACK_MARKDOWN,
    SYMPHONY_MESSAGEML,
    TELEGRAM_HTML,
    Bold,
    ChannelMention,
    Code,
    CodeBlock,
    Document,
    # Variant/Format
    Format,
    # Attachment formatting
    FormattedAttachment,
    FormattedImage,
    # Message formatting
    FormattedMessage,
    Heading,
    HorizontalRule,
    Italic,
    LineBreak,
    Link,
    ListItem,
    MessageBuilder,
    OrderedList,
    Paragraph,
    Quote,
    Span,
    Strikethrough,
    # Table
    Table,
    TableAlignment,
    TableCell,
    TableRow,
    Text,
    # Text nodes
    TextNode,
    Underline,
    UnorderedList,
    UserMention,
    bold,
    code,
    code_block,
    format_message,
    get_format_for_backend,
    italic,
    link,
    render_message,
    # Helper functions
    text,
)
from .handlers import InteractionHandler, InteractionRegistry

__version__ = "0.2.0"

__all__ = (
    "ALL_BACKENDS",
    # Enums
    "BACKEND",
    "BACKEND_FORMAT_MAP",
    "DISCORD",
    "DISCORD_CAPABILITIES",
    "DISCORD_MARKDOWN",
    "FORMAT",
    "HTML",
    "MARKDOWN",
    "PLAINTEXT",
    "SLACK",
    "SLACK_CAPABILITIES",
    "SLACK_MARKDOWN",
    "SYMPHONY",
    "SYMPHONY_CAPABILITIES",
    "SYMPHONY_MESSAGEML",
    "TELEGRAM",
    "TELEGRAM_CAPABILITIES",
    "TELEGRAM_HTML",
    # Presence
    "Activity",
    "ActivityType",
    # Attachment
    "Attachment",
    "AttachmentType",
    # Backend
    "Backend",
    # Backend registry
    "BackendBase",
    # Capabilities
    "BackendCapabilities",
    "BackendConfig",
    # Conversion utilities
    "BackendNotFoundError",
    "BackendRegistry",
    # Base classes
    "BaseModel",
    "Bold",
    "Capability",
    # Channel
    "Channel",
    "ChannelMention",
    "ChannelRegistry",
    "ChannelType",
    "Code",
    "CodeBlock",
    # Connection and registries
    "Connection",
    "ConversionError",
    "Document",
    # Embed
    "Embed",
    "EmbedAuthor",
    "EmbedField",
    "EmbedFooter",
    "EmbedMedia",
    # Reaction
    "Emoji",
    "Field",
    "File",
    # Format
    "Format",
    # Attachment formatting
    "FormattedAttachment",
    "FormattedImage",
    # Message formatting
    "FormattedMessage",
    "Heading",
    "HorizontalRule",
    "Identifiable",
    # Bridge
    "IdentityMapper",
    "Image",
    # Interactions
    "Interaction",
    "InteractionHandler",
    "InteractionRegistry",
    "InteractionType",
    "Italic",
    "LineBreak",
    "Link",
    "ListItem",
    "LookupError",
    # Message
    "Message",
    "MessageBridge",
    "MessageBuilder",
    "MessageReference",
    "MessageType",
    "OrderedList",
    "Paragraph",
    "Presence",
    "PresenceStatus",
    "Quote",
    "Reaction",
    "Span",
    "Strikethrough",
    # Table
    "Table",
    "TableAlignment",
    "TableCell",
    "TableRow",
    "Text",
    # Text nodes
    "TextNode",
    # Thread
    "Thread",
    "Underline",
    "UnorderedList",
    # User
    "User",
    "UserMention",
    "UserRegistry",
    "ValidationResult",
    # Version
    "__version__",
    "bold",
    "can_promote",
    "code",
    "code_block",
    "demote",
    "format_message",
    "get_backend",
    "get_backend_format",
    "get_backend_type",
    "get_base_type",
    "get_format_for_backend",
    "italic",
    "link",
    "list_backends",
    "list_backends_for_type",
    # Mention utilities
    "mention_channel",
    "mention_channel_for_backend",
    "mention_user",
    "mention_user_for_backend",
    "promote",
    "register_backend",
    "register_backend_type",
    "render_message",
    # Helper functions
    "text",
    "validate_for_backend",
)
