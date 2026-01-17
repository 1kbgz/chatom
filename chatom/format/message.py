"""Message formatting and conversion utilities.

This module provides utilities for building and converting messages
between different chat platform formats.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from chatom.base import BaseModel

from .attachment import FormattedAttachment, FormattedImage
from .table import Table
from .text import (
    Bold,
    Code,
    CodeBlock,
    Heading,
    Italic,
    LineBreak,
    Link,
    ListItem,
    OrderedList,
    Paragraph,
    Quote,
    Raw,
    Strikethrough,
    Text,
    TextNode,
    UnorderedList,
    UserMention,
)
from .variant import FORMAT, Format

__all__ = (
    "FormattedMessage",
    "MessageBuilder",
    "render_message",
    "format_message",
    "BACKEND_FORMAT_MAP",
    "get_format_for_backend",
)


# Mapping of backends to their preferred format
# This is kept for backwards compatibility; the BackendRegistry
# now provides the authoritative source via entry points.
BACKEND_FORMAT_MAP = {
    "discord": Format.DISCORD_MARKDOWN,
    "slack": Format.SLACK_MARKDOWN,
    "symphony": Format.SYMPHONY_MESSAGEML,
    "matrix": Format.HTML,
    "irc": Format.PLAINTEXT,
    "email": Format.HTML,
}


def get_format_for_backend(backend: str) -> Format:
    """Get the preferred format for a backend.

    This function first checks the BackendRegistry for registered
    backends, then falls back to the BACKEND_FORMAT_MAP for
    backwards compatibility.

    Args:
        backend: The backend identifier.

    Returns:
        The preferred format for that backend.
    """
    # Try the registry first (which includes entry points)
    try:
        from chatom.backend_registry import BackendRegistry

        return BackendRegistry.get_format(backend)
    except (ImportError, KeyError):
        pass

    # Fall back to the static map
    return BACKEND_FORMAT_MAP.get(backend.lower(), Format.MARKDOWN)


class FormattedMessage(BaseModel):
    """A message with formatted content that can be rendered to different formats.

    This is the main class for building rich messages that can be converted
    to platform-specific formats.

    Attributes:
        content: List of content nodes (text, tables, images, etc.).
        attachments: File attachments.
        metadata: Additional platform-specific metadata.
    """

    content: List[Union[TextNode, Table, FormattedImage, FormattedAttachment]] = Field(
        default_factory=list,
        description="Content nodes.",
    )
    attachments: List[FormattedAttachment] = Field(
        default_factory=list,
        description="File attachments.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific metadata.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render the message to the specified format.

        Args:
            format: The output format.

        Returns:
            str: The rendered message.
        """
        parts = []

        for item in self.content:
            if hasattr(item, "render"):
                parts.append(item.render(format))
            else:
                parts.append(str(item))

        return "".join(parts)

    def render_for(self, backend: str) -> str:
        """Render the message for a specific backend.

        Uses the backend's preferred format automatically.

        Args:
            backend: The backend identifier (e.g., 'slack', 'discord').

        Returns:
            str: The rendered message in the backend's format.

        Example:
            >>> msg = FormattedMessage().add_bold("Hello")
            >>> msg.render_for("slack")
            '*Hello*'
            >>> msg.render_for("discord")
            '**Hello**'
        """
        format = get_format_for_backend(backend)
        return self.render(format)

    def append(self, item: Union[TextNode, Table, FormattedImage, FormattedAttachment, str]) -> "FormattedMessage":
        """Append content to the message.

        Args:
            item: The content to append.

        Returns:
            Self for method chaining.
        """
        if isinstance(item, str):
            item = Text(content=item)
        self.content.append(item)
        return self

    def add_text(self, text: str) -> "FormattedMessage":
        """Add plain text."""
        return self.append(Text(content=text))

    def add_bold(self, text: str) -> "FormattedMessage":
        """Add bold text."""
        return self.append(Bold(child=Text(content=text)))

    def add_italic(self, text: str) -> "FormattedMessage":
        """Add italic text."""
        return self.append(Italic(child=Text(content=text)))

    def add_code(self, code: str) -> "FormattedMessage":
        """Add inline code."""
        return self.append(Code(content=code))

    def add_code_block(self, code: str, language: str = "") -> "FormattedMessage":
        """Add a code block."""
        return self.append(CodeBlock(content=code, language=language))

    def add_link(self, text: str, url: str) -> "FormattedMessage":
        """Add a hyperlink."""
        return self.append(Link(text=text, url=url))

    def add_line_break(self) -> "FormattedMessage":
        """Add a line break."""
        return self.append(LineBreak())

    def add_table(self, table: Table) -> "FormattedMessage":
        """Add a table."""
        return self.append(table)

    def add_image(self, url: str, alt_text: str = "", title: str = "") -> "FormattedMessage":
        """Add an image."""
        return self.append(FormattedImage(url=url, alt_text=alt_text, title=title))

    def add_mention(self, user_id: str, display_name: str = "") -> "FormattedMessage":
        """Add a user mention.

        Args:
            user_id: Platform-specific user ID.
            display_name: Fallback display name (used for plain text rendering).

        Returns:
            Self for method chaining.
        """
        return self.append(UserMention(user_id=user_id, display_name=display_name))

    def add_raw(self, content: str) -> "FormattedMessage":
        """Add raw content that will not be escaped.

        Use this for platform-specific markup that should be inserted as-is,
        such as Symphony hashtags (<hash tag="..."/>), cashtags (<cash tag="..."/>),
        or mentions (<mention uid="..."/>).

        Args:
            content: The raw content to insert (will not be escaped).

        Returns:
            Self for method chaining.

        Example:
            >>> msg = FormattedMessage()
            >>> msg.add_text("Check out ").add_raw('<hash tag="chatom"/>').add_text("!")
        """
        return self.append(Raw(content=content))


class MessageBuilder:
    """Builder for constructing formatted messages fluently.

    Example:
        >>> msg = (
        ...     MessageBuilder()
        ...     .text("Hello, ")
        ...     .bold("world")
        ...     .text("!")
        ...     .build()
        ... )
        >>> msg.render(Format.MARKDOWN)
        'Hello, **world**!'
    """

    def __init__(self):
        self._content: List[Union[TextNode, Table, FormattedImage, FormattedAttachment]] = []
        self._attachments: List[FormattedAttachment] = []
        self._metadata: Dict[str, Any] = {}

    def text(self, content: str) -> "MessageBuilder":
        """Add plain text."""
        self._content.append(Text(content=content))
        return self

    def bold(self, content: str) -> "MessageBuilder":
        """Add bold text."""
        self._content.append(Bold(child=Text(content=content)))
        return self

    def italic(self, content: str) -> "MessageBuilder":
        """Add italic text."""
        self._content.append(Italic(child=Text(content=content)))
        return self

    def strikethrough(self, content: str) -> "MessageBuilder":
        """Add strikethrough text."""
        self._content.append(Strikethrough(child=Text(content=content)))
        return self

    def code(self, content: str) -> "MessageBuilder":
        """Add inline code."""
        self._content.append(Code(content=content))
        return self

    def code_block(self, content: str, language: str = "") -> "MessageBuilder":
        """Add a code block."""
        self._content.append(CodeBlock(content=content, language=language))
        return self

    def link(self, text: str, url: str, title: str = "") -> "MessageBuilder":
        """Add a link."""
        self._content.append(Link(text=text, url=url, title=title))
        return self

    def quote(self, content: str) -> "MessageBuilder":
        """Add a block quote."""
        self._content.append(Quote(child=Text(content=content)))
        return self

    def heading(self, content: str, level: int = 1) -> "MessageBuilder":
        """Add a heading."""
        self._content.append(Heading(child=Text(content=content), level=level))
        return self

    def line_break(self) -> "MessageBuilder":
        """Add a line break."""
        self._content.append(LineBreak())
        return self

    def paragraph(self, content: str) -> "MessageBuilder":
        """Add a paragraph."""
        self._content.append(Paragraph(children=[Text(content=content)]))
        return self

    def bullet_list(self, items: List[str]) -> "MessageBuilder":
        """Add a bullet list."""
        list_items = [ListItem(child=Text(content=item)) for item in items]
        self._content.append(UnorderedList(items=list_items))
        return self

    def numbered_list(self, items: List[str], start: int = 1) -> "MessageBuilder":
        """Add a numbered list."""
        list_items = [ListItem(child=Text(content=item)) for item in items]
        self._content.append(OrderedList(items=list_items, start=start))
        return self

    def table(
        self,
        data: List[List[Any]],
        headers: Optional[List[str]] = None,
        caption: str = "",
    ) -> "MessageBuilder":
        """Add a table from data."""
        self._content.append(Table.from_data(data, headers=headers, caption=caption))
        return self

    def table_from_dicts(
        self,
        data: List[dict],
        columns: Optional[List[str]] = None,
        caption: str = "",
    ) -> "MessageBuilder":
        """Add a table from a list of dictionaries."""
        self._content.append(Table.from_dict_list(data, columns=columns, caption=caption))
        return self

    def image(self, url: str, alt_text: str = "", title: str = "") -> "MessageBuilder":
        """Add an image."""
        self._content.append(FormattedImage(url=url, alt_text=alt_text, title=title))
        return self

    def attachment(self, filename: str, url: str, content_type: str = "") -> "MessageBuilder":
        """Add an attachment."""
        att = FormattedAttachment(filename=filename, url=url, content_type=content_type)
        self._attachments.append(att)
        return self

    def node(self, node: TextNode) -> "MessageBuilder":
        """Add a custom text node."""
        self._content.append(node)
        return self

    def metadata(self, key: str, value: Any) -> "MessageBuilder":
        """Add metadata."""
        self._metadata[key] = value
        return self

    def build(self) -> FormattedMessage:
        """Build the formatted message.

        Returns:
            FormattedMessage: The constructed message.
        """
        return FormattedMessage(
            content=self._content.copy(),
            attachments=self._attachments.copy(),
            metadata=self._metadata.copy(),
        )


def render_message(message: FormattedMessage, format: FORMAT = Format.MARKDOWN) -> str:
    """Render a formatted message to a specific format.

    Args:
        message: The message to render.
        format: The output format.

    Returns:
        str: The rendered message content.
    """
    return message.render(format)


def format_message(
    content: str,
    format: FORMAT = Format.PLAINTEXT,
    *,
    escape_html: bool = True,
    escape_symphony: bool = True,
) -> str:
    """Format a plain text message for a specific platform.

    This is a simple utility for converting plain text to a format-safe string.
    For rich formatting, use MessageBuilder instead.

    Args:
        content: The plain text content.
        format: The target format.
        escape_html: Whether to escape HTML characters.
        escape_symphony: Whether to apply Symphony-specific escaping.

    Returns:
        str: The formatted message.
    """
    fmt = Format(format) if isinstance(format, str) else format

    if fmt == Format.PLAINTEXT:
        return content

    text = content

    if fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML) and escape_html:
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    if fmt == Format.SYMPHONY_MESSAGEML and escape_symphony:
        text = text.replace("${", "&#36;{").replace("#{", "&#35;{")

    return text
