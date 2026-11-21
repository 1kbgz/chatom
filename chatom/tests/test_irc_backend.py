"""Focused tests for the IRC backend."""

import asyncio
import ssl
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr

from chatom import Channel, User
from chatom.base import ChannelType, PresenceStatus, get_backend_type
from chatom.irc import (
    IRCBackend,
    IRCChannel,
    IRCConfig,
    IRCMessage,
    IRCUser,
    MockIRCBackend,
    backend as irc_backend_module,
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


@pytest.mark.asyncio
async def test_chathistory_batch_is_not_delivered_as_live_traffic() -> None:
    """Replayed CHATHISTORY messages belong to history only.

    Regression: batch members were queued for stream_messages(), so every
    fetch_messages() call made streaming consumers reprocess old messages.
    """
    backend = IRCBackend(config=IRCConfig(nickname="bot"))
    backend.connected = True

    await backend._handle_line("BATCH +hist chathistory #chatom")
    await backend._handle_line("@batch=hist;msgid=old-1 :alice!user@example.org PRIVMSG #chatom :replayed")
    await backend._handle_line("BATCH -hist")

    history = await backend.fetch_messages("#chatom")
    assert [message.id for message in history] == ["old-1"]
    assert backend._messages.empty()

    # Live traffic after the batch closes is still streamed.
    await backend._handle_line("@msgid=live-1 :alice!user@example.org PRIVMSG #chatom :live")
    assert backend._messages.qsize() == 1
    streamed = backend._messages.get_nowait()
    assert streamed is not None and streamed.id == "live-1"


@pytest.mark.asyncio
async def test_non_history_batch_is_still_delivered_live() -> None:
    """Only chathistory batches are suppressed; other batch types stream."""
    backend = IRCBackend(config=IRCConfig(nickname="bot"))
    backend.connected = True

    await backend._handle_line("BATCH +netjoin netjoin")
    await backend._handle_line("@batch=netjoin;msgid=live-2 :alice!user@example.org PRIVMSG #chatom :grouped")

    assert backend._messages.qsize() == 1


class FakeWriter:
    """Minimal StreamWriter stand-in that records protocol lines."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.closing = False
        self.drain_error: Exception | None = None
        self.close_error: Exception | None = None

    def write(self, data: bytes) -> None:
        self.lines.append(data.decode("utf-8").rstrip("\r\n"))

    async def drain(self) -> None:
        if self.drain_error is not None:
            raise self.drain_error

    def close(self) -> None:
        self.closing = True

    def is_closing(self) -> bool:
        return self.closing

    async def wait_closed(self) -> None:
        if self.close_error is not None:
            raise self.close_error


def attached_backend(**config: object) -> tuple[IRCBackend, FakeWriter]:
    backend = IRCBackend(config=IRCConfig(nickname="bot", **config))
    writer = FakeWriter()
    backend._writer = writer
    backend.connected = True
    return backend, writer


class FakeIRCServer:
    """Loopback IRC server that records client lines and sends scripted replies."""

    def __init__(self, on_line: Callable[[str], list[str]] | None = None) -> None:
        self.received: list[str] = []
        self.on_line = on_line
        self.writers: list[asyncio.StreamWriter] = []
        self.port = 0

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.writers.append(writer)
        while line := await reader.readline():
            text = line.decode("utf-8").rstrip("\r\n")
            self.received.append(text)
            if self.on_line is not None:
                for reply in self.on_line(text):
                    self.send(reply)
            await writer.drain()

    def send(self, line: str) -> None:
        self.writers[-1].write((line + "\r\n").encode("utf-8"))

    async def wait_for_line(self, expected: str) -> None:
        while expected not in self.received:
            await asyncio.sleep(0.005)


@asynccontextmanager
async def irc_server(on_line: Callable[[str], list[str]] | None = None) -> AsyncIterator[FakeIRCServer]:
    fake = FakeIRCServer(on_line)
    server = await asyncio.start_server(fake.handle, "127.0.0.1", 0)
    fake.port = server.sockets[0].getsockname()[1]
    try:
        yield fake
    finally:
        for writer in fake.writers:
            writer.close()
        server.close()
        await asyncio.wait_for(server.wait_closed(), timeout=2)


def welcome_on_user(line: str) -> list[str]:
    return [":srv 001 bot :Welcome"] if line.startswith("USER ") else []


def local_config(port: int, **config: object) -> IRCConfig:
    return IRCConfig(server="127.0.0.1", port=port, use_tls=False, nickname="bot", timeout=2.0, **config)


def test_parse_line_edge_cases() -> None:
    assert _parse_line("") == ({}, "", "", [])
    assert _parse_line("@flag;a=x\\:y\\\\z\\q;b=end\\ ping") == ({"flag": "", "a": "x;y\\zq", "b": "end\\"}, "", "PING", [])
    assert _parse_line(":srv ping :token with spaces") == ({}, "srv", "PING", ["token with spaces"])


def test_config_loads_password_from_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("hunter2\n")

    assert IRCConfig(password=str(secret_file)).password_str == "hunter2"
    assert IRCConfig(password=SecretStr("direct")).password_str == "direct"


def test_config_keeps_literal_password_when_path_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(self: Path) -> bool:
        raise OSError("unreadable")

    monkeypatch.setattr(Path, "is_file", fail)

    assert IRCConfig(password="literal").password_str == "literal"


def test_bot_user_id_is_nickname() -> None:
    assert IRCBackend(config=IRCConfig(nickname="bot")).bot_user_id == "bot"


@pytest.mark.asyncio
async def test_connect_negotiates_capabilities_and_joins_channels() -> None:
    def script(line: str) -> list[str]:
        if line == "CAP LS 302":
            return [":srv CAP * LS * :batch sasl=PLAIN", ":srv CAP * LS :draft/chathistory message-tags multi-prefix"]
        if line.startswith("CAP REQ :"):
            return [f":srv CAP bot ACK :{line[len('CAP REQ :') :]}"]
        if line == "CAP END":
            return [":srv 001 bot :Welcome"]
        return []

    async with irc_server(script) as server:
        backend = IRCBackend(config=local_config(server.port, password="hunter2", channels=["#a", "#b"]))
        await backend.connect()
        await server.wait_for_line("JOIN #b")

        assert backend.connected
        assert server.received[:4] == ["PASS hunter2", "CAP LS 302", "NICK bot", "USER chatom 0 * :chatom bot"]
        assert "CAP REQ :batch draft/chathistory message-tags" in server.received
        assert server.received.index("CAP END") < server.received.index("JOIN #a") < server.received.index("JOIN #b")
        assert backend._server_capabilities >= {"sasl", "multi-prefix", "batch"}
        assert backend._enabled_capabilities == {"batch", "draft/chathistory", "message-tags"}
        assert backend.supports_server_history

        await backend.disconnect()
        await server.wait_for_line("QUIT :chatom disconnect")
        assert not backend.connected
        assert backend._writer is None


@pytest.mark.asyncio
async def test_connect_without_requestable_capabilities_ends_negotiation() -> None:
    def script(line: str) -> list[str]:
        if line == "CAP LS 302":
            return [":srv CAP * LS :multi-prefix"]
        if line == "CAP END":
            return [":srv 001 bot :Welcome"]
        return []

    async with irc_server(script) as server:
        backend = IRCBackend(config=local_config(server.port))
        await backend.connect()

        assert "PASS" not in " ".join(server.received)
        assert not any(line.startswith("CAP REQ") for line in server.received)
        assert not backend.supports_server_history
        await backend.disconnect()


@pytest.mark.asyncio
async def test_connect_when_already_connected_is_noop() -> None:
    backend = IRCBackend(config=IRCConfig(server="127.0.0.1", port=1, use_tls=False))
    backend.connected = True

    await backend.connect()

    assert backend._writer is None


@pytest.mark.asyncio
async def test_connect_times_out_without_welcome() -> None:
    async with irc_server() as server:
        backend = IRCBackend(config=local_config(server.port))
        backend.config.timeout = 0.1

        with pytest.raises(TimeoutError):
            await backend.connect()
        await server.wait_for_line("QUIT :chatom disconnect")

        assert not backend.connected
        assert backend._writer is None
        assert backend._reader_task is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("use_tls", "tls_verify", "check_hostname", "verify_mode"),
    [
        (False, True, None, None),
        (True, True, True, ssl.CERT_REQUIRED),
        (True, False, False, ssl.CERT_NONE),
    ],
)
async def test_connect_builds_tls_context(
    monkeypatch: pytest.MonkeyPatch, use_tls: bool, tls_verify: bool, check_hostname: bool | None, verify_mode: ssl.VerifyMode | None
) -> None:
    captured: dict[str, object] = {}
    reader = asyncio.StreamReader()
    reader.feed_data(b":srv 001 bot :Welcome\r\n")
    writer = FakeWriter()

    async def fake_open_connection(host: str, port: int, *, ssl: object) -> tuple[asyncio.StreamReader, FakeWriter]:
        captured.update(host=host, port=port, ssl=ssl)
        return reader, writer

    monkeypatch.setattr(irc_backend_module.asyncio, "open_connection", fake_open_connection)
    backend = IRCBackend(config=IRCConfig(server="irc.example.org", port=6697, use_tls=use_tls, tls_verify=tls_verify, nickname="bot"))

    await backend.connect()
    await backend.disconnect()

    assert captured["host"] == "irc.example.org"
    assert captured["port"] == 6697
    context = captured["ssl"]
    if check_hostname is None:
        assert context is None
    else:
        assert isinstance(context, ssl.SSLContext)
        assert context.check_hostname is check_hostname
        assert context.verify_mode == verify_mode
    assert writer.lines[:3] == ["CAP LS 302", "NICK bot", "USER chatom 0 * :chatom bot"]


@pytest.mark.asyncio
async def test_server_ping_is_answered_and_messages_stream() -> None:
    async with irc_server(welcome_on_user) as server:
        backend = IRCBackend(config=local_config(server.port))
        await backend.connect()

        server.send("PING :keepalive")
        await server.wait_for_line("PONG :keepalive")
        server.send(":bot!u@h PRIVMSG #chatom :own")
        server.send(":alice!u@h PRIVMSG #other :elsewhere")
        server.send("@msgid=m1 :alice!u@h PRIVMSG #chatom :hello bot")
        streamed = await asyncio.wait_for(anext(backend.stream_messages(channel="#chatom")), timeout=2)

        assert streamed.id == "m1"
        assert streamed.content == "hello bot"
        await backend.disconnect()


@pytest.mark.asyncio
async def test_send_message_reaches_server() -> None:
    async with irc_server(welcome_on_user) as server:
        backend = IRCBackend(config=local_config(server.port))
        await backend.connect()

        sent = await backend.send_message("#chatom", "hello server")
        await server.wait_for_line("PRIVMSG #chatom :hello server")

        assert sent.content == "hello server"
        await backend.disconnect()


@pytest.mark.asyncio
async def test_server_closing_connection_ends_stream() -> None:
    async with irc_server(welcome_on_user) as server:
        backend = IRCBackend(config=local_config(server.port))
        await backend.connect()
        listener = backend.listen_for_messages()

        server.writers[-1].close()

        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(anext(listener), timeout=2)
        assert not backend.connected
        await backend.disconnect()


@pytest.mark.asyncio
async def test_welcome_joins_configured_channels() -> None:
    backend, writer = attached_backend(channels=["#a", "#b"])
    backend.connected = False
    backend._welcome = asyncio.Event()

    await backend._handle_line(":srv 001 bot :Welcome")

    assert backend.connected
    assert backend._welcome.is_set()
    assert writer.lines == ["JOIN #a", "JOIN #b"]


@pytest.mark.asyncio
async def test_welcome_without_pending_connect_marks_connected() -> None:
    backend, writer = attached_backend()
    backend.connected = False

    await backend._handle_line(":srv 001 bot :Welcome")

    assert backend.connected
    assert writer.lines == []


@pytest.mark.asyncio
async def test_ping_replies_with_pong() -> None:
    backend, writer = attached_backend()

    await backend._handle_line("PING :abc def")
    await backend._handle_line("PING")

    assert writer.lines == ["PONG :abc def", "PONG :"]


@pytest.mark.asyncio
async def test_send_command_validation() -> None:
    backend, writer = attached_backend()

    with pytest.raises(ValueError, match="CR or LF"):
        await backend._send_command("PRIVMSG", "#chatom", trailing="a\nQUIT")
    with pytest.raises(ValueError, match="CR or LF"):
        await backend._send_command("JOIN", "#a\r")
    with pytest.raises(ValueError, match="512 bytes"):
        await backend._send_command("PRIVMSG", "#chatom", trailing="x" * 600)
    assert writer.lines == []

    await backend._send_command("JOIN", "#chatom")
    assert writer.lines == ["JOIN #chatom"]

    backend._writer = None
    with pytest.raises(ConnectionError, match="not open"):
        await backend._send_command("JOIN", "#chatom")


@pytest.mark.asyncio
async def test_cap_subcommands() -> None:
    backend, writer = attached_backend()

    await backend._handle_line("CAP *")
    await backend._handle_line(":srv CAP * NEW :batch")
    assert writer.lines == []

    await backend._handle_line(":srv CAP * LS :multi-prefix sasl=PLAIN")
    assert writer.lines == ["CAP END"]
    assert backend._server_capabilities == {"multi-prefix", "sasl"}

    await backend._handle_line(":srv CAP * LS :server-time")
    assert writer.lines[-1] == "CAP REQ :server-time"

    await backend._handle_line(":srv CAP * NAK :server-time")
    assert writer.lines[-1] == "CAP END"
    assert not backend._enabled_capabilities

    await backend._handle_line(":srv CAP bot ACK :batch")
    assert backend._enabled_capabilities == {"batch"}
    assert not backend.supports_server_history

    await backend._handle_line(":srv CAP bot ACK :chathistory")
    assert backend.supports_server_history


@pytest.mark.asyncio
async def test_multiline_cap_ls_waits_for_final_line() -> None:
    backend, writer = attached_backend()

    await backend._handle_line(":srv CAP * LS * :batch")

    assert writer.lines == []
    assert backend._server_capabilities == {"batch"}


@pytest.mark.asyncio
async def test_batch_close_resolves_history_waiter() -> None:
    backend, _ = attached_backend()
    waiter = asyncio.get_running_loop().create_future()
    backend._history_waiters["#chatom"] = waiter

    await backend._handle_line("BATCH")
    await backend._handle_line("BATCH -unknown")
    assert not waiter.done()
    await backend._handle_line("BATCH +h chathistory #chatom")
    assert backend._history_batches == {"h": "#chatom"}
    await backend._handle_line("BATCH -h")

    assert waiter.done()
    assert backend._history_batches == {}
    assert backend._history_waiters == {}


@pytest.mark.asyncio
async def test_private_message_notice_and_bad_time_tag() -> None:
    backend, _ = attached_backend()
    before = datetime.now(UTC)

    await backend._handle_line("@time=garbage :alice!u@h PRIVMSG bot :psst")
    await backend._handle_line(":srv!u@h NOTICE #chatom :notice text")
    await backend._handle_line(":alice!u@h PRIVMSG #chatom")
    direct, notice = await backend._messages.get(), await backend._messages.get()

    assert backend._messages.empty()
    assert direct is not None and notice is not None
    assert direct.channel is not None and direct.channel.id == "alice"
    assert direct.channel.channel_type == ChannelType.DIRECT
    assert direct.created_at is not None and direct.created_at >= before
    assert direct.message_type.value == "default"
    assert notice.is_system
    assert notice.command == "NOTICE"
    assert notice.message_type.value == "system"
    presence = await backend.get_presence("alice")
    assert presence is not None and presence.status == PresenceStatus.ONLINE


@pytest.mark.asyncio
async def test_away_notifications_update_presence() -> None:
    backend, _ = attached_backend()

    await backend._handle_line(":alice!u@h AWAY :gone fishing")
    await backend._handle_line("AWAY :no prefix ignored")

    presence = await backend.get_presence("alice")
    assert presence is not None
    assert presence.status == PresenceStatus.IDLE
    assert presence.away_message == "gone fishing"
    assert await backend.get_presence("no") is None

    await backend._handle_line(":alice!u@h AWAY")
    returned = await backend.get_presence("alice")
    assert returned is not None and returned.away_message == ""


@pytest.mark.asyncio
async def test_duplicate_message_ids_are_stored_once() -> None:
    backend, _ = attached_backend()

    await backend._handle_line("@msgid=dup :alice!u@h PRIVMSG #chatom :first")
    await backend._handle_line("@msgid=dup :alice!u@h PRIVMSG #chatom :again")

    assert len(await backend.fetch_messages("#chatom")) == 1


@pytest.mark.asyncio
async def test_fetch_user() -> None:
    backend, _ = attached_backend()
    alice = IRCUser(id="alice", name="alice", nickname="alice")
    backend.users.add(alice)

    assert await backend.fetch_user(alice) is alice
    cached = await backend.fetch_user("alice")
    assert isinstance(cached, IRCUser) and cached.id == "alice"
    own = await backend.fetch_user(id="BOT")
    assert own is not None and own.id == "bot" and own.is_bot
    assert await backend.fetch_user("stranger") is None
    assert await backend.fetch_user() is None


@pytest.mark.asyncio
async def test_fetch_channel() -> None:
    backend, _ = attached_backend()
    existing = IRCChannel(id="#known", name="#known")

    assert await backend.fetch_channel(existing) is existing
    created = await backend.fetch_channel("#new")
    assert created is not None and created.id == "#new"
    cached = await backend.fetch_channel(id="#new")
    assert cached is not None and cached.id == "#new"
    by_name = await backend.fetch_channel(name="&local")
    assert by_name is not None and by_name.id == "&local"
    assert await backend.fetch_channel("nick") is None
    assert await backend.fetch_channel() is None


@pytest.mark.asyncio
async def test_fetch_messages_time_bounds_and_limit() -> None:
    backend, _ = attached_backend()
    for number in (1, 2, 3):
        await backend._handle_line(f"@msgid=m{number};time=2026-07-18T12:0{number}:00Z :alice!u@h PRIVMSG #chatom :msg {number}")

    async def ids(**kwargs: object) -> list[str]:
        return [message.id for message in await backend.fetch_messages("#chatom", **kwargs)]

    assert await ids() == ["m3", "m2", "m1"]
    assert await ids(limit=1) == ["m3"]
    assert await ids(before="m2") == ["m2", "m1"]
    assert await ids(after="m2") == ["m3", "m2"]
    assert await ids(before=datetime(2026, 7, 18, 12, 2))  # noqa: DTZ001 == ["m2", "m1"]
    assert await ids(after=datetime(2026, 7, 18, 12, 4, tzinfo=UTC)) == []
    assert await ids(after=(await backend.fetch_messages("#chatom"))[0]) == ["m3"]
    assert await ids(before="missing") == ["m3", "m2", "m1"]
    assert await backend.fetch_messages(IRCChannel(id="#chatom", name="#chatom"), limit=1) != []


@pytest.mark.asyncio
async def test_fetch_messages_requests_server_history() -> None:
    backend, writer = attached_backend()
    backend._enabled_capabilities.add("draft/chathistory")

    task = asyncio.create_task(backend.fetch_messages("#chatom", limit=5))
    while not writer.lines:
        await asyncio.sleep(0)
    await backend._handle_line("BATCH +h chathistory #chatom")
    await backend._handle_line("@batch=h;msgid=old :alice!u@h PRIVMSG #chatom :from history")
    await backend._handle_line("BATCH -h")
    history = await asyncio.wait_for(task, timeout=2)

    assert writer.lines == ["CHATHISTORY LATEST #chatom * 5"]
    assert [message.id for message in history] == ["old"]


@pytest.mark.asyncio
async def test_fetch_messages_history_timeout_falls_back_to_local() -> None:
    backend, writer = attached_backend()
    backend.config.timeout = 0.05
    backend._enabled_capabilities.add("chathistory")
    await backend._handle_line("@msgid=local :alice!u@h PRIVMSG #chatom :cached")

    history = await backend.fetch_messages("#chatom")

    assert writer.lines == ["CHATHISTORY LATEST #chatom * 100"]
    assert backend._history_waiters == {}
    assert [message.id for message in history] == ["local"]


@pytest.mark.asyncio
async def test_send_message_writes_privmsg_and_records_history() -> None:
    backend, writer = attached_backend()

    sent = await backend.send_message(IRCChannel(id="#chatom", name="#chatom"), "hello there")

    assert writer.lines == ["PRIVMSG #chatom :hello there"]
    assert sent.author is not None and sent.author.id == "bot" and sent.author.is_bot
    assert sent.target == "#chatom"
    assert [message.id for message in await backend.fetch_messages("#chatom")] == [sent.id]


@pytest.mark.asyncio
async def test_send_message_rejects_bad_input_and_missing_writer() -> None:
    backend, writer = attached_backend()

    with pytest.raises(ValueError, match="cannot be empty"):
        await backend.send_message("#chatom", "")
    with pytest.raises(ValueError, match="CR or LF"):
        await backend.send_message("#chatom", "line1\nline2")
    assert writer.lines == []

    backend._writer = None
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.send_message("#chatom", "hi")


@pytest.mark.asyncio
async def test_stream_messages_filters_own_and_channel() -> None:
    backend, _ = attached_backend()
    await backend._handle_line(":bot!u@h PRIVMSG #chatom :own")
    await backend._handle_line(":alice!u@h PRIVMSG #other :elsewhere")
    await backend._handle_line("@msgid=want :alice!u@h PRIVMSG #chatom :wanted")
    await backend._messages.put(None)

    streamed = [message async for message in backend.stream_messages(channel="#chatom")]
    assert [message.id for message in streamed] == ["want"]

    await backend._handle_line("@msgid=mine :BOT!u@h PRIVMSG #chatom :own again")
    await backend._messages.put(None)
    with_own = [message.id async for message in backend.stream_messages(skip_own=False)]
    assert with_own == ["mine"]


@pytest.mark.asyncio
async def test_stream_messages_requires_connection() -> None:
    backend = IRCBackend()

    with pytest.raises(ConnectionError, match="Not connected"):
        await anext(backend.stream_messages())


@pytest.mark.asyncio
async def test_set_presence_sends_away_and_records_state() -> None:
    backend, writer = attached_backend()

    await backend.set_presence("dnd", "Busy")
    busy = await backend.get_presence("bot")
    assert writer.lines[-1] == "AWAY :Busy"
    assert busy is not None and busy.status == PresenceStatus.IDLE and busy.away_message == "Busy"

    await backend.set_presence("Away")
    assert writer.lines[-1] == "AWAY :Away"

    await backend.set_presence("online")
    back = await backend.get_presence("bot")
    assert writer.lines[-1] == "AWAY"
    assert back is not None and back.status == PresenceStatus.ONLINE and back.away_message == ""


@pytest.mark.asyncio
async def test_set_presence_requires_connection() -> None:
    with pytest.raises(ConnectionError, match="Not connected"):
        await IRCBackend().set_presence("away")


@pytest.mark.asyncio
async def test_get_bot_info() -> None:
    backend, _ = attached_backend()

    bot = await backend.get_bot_info()

    assert bot.id == "bot" and bot.is_bot


@pytest.mark.asyncio
async def test_disconnect_quits_closes_and_cancels_reader_task() -> None:
    backend, writer = attached_backend()
    backend._reader_task = asyncio.create_task(asyncio.sleep(60))
    task = backend._reader_task

    await backend.disconnect()

    assert writer.lines == ["QUIT :chatom disconnect"]
    assert writer.closing
    assert task.cancelled()
    assert not backend.connected
    assert backend._writer is None and backend._reader is None and backend._reader_task is None
    assert backend._messages.get_nowait() is None


@pytest.mark.asyncio
async def test_disconnect_tolerates_connection_errors() -> None:
    backend, writer = attached_backend()
    writer.drain_error = ConnectionResetError("gone")
    writer.close_error = OSError("broken pipe")

    await backend.disconnect()

    assert writer.closing
    assert not backend.connected


@pytest.mark.asyncio
async def test_disconnect_skips_quit_on_closing_writer() -> None:
    backend, writer = attached_backend()
    writer.closing = True

    await backend.disconnect()

    assert writer.lines == []
    assert backend._writer is None
