"""Focused tests for the IRC backend."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from chatom import Channel, User
from chatom.base import ChannelType, PresenceStatus, get_backend_type
from chatom.irc import (
    IRCBackend,
    IRCChannel,
    IRCConfig,
    IRCMessage,
    IRCUser,
    MockIRCBackend,
    mention_channel,
    mention_user,
)
from chatom.irc.backend import _parse_line


def test_irc_config_and_models() -> None:
    config = IRCConfig(server="irc.example.org", password="secret", channels=["#chatom"])
    user = IRCUser.from_prefix("alice!user@example.org")
    channel = IRCChannel(id="#chatom", name="#chatom")

    assert config.password_str == "secret"
    assert user.hostmask == "alice!user@example.org"
    assert channel.channel_type == ChannelType.PUBLIC
    assert IRCChannel(id="alice", name="alice").channel_type == ChannelType.DIRECT


def test_irc_mentions_and_conversion_registration() -> None:
    user = IRCUser(id="alice", nickname="alice")
    channel = IRCChannel(id="#chatom")

    assert mention_user(user) == "alice"
    assert mention_channel(channel) == "#chatom"
    assert get_backend_type(User, "irc") is IRCUser
    assert get_backend_type(Channel, "irc") is IRCChannel


def test_parse_ircv3_message() -> None:
    tags, prefix, command, params = _parse_line(
        "@time=2026-07-18T12:00:00.000Z;msgid=abc;label=hello\\sworld :alice!user@example.org PRIVMSG #chatom :hello there"
    )

    assert tags == {
        "time": "2026-07-18T12:00:00.000Z",
        "msgid": "abc",
        "label": "hello world",
    }
    assert prefix == "alice!user@example.org"
    assert command == "PRIVMSG"
    assert params == ["#chatom", "hello there"]


@pytest.mark.asyncio
async def test_mock_lookup_send_and_history_are_newest_first() -> None:
    backend = MockIRCBackend(config=IRCConfig(nickname="bot"))
    backend.add_mock_user("alice")
    backend.add_mock_channel("#chatom")
    now = datetime.now(UTC)
    backend.add_mock_message("#chatom", "alice", "older", message_id="1", timestamp=now - timedelta(minutes=1))
    backend.add_mock_message("#chatom", "alice", "newer", message_id="2", timestamp=now)

    await backend.connect()
    sent = await backend.send_message("#chatom", "hello")
    history = await backend.fetch_messages("#chatom", limit=2)

    user = await backend.fetch_user("alice")
    channel = await backend.fetch_channel("#chatom")
    assert user is not None
    assert channel is not None
    assert sent.author is not None
    assert user.nickname == "alice"
    assert channel.id == "#chatom"
    assert sent.author.id == "bot"
    assert backend.sent_messages == [sent]
    assert [message.content for message in history] == ["hello", "newer"]


@pytest.mark.asyncio
async def test_mock_history_bounds() -> None:
    backend = MockIRCBackend()
    now = datetime.now(UTC)
    older = backend.add_mock_message("#chatom", "alice", "older", timestamp=now - timedelta(minutes=2))
    middle = backend.add_mock_message("#chatom", "alice", "middle", timestamp=now - timedelta(minutes=1))
    backend.add_mock_message("#chatom", "alice", "newer", timestamp=now)

    history = await backend.fetch_messages("#chatom", after=older, before=middle)

    assert [message.content for message in history] == ["middle", "older"]


@pytest.mark.asyncio
async def test_mock_listener_filters_channels() -> None:
    backend = MockIRCBackend()
    await backend.connect()
    listener = backend.listen_for_messages(channels={"#wanted"})

    await backend.emit_message("#other", "alice", "skip")
    wanted = await backend.emit_message("#wanted", "alice", "keep")

    assert await asyncio.wait_for(anext(listener), timeout=1) == wanted
    await backend.disconnect()


@pytest.mark.asyncio
async def test_public_listen_filters_channel_and_own_messages() -> None:
    backend = MockIRCBackend(config=IRCConfig(nickname="bot"))
    await backend.connect()
    listener = backend.listen(channel="#wanted")
    next_message = asyncio.ensure_future(anext(listener))
    await asyncio.sleep(0)

    await backend.emit_message("#wanted", "bot", "skip own")
    await backend.emit_message("#other", "alice", "skip channel")
    wanted = await backend.emit_message("#wanted", "alice", "keep")

    assert await asyncio.wait_for(next_message, timeout=1) == wanted
    await backend.disconnect()


@pytest.mark.asyncio
async def test_mock_presence() -> None:
    backend = MockIRCBackend()
    backend.set_mock_presence("alice", PresenceStatus.IDLE)

    presence = await backend.get_presence("alice")

    assert presence is not None
    assert presence.status == PresenceStatus.IDLE


@pytest.mark.asyncio
async def test_protocol_handler_records_tagged_messages() -> None:
    backend = IRCBackend(config=IRCConfig(nickname="bot"))

    await backend._handle_line("@time=2026-07-18T12:00:00Z;msgid=abc :alice!user@example.org PRIVMSG #chatom :hello")
    history = await backend.fetch_messages("#chatom")

    assert len(history) == 1
    message = history[0]
    assert isinstance(message, IRCMessage)
    assert message.id == "abc"
    assert message.created_at == datetime(2026, 7, 18, 12, tzinfo=UTC)
    assert isinstance(message.author, IRCUser)
    assert message.author.hostname == "example.org"


@pytest.mark.asyncio
async def test_send_requires_connection() -> None:
    backend = MockIRCBackend()

    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.send_message("#chatom", "hello")


@pytest.mark.asyncio
async def test_live_backend_requires_server() -> None:
    backend = IRCBackend()

    with pytest.raises(ValueError, match="server is required"):
        await backend.connect()
