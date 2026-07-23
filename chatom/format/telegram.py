"""Telegram-specific format helpers."""

from html import escape
from html.parser import HTMLParser

__all__ = ("sanitize_telegram_html",)

_TELEGRAM_SAFE_TAGS = {
    "a",
    "b",
    "blockquote",
    "code",
    "del",
    "em",
    "i",
    "ins",
    "pre",
    "s",
    "span",
    "strike",
    "strong",
    "tg-emoji",
    "u",
}
_TELEGRAM_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_TELEGRAM_LINE_TAGS = {
    "article",
    "caption",
    "div",
    "footer",
    "form",
    "header",
    "li",
    "ol",
    "p",
    "section",
    "table",
    "tbody",
    "thead",
    "tr",
    "ul",
}
_TELEGRAM_SPACE_TAGS = {"td", "th"}
_TELEGRAM_VOID_LINE_TAGS = {"br", "hr"}


class _TelegramHTMLSanitizer(HTMLParser):
    """Convert broad HTML into Telegram Bot API's narrow HTML subset."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._open_tags: list[str | None] = []

    def render(self) -> str:
        return "".join(self._parts).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        rendered = self._render_start_tag(tag, attrs)
        if rendered is not None:
            self._parts.append(rendered)
        self._open_tags.append(self._closing_tag(tag, rendered))

    def handle_endtag(self, tag: str) -> None:
        closing = self._open_tags.pop() if self._open_tags else None
        if closing:
            self._parts.append(f"</{closing}>")
        if tag.lower() in _TELEGRAM_HEADING_TAGS | _TELEGRAM_LINE_TAGS:
            self._append_line()
        elif tag.lower() in _TELEGRAM_SPACE_TAGS:
            self._append_space()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _TELEGRAM_VOID_LINE_TAGS:
            self._append_line()
            return
        rendered = self._render_start_tag(tag, attrs)
        if rendered is not None:
            closing = self._closing_tag(tag, rendered)
            self._parts.append(rendered)
            if closing:
                self._parts.append(f"</{closing}>")

    def handle_data(self, data: str) -> None:
        self._parts.append(escape(data, quote=False))

    def _render_start_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> str | None:
        if tag in _TELEGRAM_HEADING_TAGS:
            self._append_line()
            return "<b>"
        if tag == "a":
            href = self._attr(attrs, "href")
            return f'<a href="{escape(href, quote=True)}">' if href else None
        if tag == "span" and self._attr(attrs, "class") == "tg-spoiler":
            return '<span class="tg-spoiler">'
        if tag == "tg-emoji":
            emoji_id = self._attr(attrs, "emoji-id")
            return f'<tg-emoji emoji-id="{escape(emoji_id, quote=True)}">' if emoji_id else None
        if tag == "code":
            class_attr = self._attr(attrs, "class")
            if class_attr and class_attr.startswith("language-"):
                return f'<code class="{escape(class_attr, quote=True)}">'
            return "<code>"
        if tag in _TELEGRAM_SAFE_TAGS and tag not in {"span", "tg-emoji"}:
            return f"<{tag}>"
        if tag in _TELEGRAM_LINE_TAGS | _TELEGRAM_VOID_LINE_TAGS:
            self._append_line()
        elif tag in _TELEGRAM_SPACE_TAGS:
            self._append_space()
        return None

    def _closing_tag(self, tag: str, rendered: str | None) -> str | None:
        if rendered is None:
            return None
        if tag in _TELEGRAM_HEADING_TAGS:
            return "b"
        return tag

    def _append_line(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")

    def _append_space(self) -> None:
        if self._parts and not self._parts[-1].endswith((" ", "\n")):
            self._parts.append(" ")

    @staticmethod
    def _attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
        for attr_name, value in attrs:
            if attr_name.lower() == name:
                return value
        return None


def sanitize_telegram_html(content: str) -> str:
    """Return HTML accepted by Telegram's Bot API parse_mode=HTML."""
    sanitizer = _TelegramHTMLSanitizer()
    sanitizer.feed(content)
    sanitizer.close()
    return sanitizer.render()
