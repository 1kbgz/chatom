"""Text formatting nodes for chatom.

This module provides a composable system for building formatted text
that can be rendered to different output formats (Markdown, HTML, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Union

from pydantic import Field

from chatom.base import BaseModel

from .variant import FORMAT, Format

__all__ = (
    "TextNode",
    "Text",
    "Raw",
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
    "Emoji",
    "Span",
    "Document",
)


class TextNode(BaseModel, ABC):
    """Base class for all text formatting nodes.

    TextNodes represent semantic text content that can be rendered
    to different output formats. They form a tree structure allowing
    complex nested formatting.
    """

    @abstractmethod
    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render this node to the specified format.

        Args:
            format: The output format to render to.

        Returns:
            str: The rendered string.
        """
        ...

    def __str__(self) -> str:
        """Return plaintext representation."""
        return self.render(Format.PLAINTEXT)

    def __add__(self, other: Union["TextNode", str]) -> "Span":
        """Concatenate nodes with + operator."""
        if isinstance(other, str):
            other = Text(content=other)
        return Span(children=[self, other])


class Text(TextNode):
    """Plain text content.

    Attributes:
        content: The text content.
    """

    content: str = Field(
        default="",
        description="The text content.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render plain text, escaping special characters as needed."""
        text = self.content

        if format in (Format.HTML, "html", Format.SYMPHONY_MESSAGEML, "symphony-messageml"):
            # Escape HTML special characters
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elif format in (Format.SYMPHONY_MESSAGEML, "symphony-messageml"):
            # Additional Symphony escapes
            text = text.replace("${", "&#36;{").replace("#{", "&#35;{")

        return text


class Raw(TextNode):
    """Raw content that is not escaped.

    Use this for inserting platform-specific markup that should not be
    escaped, such as Symphony hashtags, cashtags, or mentions.

    Attributes:
        content: The raw content (will be inserted as-is).
    """

    content: str = Field(
        default="",
        description="The raw content (not escaped).",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render raw content without any escaping."""
        return self.content


class Bold(TextNode):
    """Bold formatted text.

    Attributes:
        child: The content to make bold.
    """

    child: "TextNode" = Field(description="The content to make bold.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = self.child.render(format)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"**{content}**"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"*{content}*"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<b>{content}</b>"
        return content


class Italic(TextNode):
    """Italic formatted text.

    Attributes:
        child: The content to italicize.
    """

    child: "TextNode" = Field(description="The content to italicize.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = self.child.render(format)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"*{content}*"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"_{content}_"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<i>{content}</i>"
        return content


class Strikethrough(TextNode):
    """Strikethrough formatted text.

    Attributes:
        child: The content to strike through.
    """

    child: "TextNode" = Field(description="The content to strike through.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = self.child.render(format)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"~~{content}~~"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"~{content}~"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<s>{content}</s>"
        return content


class Underline(TextNode):
    """Underlined text.

    Note: Not all formats support underline.

    Attributes:
        child: The content to underline.
    """

    child: "TextNode" = Field(description="The content to underline.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = self.child.render(format)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt == Format.DISCORD_MARKDOWN:
            return f"__{content}__"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<u>{content}</u>"
        # Most formats don't support underline
        return content


class Code(TextNode):
    """Inline code.

    Attributes:
        content: The code content.
    """

    content: str = Field(description="The code content.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN, Format.SLACK_MARKDOWN):
            return f"`{self.content}`"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            escaped = self.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f"<code>{escaped}</code>"
        return self.content


class CodeBlock(TextNode):
    """Code block with optional language specification.

    Attributes:
        content: The code content.
        language: The programming language for syntax highlighting.
    """

    content: str = Field(description="The code content.")
    language: str = Field(default="", description="Programming language for syntax highlighting.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN, Format.SLACK_MARKDOWN):
            return f"```{self.language}\n{self.content}\n```"
        elif fmt == Format.SYMPHONY_MESSAGEML:
            # Symphony MessageML doesn't allow <code> inside <pre>
            escaped = self.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f"<pre>{escaped}</pre>"
        elif fmt == Format.HTML:
            escaped = self.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            lang_attr = f' class="language-{self.language}"' if self.language else ""
            return f"<pre><code{lang_attr}>{escaped}</code></pre>"
        return self.content


class Link(TextNode):
    """Hyperlink.

    Attributes:
        text: The link text.
        url: The URL to link to.
        title: Optional title attribute.
    """

    text: str = Field(description="The link text.")
    url: str = Field(description="The URL to link to.")
    title: str = Field(default="", description="Optional title attribute.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            if self.title:
                return f'[{self.text}]({self.url} "{self.title}")'
            return f"[{self.text}]({self.url})"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"<{self.url}|{self.text}>"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            title_attr = f' title="{self.title}"' if self.title else ""
            return f'<a href="{self.url}"{title_attr}>{self.text}</a>'
        elif fmt == Format.PLAINTEXT:
            return f"{self.text} ({self.url})"
        return self.text


class Quote(TextNode):
    """Block quote.

    Attributes:
        child: The quoted content.
    """

    child: "TextNode" = Field(description="The quoted content.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = self.child.render(format)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN, Format.SLACK_MARKDOWN):
            # Prefix each line with >
            lines = content.split("\n")
            return "\n".join(f"> {line}" for line in lines)
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<blockquote>{content}</blockquote>"
        return content


class Paragraph(TextNode):
    """Paragraph of text.

    Attributes:
        children: The content nodes within the paragraph.
    """

    children: List["TextNode"] = Field(
        default_factory=list,
        description="Content nodes within the paragraph.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = "".join(child.render(format) for child in self.children)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<p>{content}</p>"
        return content + "\n"


class LineBreak(TextNode):
    """Line break."""

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return "<br/>"
        return "\n"


class HorizontalRule(TextNode):
    """Horizontal rule/divider."""

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return "\n---\n"
        elif fmt == Format.SLACK_MARKDOWN:
            return "\n---\n"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return "<hr/>"
        return "\n" + "-" * 40 + "\n"


class ListItem(TextNode):
    """List item.

    Attributes:
        child: The item content.
    """

    child: "TextNode" = Field(description="The item content.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        return self.child.render(format)


class UnorderedList(TextNode):
    """Unordered (bulleted) list.

    Attributes:
        items: List items.
    """

    items: List[ListItem] = Field(
        default_factory=list,
        description="List items.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN, Format.SLACK_MARKDOWN):
            lines = [f"- {item.render(format)}" for item in self.items]
            return "\n".join(lines)
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            items_html = "".join(f"<li>{item.render(format)}</li>" for item in self.items)
            return f"<ul>{items_html}</ul>"
        else:
            lines = [f"• {item.render(format)}" for item in self.items]
            return "\n".join(lines)


class OrderedList(TextNode):
    """Ordered (numbered) list.

    Attributes:
        items: List items.
        start: Starting number.
    """

    items: List[ListItem] = Field(
        default_factory=list,
        description="List items.",
    )
    start: int = Field(default=1, description="Starting number.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN, Format.SLACK_MARKDOWN):
            lines = [f"{i + self.start}. {item.render(format)}" for i, item in enumerate(self.items)]
            return "\n".join(lines)
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            items_html = "".join(f"<li>{item.render(format)}</li>" for item in self.items)
            start_attr = f' start="{self.start}"' if self.start != 1 else ""
            return f"<ol{start_attr}>{items_html}</ol>"
        else:
            lines = [f"{i + self.start}. {item.render(format)}" for i, item in enumerate(self.items)]
            return "\n".join(lines)


class Heading(TextNode):
    """Heading.

    Attributes:
        child: The heading content.
        level: Heading level (1-6).
    """

    child: "TextNode" = Field(description="The heading content.")
    level: int = Field(default=1, ge=1, le=6, description="Heading level (1-6).")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        content = self.child.render(format)
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"{'#' * self.level} {content}\n"
        elif fmt == Format.SLACK_MARKDOWN:
            # Slack doesn't have headings, use bold
            return f"*{content}*\n"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<h{self.level}>{content}</h{self.level}>"
        return content.upper() + "\n"


class UserMention(TextNode):
    """User mention.

    Attributes:
        user_id: Platform-specific user ID.
        display_name: Fallback display name.
    """

    user_id: str = Field(description="Platform-specific user ID.")
    display_name: str = Field(default="", description="Fallback display name.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt == Format.DISCORD_MARKDOWN:
            return f"<@{self.user_id}>"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"<@{self.user_id}>"
        elif fmt == Format.SYMPHONY_MESSAGEML:
            return f'<mention uid="{self.user_id}"/>'
        elif fmt in (Format.HTML,):
            return f'<span class="mention" data-user-id="{self.user_id}">@{self.display_name or self.user_id}</span>'
        return f"@{self.display_name or self.user_id}"


class ChannelMention(TextNode):
    """Channel mention.

    Attributes:
        channel_id: Platform-specific channel ID.
        display_name: Fallback display name.
    """

    channel_id: str = Field(description="Platform-specific channel ID.")
    display_name: str = Field(default="", description="Fallback display name.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        if fmt == Format.DISCORD_MARKDOWN:
            return f"<#{self.channel_id}>"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"<#{self.channel_id}>"
        elif fmt in (Format.HTML,):
            return f'<span class="channel-mention" data-channel-id="{self.channel_id}">#{self.display_name or self.channel_id}</span>'
        return f"#{self.display_name or self.channel_id}"


class Emoji(TextNode):
    """Emoji.

    Attributes:
        name: Emoji name (without colons).
        unicode: Unicode representation if standard emoji.
        custom_id: Platform-specific ID for custom emoji.
    """

    name: str = Field(description="Emoji name (without colons).")
    unicode: str = Field(default="", description="Unicode representation.")
    custom_id: str = Field(default="", description="Platform-specific custom emoji ID.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format

        # If we have unicode, prefer that
        if self.unicode:
            return self.unicode

        if fmt == Format.DISCORD_MARKDOWN:
            if self.custom_id:
                return f"<:{self.name}:{self.custom_id}>"
            return f":{self.name}:"
        elif fmt == Format.SLACK_MARKDOWN:
            return f":{self.name}:"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            if self.unicode:
                return self.unicode
            return f'<span class="emoji" data-emoji="{self.name}">:{self.name}:</span>'
        return f":{self.name}:"


class Span(TextNode):
    """Container for multiple text nodes.

    Attributes:
        children: The child nodes.
    """

    children: List["TextNode"] = Field(
        default_factory=list,
        description="Child nodes.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        return "".join(child.render(format) for child in self.children)

    def __add__(self, other: Union["TextNode", str]) -> "Span":
        if isinstance(other, str):
            other = Text(content=other)
        return Span(children=[*self.children, other])


class Document(TextNode):
    """Top-level document containing multiple nodes.

    Attributes:
        children: The document content nodes.
    """

    children: List["TextNode"] = Field(
        default_factory=list,
        description="Document content nodes.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        fmt = Format(format) if isinstance(format, str) else format
        content = "".join(child.render(format) for child in self.children)

        if fmt in (Format.HTML,):
            return f"<div>{content}</div>"
        return content

    def append(self, node: "TextNode") -> "Document":
        """Append a node to the document.

        Args:
            node: The node to append.

        Returns:
            Self for method chaining.
        """
        self.children.append(node)
        return self


# Helper functions for building text nodes
def text(content: str) -> Text:
    """Create a Text node."""
    return Text(content=content)


def bold(content: Union[str, TextNode]) -> Bold:
    """Create a Bold node."""
    if isinstance(content, str):
        content = Text(content=content)
    return Bold(child=content)


def italic(content: Union[str, TextNode]) -> Italic:
    """Create an Italic node."""
    if isinstance(content, str):
        content = Text(content=content)
    return Italic(child=content)


def code(content: str) -> Code:
    """Create an inline Code node."""
    return Code(content=content)


def code_block(content: str, language: str = "") -> CodeBlock:
    """Create a CodeBlock node."""
    return CodeBlock(content=content, language=language)


def link(text: str, url: str, title: str = "") -> Link:
    """Create a Link node."""
    return Link(text=text, url=url, title=title)
