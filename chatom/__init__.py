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

from .backend import BackendConfig
from .backend_registry import (
    BackendBase,
    BackendRegistry,
    get_backend,
    get_backend_format,
    list_backends,
    register_backend,
)
from .base import (
    DISCORD_CAPABILITIES,
    EMAIL_CAPABILITIES,
    IRC_CAPABILITIES,
    MATRIX_CAPABILITIES,
    SLACK_CAPABILITIES,
    SYMPHONY_CAPABILITIES,
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
    LookupError,
    # Message
    Message,
    MessageReference,
    MessageType,
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
from .enums import (
    ALL_BACKENDS,
    BACKEND,
    DISCORD,
    EMAIL,
    IRC,
    MATRIX,
    SLACK,
    SYMPHONY,
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

__version__ = "0.1.0"

__all__ = (
    # Version
    "__version__",
    # Backend
    "BackendConfig",
    # Backend registry
    "BackendBase",
    "BackendRegistry",
    "get_backend",
    "get_backend_format",
    "list_backends",
    "register_backend",
    # Enums
    "BACKEND",
    "DISCORD",
    "EMAIL",
    "IRC",
    "MATRIX",
    "SLACK",
    "SYMPHONY",
    "ALL_BACKENDS",
    # Base classes
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
    # Presence
    "Activity",
    "ActivityType",
    "Presence",
    "PresenceStatus",
    # Capabilities
    "BackendCapabilities",
    "Capability",
    "DISCORD_CAPABILITIES",
    "EMAIL_CAPABILITIES",
    "IRC_CAPABILITIES",
    "MATRIX_CAPABILITIES",
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
    # Connection and registries
    "Connection",
    "UserRegistry",
    "ChannelRegistry",
    "LookupError",
    # Format
    "Format",
    "FORMAT",
    "PLAINTEXT",
    "MARKDOWN",
    "SLACK_MARKDOWN",
    "DISCORD_MARKDOWN",
    "HTML",
    "SYMPHONY_MESSAGEML",
    # Text nodes
    "TextNode",
    "Text",
    "Bold",
    "Italic",
    "Strikethrough",
    "Underline",
    "Code",
    "CodeBlock",
    "Link",
    "Quote",
    "Paragraph",
    "LineBreak",
    "HorizontalRule",
    "ListItem",
    "UnorderedList",
    "OrderedList",
    "Heading",
    "UserMention",
    "ChannelMention",
    "Span",
    "Document",
    # Helper functions
    "text",
    "bold",
    "italic",
    "code",
    "code_block",
    "link",
    # Table
    "Table",
    "TableRow",
    "TableCell",
    "TableAlignment",
    # Attachment formatting
    "FormattedAttachment",
    "FormattedImage",
    # Message formatting
    "FormattedMessage",
    "MessageBuilder",
    "render_message",
    "format_message",
    "BACKEND_FORMAT_MAP",
    "get_format_for_backend",
)
