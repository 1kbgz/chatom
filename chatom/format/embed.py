"""Embed formatting for chatom.

This module provides the FormattedEmbed class — a content node that wraps
the base Embed model and can be placed inside a FormattedMessage content tree.
It renders a text fallback for all formats and exposes per-backend structured
payloads via to_discord_dict(), to_slack_attachment(), and to_symphony_messageml().
"""

from typing import Any, Dict, List

from pydantic import Field

from chatom.base import BaseModel
from chatom.base.embed import Embed

from .variant import FORMAT, Format

__all__ = ("FormattedEmbed",)


class FormattedEmbed(BaseModel):
    """A renderable embed content node for FormattedMessage.

    Wraps the base ``Embed`` model so that embeds can appear alongside
    Text, Table, and FormattedImage nodes in a message's content list.

    ``render()`` produces a reasonable text fallback (bold title, field list)
    for backends that don't support native embeds.  For backends that do,
    callers should use the structured-payload methods instead:

    * ``to_discord_dict()``  — Discord embed object
    * ``to_slack_attachment()`` — Slack Block Kit attachment
    * ``to_symphony_messageml()`` — Symphony ``<card>`` MessageML

    Attributes:
        embed: The underlying Embed data model.
    """

    embed: Embed = Field(default_factory=Embed, description="The underlying embed data.")

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_embed(cls, embed: Embed) -> "FormattedEmbed":
        """Create a FormattedEmbed from an existing Embed instance."""
        return cls(embed=embed)

    # ------------------------------------------------------------------
    # Text fallback rendering (for content list)
    # ------------------------------------------------------------------
    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render the embed as a text fallback.

        This is used when the embed appears in the content list and needs
        to be converted to a flat string.  Backends that support native
        embeds should use the structured-payload methods instead.
        """
        fmt = Format(format) if isinstance(format, str) else format
        parts: List[str] = []

        if self.embed.author:
            parts.append(self._render_author(fmt))

        if self.embed.title:
            parts.append(self._render_title(fmt))

        if self.embed.description:
            parts.append(self.embed.description)

        if self.embed.fields:
            parts.append(self._render_fields(fmt))

        if self.embed.image:
            parts.append(self._render_image(fmt))

        if self.embed.footer:
            parts.append(self._render_footer(fmt))

        return "\n".join(parts)

    def _render_title(self, fmt: Format) -> str:
        title = self.embed.title
        if self.embed.url:
            if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
                title = f"[{title}]({self.embed.url})"
            elif fmt == Format.SLACK_MARKDOWN:
                title = f"<{self.embed.url}|{title}>"
            elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
                title = f'<a href="{self.embed.url}">{title}</a>'

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"**{title}**"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"*{title}*"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<b>{title}</b>"
        return title

    def _render_author(self, fmt: Format) -> str:
        author = self.embed.author
        if not author:
            return ""
        name = author.name
        if author.url:
            if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
                name = f"[{name}]({author.url})"
            elif fmt == Format.SLACK_MARKDOWN:
                name = f"<{author.url}|{name}>"
            elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
                name = f'<a href="{author.url}">{name}</a>'
        return name

    def _render_fields(self, fmt: Format) -> str:
        lines: List[str] = []
        for field in self.embed.fields:
            if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
                lines.append(f"**{field.name}**: {field.value}")
            elif fmt == Format.SLACK_MARKDOWN:
                lines.append(f"*{field.name}*: {field.value}")
            elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
                lines.append(f"<b>{field.name}</b>: {field.value}")
            else:
                lines.append(f"{field.name}: {field.value}")
        return "\n".join(lines)

    def _render_image(self, fmt: Format) -> str:
        image = self.embed.image
        if not image:
            return ""
        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"![image]({image.url})"
        elif fmt == Format.SLACK_MARKDOWN:
            return image.url
        elif fmt == Format.HTML:
            return f'<img src="{image.url}"/>'
        elif fmt == Format.SYMPHONY_MESSAGEML:
            return f'<img src="{image.url}"/>'
        return image.url

    def _render_footer(self, fmt: Format) -> str:
        footer = self.embed.footer
        if not footer:
            return ""
        if fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f"<i>{footer.text}</i>"
        elif fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"*{footer.text}*"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"_{footer.text}_"
        return footer.text

    # ------------------------------------------------------------------
    # Structured per-backend payloads
    # ------------------------------------------------------------------
    def to_discord_dict(self) -> Dict[str, Any]:
        """Convert to a Discord embed dict suitable for the API."""
        e = self.embed
        data: Dict[str, Any] = {}
        if e.title:
            data["title"] = e.title
        if e.description:
            data["description"] = e.description
        if e.url:
            data["url"] = e.url
        if e.color is not None:
            data["color"] = e.color
        if e.timestamp:
            data["timestamp"] = e.timestamp.isoformat()
        if e.author:
            author: Dict[str, str] = {}
            if e.author.name:
                author["name"] = e.author.name
            if e.author.url:
                author["url"] = e.author.url
            if e.author.icon_url:
                author["icon_url"] = e.author.icon_url
            data["author"] = author
        if e.footer:
            footer: Dict[str, str] = {}
            if e.footer.text:
                footer["text"] = e.footer.text
            if e.footer.icon_url:
                footer["icon_url"] = e.footer.icon_url
            data["footer"] = footer
        if e.thumbnail:
            data["thumbnail"] = {"url": e.thumbnail.url}
        if e.image:
            data["image"] = {"url": e.image.url}
        if e.fields:
            data["fields"] = [{"name": f.name, "value": f.value, "inline": f.inline} for f in e.fields]
        return data

    def to_slack_attachment(self) -> Dict[str, Any]:
        """Convert to a Slack Block Kit attachment dict."""
        e = self.embed
        attachment: Dict[str, Any] = {}
        if e.color is not None:
            attachment["color"] = f"#{e.color:06x}"
        blocks: List[Dict[str, Any]] = []

        # Title as a section header
        if e.title:
            title_text = e.title
            if e.url:
                title_text = f"<{e.url}|{e.title}>"
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{title_text}*"},
                }
            )

        # Description
        if e.description:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": e.description},
                }
            )

        # Fields — group into sections (max 10 fields per section in Slack)
        if e.fields:
            fields_list = [{"type": "mrkdwn", "text": f"*{f.name}*\n{f.value}"} for f in e.fields]
            blocks.append(
                {
                    "type": "section",
                    "fields": fields_list,
                }
            )

        # Image
        if e.image and e.image.url:
            blocks.append(
                {
                    "type": "image",
                    "image_url": e.image.url,
                    "alt_text": "image",
                }
            )

        # Footer as context block
        if e.footer:
            elements: List[Dict[str, Any]] = []
            if e.footer.icon_url:
                elements.append({"type": "image", "image_url": e.footer.icon_url, "alt_text": "footer icon"})
            if e.footer.text:
                elements.append({"type": "mrkdwn", "text": e.footer.text})
            if elements:
                blocks.append({"type": "context", "elements": elements})

        # Author as context block at the top
        if e.author:
            author_elements: List[Dict[str, Any]] = []
            if e.author.icon_url:
                author_elements.append({"type": "image", "image_url": e.author.icon_url, "alt_text": "author icon"})
            name = e.author.name
            if e.author.url:
                name = f"<{e.author.url}|{e.author.name}>"
            author_elements.append({"type": "mrkdwn", "text": name})
            blocks.insert(0, {"type": "context", "elements": author_elements})

        attachment["blocks"] = blocks
        return attachment

    def to_symphony_messageml(self) -> str:
        """Convert to Symphony MessageML ``<card>`` markup."""
        e = self.embed
        parts: List[str] = []

        # Header
        header_parts: List[str] = []
        if e.title:
            header_parts.append(e.title)
        if e.author and e.author.name:
            header_parts.append(f" — {e.author.name}")
        header = "".join(header_parts) or "Embed"

        parts.append(f'<card accent="tempo-bg-color--blue"><header>{header}</header><body>')

        if e.description:
            parts.append(f"<p>{e.description}</p>")

        if e.fields:
            parts.append("<table><thead><tr><td>Field</td><td>Value</td></tr></thead><tbody>")
            for f in e.fields:
                parts.append(f"<tr><td>{f.name}</td><td>{f.value}</td></tr>")
            parts.append("</tbody></table>")

        if e.image and e.image.url:
            parts.append(f'<img src="{e.image.url}"/>')

        if e.footer and e.footer.text:
            parts.append(f"<p><i>{e.footer.text}</i></p>")

        parts.append("</body></card>")
        return "".join(parts)

    def to_telegram_html(self) -> str:
        """Convert to Telegram-compatible HTML."""
        return self.render(Format.HTML)
