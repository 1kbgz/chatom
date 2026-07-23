"""Formatting utilities for chatom.

This module provides utilities for formatting messages and content
that can be rendered to different output formats like Markdown,
HTML, Slack mrkdwn, Discord Markdown, and Symphony MessageML.
"""

from .attachment import FormattedAttachment, FormattedImage
from .components import (
    ActionRow,
    Button,
    ButtonStyle,
    ComponentContainer,
    Modal,
    SelectMenu,
    SelectOption,
    TextInput,
    TextInputStyle,
    attach_components_for_backend,
)
from .embed import FormattedEmbed
from .message import (
    BACKEND_FORMAT_MAP,
    FormattedMessage,
    MessageBuilder,
    format_message,
    get_format_for_backend,
    render_message,
)
from .parse import convert_format, parse_markdown
from .table import Table, TableAlignment, TableCell, TableRow
from .text import (
    Bold,
    ChannelMention,
    Code,
    CodeBlock,
    Document,
    Emoji,
    Heading,
    HorizontalRule,
    Italic,
    LineBreak,
    Link,
    ListItem,
    OrderedList,
    Paragraph,
    Quote,
    Span,
    Strikethrough,
    Text,
    TextNode,
    Underline,
    UnorderedList,
    UserMention,
    bold,
    code,
    code_block,
    italic,
    link,
    text,
)
from .variant import (
    DISCORD_MARKDOWN,
    FORMAT,
    HTML,
    MARKDOWN,
    PLAINTEXT,
    SLACK_MARKDOWN,
    SYMPHONY_MESSAGEML,
    TELEGRAM_HTML,
    Format,
)

__all__ = (
    "BACKEND_FORMAT_MAP",
    "DISCORD_MARKDOWN",
    "FORMAT",
    "HTML",
    "MARKDOWN",
    "PLAINTEXT",
    "SLACK_MARKDOWN",
    "SYMPHONY_MESSAGEML",
    "TELEGRAM_HTML",
    "ActionRow",
    "Bold",
    # Interactive Components
    "Button",
    "ButtonStyle",
    "ChannelMention",
    "Code",
    "CodeBlock",
    "ComponentContainer",
    "Document",
    "Emoji",
    # Variant/Format
    "Format",
    # Attachment
    "FormattedAttachment",
    # Embed
    "FormattedEmbed",
    "FormattedImage",
    # Message
    "FormattedMessage",
    "Heading",
    "HorizontalRule",
    "Italic",
    "LineBreak",
    "Link",
    "ListItem",
    "MessageBuilder",
    "Modal",
    "OrderedList",
    "Paragraph",
    "Quote",
    "SelectMenu",
    "SelectOption",
    "Span",
    "Strikethrough",
    # Table
    "Table",
    "TableAlignment",
    "TableCell",
    "TableRow",
    "Text",
    "TextInput",
    "TextInputStyle",
    # Text nodes
    "TextNode",
    "Underline",
    "UnorderedList",
    "UserMention",
    "attach_components_for_backend",
    "bold",
    "code",
    "code_block",
    "convert_format",
    "format_message",
    "get_format_for_backend",
    "italic",
    "link",
    # Parse / convert
    "parse_markdown",
    "render_message",
    # Helper functions
    "text",
)
