"""Tests for Discord thread handling in DiscordBackend."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from chatom.base import Channel, Message
from chatom.discord import DiscordBackend, DiscordConfig


def _sent(channel_id):
    return SimpleNamespace(
        id=999,
        content="sent",
        created_at=datetime.now(UTC),
        author=SimpleNamespace(id=1),
        channel=SimpleNamespace(id=channel_id),
        guild=SimpleNamespace(id=456),
    )


def _channel(channel_id, root_content="Deploy finished\nDetails follow"):
    thread = SimpleNamespace(id=500, type=SimpleNamespace(value=11), guild=SimpleNamespace(id=456), name="t", send=AsyncMock(return_value=_sent(500)))
    root = SimpleNamespace(content=root_content, create_thread=AsyncMock(return_value=thread))
    return SimpleNamespace(
        id=channel_id,
        send=AsyncMock(return_value=_sent(channel_id)),
        fetch_message=AsyncMock(return_value=root),
        root=root,
        thread=thread,
    )


def _backend(channels):
    async def fetch_channel(channel_id):
        if channel_id not in channels:
            raise discord.NotFound(MagicMock(status=404, reason="Not Found"), {"code": 10003, "message": "Unknown Channel"})
        return channels[channel_id]

    backend = DiscordBackend(config=DiscordConfig(token="token"))
    backend._client = MagicMock(fetch_channel=AsyncMock(side_effect=fetch_channel))
    return backend


@pytest.mark.asyncio
async def test_send_message_starts_thread_from_message():
    parent = _channel(100)
    backend = _backend({100: parent})

    msg = await backend.send_message("100", "hi", thread="500")

    parent.fetch_message.assert_awaited_once_with(500)
    parent.root.create_thread.assert_awaited_once_with(name="Deploy finished")
    parent.thread.send.assert_awaited_once()
    parent.send.assert_not_awaited()
    assert msg.channel.id == "500"


@pytest.mark.asyncio
async def test_send_message_uses_existing_thread():
    parent = _channel(100)
    backend = _backend({100: parent, 500: parent.thread})

    await backend.send_message("100", "hi", thread="500")

    parent.root.create_thread.assert_not_awaited()
    parent.thread.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_quote_reply_in_new_thread_drops_reference_to_root():
    parent = _channel(100)
    backend = _backend({100: parent})
    root = Message(id="500", content="Deploy finished", channel=None)
    draft = root.as_quote_reply("ack")

    await backend.send_message("100", draft.content, thread=draft.thread, reply_to=draft.reply_to)

    assert "reference" not in parent.thread.send.await_args.kwargs


@pytest.mark.asyncio
async def test_reply_in_thread_starts_thread():
    parent = _channel(100)
    backend = _backend({100: parent})
    root = Message(id="500", content="Deploy finished", channel=Channel(id="100"))

    await backend.reply_in_thread(root, "ack")

    parent.root.create_thread.assert_awaited_once()
    parent.thread.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_thread():
    parent = _channel(100)
    backend = _backend({100: parent})

    thread = await backend.create_thread("100", "500", "Discussion", auto_archive_duration=60)

    parent.root.create_thread.assert_awaited_once_with(name="Discussion", auto_archive_duration=60)
    assert thread.id == "500"


@pytest.mark.asyncio
async def test_read_thread_reads_thread_channel(monkeypatch):
    backend = _backend({})
    messages = [Message(id="2"), Message(id="1")]
    fetch_messages = AsyncMock(return_value=messages)
    monkeypatch.setattr(DiscordBackend, "fetch_messages", fetch_messages)

    result = [m async for m in backend.read_thread("100", "500", limit=10)]

    fetch_messages.assert_awaited_once_with("500", limit=10)
    assert result == messages
