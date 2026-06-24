"""Tests for Telegram HTML compatibility."""

import pytest

from chatom.format import Format, FormattedMessage, Heading, Table, Text
from chatom.format.telegram import sanitize_telegram_html
from chatom.telegram.backend import TelegramBackend
from chatom.telegram.message import TelegramMessage


def test_sanitize_telegram_html_converts_heading_and_table() -> None:
    content = (
        "<h3>Bot Commands Help</h3>"
        "<table><thead><tr><th>Command</th><th>Name</th></tr></thead>"
        "<tbody><tr><td>/help</td><td>Help</td></tr></tbody></table>"
    )

    result = sanitize_telegram_html(content)

    assert result.startswith("<b>Bot Commands Help</b>")
    assert "<h3>" not in result
    assert "<table>" not in result
    assert "Command" in result
    assert "Name" in result
    assert "/help" in result
    assert "Help" in result


def test_sanitize_telegram_html_preserves_supported_tags() -> None:
    content = '<b>Bold</b> <i>italic</i> <a href="https://example.com?a=1&b=2">link</a>'

    result = sanitize_telegram_html(content)

    assert result == '<b>Bold</b> <i>italic</i> <a href="https://example.com?a=1&amp;b=2">link</a>'


def test_sanitize_telegram_html_keeps_plain_text_from_unknown_tags() -> None:
    result = sanitize_telegram_html("<unknown>keep &amp; escape</unknown>")

    assert result == "keep &amp; escape"


def test_formatted_message_renders_telegram_html_without_unsupported_tags() -> None:
    msg = FormattedMessage(
        content=[
            Heading(level=3, child=Text(content="Stats")),
            Table.from_data([["NYM", "50 < 60"]], headers=["Team", "Record"]),
        ]
    )

    result = msg.render_for("telegram")

    assert result.startswith("<b>Stats</b>")
    assert "<h3>" not in result
    assert "<table>" not in result
    assert "<pre>" in result
    assert "50 &lt; 60" in result
    assert result == msg.render(Format.TELEGRAM_HTML)


@pytest.mark.asyncio
async def test_send_message_sanitizes_html_before_telegram_api(monkeypatch) -> None:
    class FakeBot:
        kwargs = None

        async def send_message(self, **kwargs):
            self.kwargs = kwargs
            return object()

    fake_bot = FakeBot()
    backend = TelegramBackend()
    backend.connected = True
    backend._bot = fake_bot

    monkeypatch.setattr(
        TelegramMessage,
        "from_telegram_message",
        classmethod(lambda cls, msg: TelegramMessage(id="1", content=fake_bot.kwargs["text"])),
    )

    await backend.send_message("123", "<h3>Title</h3><table><tr><td>Cell</td></tr></table>")

    assert fake_bot.kwargs["parse_mode"] == "HTML"
    assert fake_bot.kwargs["text"] == "<b>Title</b>\nCell"
