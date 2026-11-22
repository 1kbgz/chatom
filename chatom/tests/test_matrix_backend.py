"""Focused tests for the Matrix backend."""

import asyncio
import sys
import types
from datetime import UTC, datetime

import pytest

from chatom.base import Channel, Presence, PresenceStatus, User, get_backend_type, mention_channel, mention_user
from chatom.format import Format, FormattedMessage
from chatom.matrix import (
    MatrixBackend,
    MatrixChannel,
    MatrixConfig,
    MatrixPresence,
    MatrixPresenceState,
    MatrixUser,
    MockMatrixBackend,
)


def test_config_loads_token_file(tmp_path):
    token_file = tmp_path / "matrix-token"
    token_file.write_text("secret-token\n")

    config = MatrixConfig(access_token=str(token_file), password="secret-password")

    assert config.access_token_str == "secret-token"
    assert config.password_str == "secret-password"
    assert "secret-token" not in repr(config)


def test_matrix_mentions_and_conversion_registration():
    user = MatrixUser(id="@alice:example.org", name="Alice")
    room = MatrixChannel(
        id="!room:example.org",
        name="General",
        canonical_alias="#general:example.org",
    )

    assert mention_user(user) == '<a href="https://matrix.to/#/@alice:example.org">Alice</a>'
    assert mention_channel(room) == '<a href="https://matrix.to/#/#general:example.org">General</a>'
    assert get_backend_type(User, "matrix") is MatrixUser
    assert get_backend_type(Channel, "matrix") is MatrixChannel
    assert get_backend_type(Presence, "matrix") is MatrixPresence


def test_parse_matrix_reply_event():
    backend = MatrixBackend()
    event = {
        "type": "m.room.message",
        "event_id": "$reply",
        "sender": "@alice:example.org",
        "origin_server_ts": 1_700_000_000_000,
        "content": {
            "msgtype": "m.text",
            "body": "reply",
            "format": "org.matrix.custom.html",
            "formatted_body": "<b>reply</b>",
            "m.relates_to": {"m.in_reply_to": {"event_id": "$parent"}},
        },
    }

    message = backend._parse_message_event(event, "!room:example.org")

    assert message is not None
    assert message.id == "$reply"
    assert message.author_id == "@alice:example.org"
    assert message.reference is not None
    assert message.reference.message_id == "$parent"
    assert message.formatted_content == "<b>reply</b>"
    assert message.created_at == datetime.fromtimestamp(1_700_000_000, tz=UTC)


def test_formatted_message_mentions_become_matrix_links():
    backend = MatrixBackend()
    formatted = (
        FormattedMessage()
        .add_mention("@alice:example.org", "Alice")
        .channel_mention(MatrixChannel(id="!room:example.org", name="General"))
        .render(Format.HTML)
    )

    content = backend._message_content(formatted)

    assert 'href="https://matrix.to/#/@alice:example.org"' in content["formatted_body"]
    assert 'href="https://matrix.to/#/!room:example.org"' in content["formatted_body"]


@pytest.fixture
def backend():
    result = MockMatrixBackend(
        config=MatrixConfig(
            homeserver="https://matrix.example.org",
            user_id="@bot:example.org",
            access_token="test-token",
            device_id="DEVICE",
        )
    )
    result.add_mock_user("@bot:example.org", "Bot", is_bot=True)
    result.add_mock_user("@alice:example.org", "Alice")
    result.add_mock_channel(
        "!general:example.org",
        "General",
        canonical_alias="#general:example.org",
    )
    return result


@pytest.mark.asyncio
async def test_mock_message_lifecycle_and_history(backend):
    await backend.connect()
    older = backend.add_mock_message(
        "!general:example.org",
        "@alice:example.org",
        "older",
        event_id="$older",
    )
    sent = await backend.send_message(
        "!general:example.org",
        "<b>Hello</b>",
        reply_to=older,
    )

    assert sent.content == "Hello"
    assert sent.formatted_content == "<b>Hello</b>"
    assert sent.reference.message_id == "$older"
    assert (await backend.fetch_messages("!general:example.org"))[0] == sent

    edited = await backend.edit_message(sent, "<i>Updated</i>")
    assert edited.content == "Updated"
    assert edited.is_edited
    assert backend.edited_messages == [edited]

    await backend.delete_message(sent)
    assert backend.deleted_messages == [("!general:example.org", sent.id)]
    assert await backend.fetch_messages("!general:example.org") == [older]


@pytest.mark.asyncio
async def test_mock_presence_and_streaming(backend):
    await backend.connect()
    backend.set_mock_presence(
        "@alice:example.org",
        MatrixPresenceState.UNAVAILABLE,
        "Lunch",
    )

    presence = await backend.get_presence("@alice:example.org")
    assert presence.status == PresenceStatus.IDLE
    assert presence.status_text == "Lunch"

    stream = backend.stream_messages("!general:example.org")
    backend.add_mock_message(
        "!general:example.org",
        "@alice:example.org",
        "Incoming",
        queue=True,
    )
    incoming = await asyncio.wait_for(anext(stream), timeout=1)
    await stream.aclose()
    assert incoming.content == "Incoming"


@pytest.mark.asyncio
async def test_encrypted_room_is_explicitly_unsupported(backend):
    await backend.connect()
    backend.add_mock_channel("!encrypted:example.org", "Secret", encrypted=True)

    with pytest.raises(NotImplementedError, match="end-to-end encrypted"):
        await backend.send_message("!encrypted:example.org", "Nope")


@pytest.fixture
def nio_stub(monkeypatch):
    """Provide the one nio symbol fetch_messages imports.

    matrix-nio is an optional dependency, so the history tests stub it
    rather than requiring the SDK to be installed.
    """
    module = types.ModuleType("nio")
    module.MessageDirection = types.SimpleNamespace(back="b", front="f")
    monkeypatch.setitem(sys.modules, "nio", module)
    return module


class _Response:
    """Stand-in for a nio response object (no name ending in 'Error')."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


class FakeNioClient:
    """Minimal nio client recording room_messages/room_send calls."""

    def __init__(self, pages):
        self._pages = list(pages)
        self.history_requests = []
        self.sent = []
        self.rooms = {}

    async def room_messages(self, room_id, start=None, direction=None, limit=None):
        self.history_requests.append({"room_id": room_id, "start": start, "limit": limit})
        if not self._pages:
            return _Response(chunk=[], end=None)
        chunk, end = self._pages.pop(0)
        return _Response(chunk=chunk, end=end)

    async def room_send(self, room_id=None, message_type=None, content=None, **kwargs):
        self.sent.append({"room_id": room_id, "content": content})
        return _Response(event_id="$replacement")


def _event(event_id: str, ts: int) -> dict:
    return {
        "type": "m.room.message",
        "event_id": event_id,
        "sender": "@alice:example.org",
        "origin_server_ts": ts,
        "content": {"msgtype": "m.text", "body": event_id},
    }


def _live_backend(client) -> MatrixBackend:
    backend = MatrixBackend(
        config=MatrixConfig(
            homeserver="https://example.org",
            user_id="@bot:example.org",
            access_token="token",
            device_id="DEVICE",
        )
    )
    backend._client = client
    backend.connected = True
    backend._next_batch = "s0"
    backend._bot_user_id = "@bot:example.org"
    return backend


@pytest.mark.asyncio
async def test_fetch_messages_pages_until_limit_is_satisfied(nio_stub) -> None:
    """History must page, not return one short chunk.

    Regression: a single room_messages call returned fewer than `limit`
    messages even when the room had more.
    """
    client = FakeNioClient(
        pages=[
            ([_event("$e1", 1_700_000_003_000)], "s1"),
            ([_event("$e2", 1_700_000_002_000)], "s2"),
            ([_event("$e3", 1_700_000_001_000)], "s3"),
        ]
    )
    backend = _live_backend(client)

    messages = await backend.fetch_messages("!room:example.org", limit=3)

    assert [message.id for message in messages] == ["$e1", "$e2", "$e3"]
    assert len(client.history_requests) == 3
    assert [request["start"] for request in client.history_requests] == ["s0", "s1", "s2"]


@pytest.mark.asyncio
async def test_fetch_messages_stops_when_history_is_exhausted(nio_stub) -> None:
    """Paging terminates when the server stops advancing the token."""
    client = FakeNioClient(pages=[([_event("$only", 1_700_000_000_000)], None)])
    backend = _live_backend(client)

    messages = await backend.fetch_messages("!room:example.org", limit=50)

    assert [message.id for message in messages] == ["$only"]
    assert len(client.history_requests) == 1


@pytest.mark.asyncio
async def test_edit_message_reports_the_original_event_id() -> None:
    """Edits must identify the original event, not the m.replace event.

    Regression: returning the replacement id meant delete_message() on the
    result redacted only the edit and left the original message visible.
    """
    client = FakeNioClient(pages=[])
    backend = _live_backend(client)

    edited = await backend.edit_message("$original", "updated", channel="!room:example.org")

    assert edited.id == "$original"
    assert edited.replacement_event_id == "$replacement"
    assert edited.is_edited
    relation = client.sent[0]["content"]["m.relates_to"]
    assert relation == {"rel_type": "m.replace", "event_id": "$original"}


class FakeError(_Response):
    """Stand-in for a nio error response; the class name ends in 'Error'."""


class FakeMatrixClient(FakeNioClient):
    """nio client fake covering login, sync, profile, presence and redaction."""

    def __init__(self, pages=(), *, syncs=(), **responses):
        super().__init__(pages)
        self.calls = []
        self.user_id = ""
        self.closed = False
        self._syncs = list(syncs)
        self.responses = responses

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return self.responses.get(name, _Response())

    def calls_to(self, name):
        return [(args, kwargs) for call, args, kwargs in self.calls if call == name]

    def restore_login(self, *args):
        self._record("restore_login", *args)

    async def login(self, *args, **kwargs):
        return self._record("login", *args, **kwargs)

    async def sync(self, **kwargs):
        self.calls.append(("sync", (), kwargs))
        if not self._syncs:
            raise asyncio.CancelledError
        return self._syncs.pop(0)

    async def close(self):
        self.closed = True

    async def get_profile(self, user_id):
        return self._record("get_profile", user_id)

    async def room_resolve_alias(self, alias):
        return self._record("room_resolve_alias", alias)

    async def room_redact(self, room_id, event_id):
        return self._record("room_redact", room_id, event_id)

    async def get_presence(self, user_id):
        return self._record("get_presence", user_id)

    async def set_presence(self, state, status_msg=None):
        return self._record("set_presence", state, status_msg=status_msg)

    async def room_send(self, room_id=None, message_type=None, content=None, **kwargs):
        self.sent.append({"room_id": room_id, "content": content, "kwargs": kwargs})
        return self.responses.get("room_send", _Response(event_id="$sent"))


def _nio_room(room_id="!r1:example.org", **fields):
    defaults = {
        "room_id": room_id,
        "display_name": "Room One",
        "topic": "A topic",
        "canonical_alias": "#r1:example.org",
        "encrypted": False,
        "users": {"@a:example.org": object(), "@b:example.org": object()},
    }
    return types.SimpleNamespace(**{**defaults, **fields})


def _sync_response(next_batch, events_by_room=None):
    join = {room_id: types.SimpleNamespace(timeline=types.SimpleNamespace(events=events)) for room_id, events in (events_by_room or {}).items()}
    return _Response(next_batch=next_batch, rooms=types.SimpleNamespace(join=join))


def _connect_config(**overrides) -> MatrixConfig:
    fields = {
        "homeserver": "https://example.org",
        "user_id": "@bot:example.org",
        "access_token": "token",
        "device_id": "DEVICE",
    }
    fields.update(overrides)
    return MatrixConfig(**fields)


@pytest.fixture
def nio_client(nio_stub):
    """Install a nio.AsyncClient that returns one shared fake client."""
    client = FakeMatrixClient(syncs=[_Response(next_batch="s9")])
    client.constructed_with = None

    def factory(*args, **kwargs):
        client.constructed_with = (args, kwargs)
        return client

    nio_stub.AsyncClient = factory
    return client


def test_bot_identity_properties() -> None:
    backend = MatrixBackend()
    assert backend.bot_user_id is None
    assert backend.bot_user_name is None

    backend._bot_user_id = "@bot:example.org"
    assert backend.bot_user_id == "@bot:example.org"
    assert backend.bot_user_name == "bot"


@pytest.mark.asyncio
async def test_connect_with_access_token_restores_login_and_caches_rooms(nio_client) -> None:
    nio_client.user_id = "@resolved:example.org"
    nio_client.rooms = {"!r1:example.org": _nio_room(encrypted=True)}
    backend = MatrixBackend(config=_connect_config(store_path="/tmp/store"))

    await backend.connect()

    assert nio_client.constructed_with == (
        ("https://example.org", "@bot:example.org"),
        {"device_id": "DEVICE", "store_path": "/tmp/store"},
    )
    assert nio_client.calls_to("restore_login") == [(("@bot:example.org", "DEVICE", "token"), {})]
    assert nio_client.calls_to("login") == []
    assert nio_client.calls_to("sync") == [((), {"timeout": 0, "full_state": True})]
    assert backend.connected
    assert backend._next_batch == "s9"
    assert backend.bot_user_id == "@resolved:example.org"
    cached = backend.channels.get_by_id("!r1:example.org")
    assert cached.name == "Room One"
    assert cached.topic == "A topic"
    assert cached.canonical_alias == "#r1:example.org"
    assert cached.encrypted
    assert cached.member_count == 2


@pytest.mark.asyncio
async def test_connect_with_password_logs_in_and_defaults_bot_id(nio_client) -> None:
    backend = MatrixBackend(config=_connect_config(access_token="", device_id="", password="hunter2"))

    await backend.connect()

    assert nio_client.calls_to("login") == [(("hunter2",), {"device_name": "chatom"})]
    assert nio_client.calls_to("restore_login") == []
    assert backend.bot_user_id == "@bot:example.org"
    assert backend.connected


@pytest.mark.asyncio
async def test_connect_password_login_error_is_raised(nio_client) -> None:
    nio_client.responses["login"] = type("LoginError", (_Response,), {})(message="bad credentials")
    backend = MatrixBackend(config=_connect_config(access_token="", device_id="", password="wrong"))

    with pytest.raises(RuntimeError, match="Matrix login failed: bad credentials"):
        await backend.connect()

    assert not backend.connected


@pytest.mark.asyncio
async def test_connect_initial_sync_error_is_raised(nio_client) -> None:
    nio_client._syncs = [type("SyncError", (_Response,), {})(message="boom")]
    backend = MatrixBackend(config=_connect_config())

    with pytest.raises(RuntimeError, match="Initial Matrix sync failed: boom"):
        await backend.connect()

    assert not backend.connected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"homeserver": ""}, "homeserver is required"),
        ({"user_id": ""}, "user_id is required"),
        ({"device_id": ""}, "device_id is required when using access_token"),
        ({"access_token": ""}, "access_token or password is required"),
    ],
)
async def test_connect_validates_config(nio_client, overrides, message) -> None:
    backend = MatrixBackend(config=_connect_config(**overrides))

    with pytest.raises(ValueError, match=message):
        await backend.connect()

    assert not backend.connected


@pytest.mark.asyncio
async def test_connect_requires_matrix_nio(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "nio", None)

    with pytest.raises(ImportError, match="matrix-nio is required"):
        await MatrixBackend(config=_connect_config()).connect()


@pytest.mark.asyncio
async def test_disconnect_closes_client_and_resets_state() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    await backend.disconnect()

    assert client.closed
    assert backend._client is None
    assert backend._next_batch is None
    assert backend.bot_user_id is None
    assert not backend.connected

    await backend.disconnect()
    assert not backend.connected


@pytest.mark.asyncio
async def test_operations_require_connection() -> None:
    backend = MatrixBackend()

    with pytest.raises(ConnectionError, match="Not connected to Matrix"):
        await backend.fetch_user("@alice:example.org")
    with pytest.raises(ConnectionError, match="Not connected to Matrix"):
        await backend.send_message("!room:example.org", "hi")

    backend.connected = True
    with pytest.raises(ConnectionError, match="Not connected to Matrix"):
        await backend.get_presence("@alice:example.org")


def test_raise_for_error_uses_message_or_repr() -> None:
    MatrixBackend._raise_for_error(_Response(), "ok")

    with pytest.raises(RuntimeError, match="ctx: nope"):
        MatrixBackend._raise_for_error(FakeError(message="nope"), "ctx")
    with pytest.raises(RuntimeError, match="ctx: .*FakeError"):
        MatrixBackend._raise_for_error(FakeError(), "ctx")


def test_source_accepts_dicts_and_objects_with_source() -> None:
    raw = {"type": "m.room.message"}

    assert MatrixBackend._source(raw) is raw
    assert MatrixBackend._source(_Response(source=raw)) is raw
    assert MatrixBackend._source(_Response(source="not-a-dict")) == {}
    assert MatrixBackend._source(object()) == {}


def test_room_from_nio_falls_back_to_room_id() -> None:
    backend = MatrixBackend()

    sparse = backend._room_from_nio(types.SimpleNamespace(room_id="!bare:example.org", users=None))
    named = backend._room_from_nio(types.SimpleNamespace(room_id="!n:example.org", name="Named", display_name=None))

    assert sparse.name == "!bare:example.org"
    assert sparse.topic == ""
    assert sparse.canonical_alias == ""
    assert not sparse.encrypted
    assert sparse.member_count == 0
    assert named.name == "Named"


@pytest.mark.asyncio
async def test_fetch_user_looks_up_profile_then_serves_from_cache() -> None:
    client = FakeMatrixClient(get_profile=_Response(displayname="Alice", avatar_url="mxc://example.org/a"))
    backend = _live_backend(client)

    user = await backend.fetch_user("@alice:example.org")

    assert isinstance(user, MatrixUser)
    assert user.id == "@alice:example.org"
    assert user.name == "Alice"
    assert user.avatar_mxc == "mxc://example.org/a"
    assert client.calls_to("get_profile") == [(("@alice:example.org",), {})]

    again = await backend.fetch_user(id="@alice:example.org")
    by_name = await backend.fetch_user(name="Alice")
    assert again.id == by_name.id == "@alice:example.org"
    assert len(client.calls_to("get_profile")) == 1


@pytest.mark.asyncio
async def test_fetch_user_defaults_display_name_to_mxid() -> None:
    backend = _live_backend(FakeMatrixClient(get_profile=_Response()))

    user = await backend.fetch_user("@anon:example.org")

    assert user.name == "@anon:example.org"
    assert user.avatar_mxc == ""


@pytest.mark.asyncio
async def test_fetch_user_handles_missing_profile_and_missing_identifier() -> None:
    client = FakeMatrixClient(get_profile=FakeError(message="not found"))
    backend = _live_backend(client)

    assert await backend.fetch_user("@ghost:example.org") is None
    assert await backend.fetch_user() is None
    assert await backend.fetch_user(name="nobody") is None
    assert len(client.calls_to("get_profile")) == 1


@pytest.mark.asyncio
async def test_fetch_user_accepts_user_objects() -> None:
    client = FakeMatrixClient(get_profile=_Response(displayname="Carol"))
    backend = _live_backend(client)
    matrix_user = MatrixUser(id="@bob:example.org", name="Bob")

    assert await backend.fetch_user(matrix_user) is matrix_user
    assert client.calls_to("get_profile") == []

    fetched = await backend.fetch_user(User(id="@carol:example.org", name="Carol"))
    assert fetched.id == "@carol:example.org"
    assert client.calls_to("get_profile") == [(("@carol:example.org",), {})]


@pytest.mark.asyncio
async def test_fetch_user_converts_cached_generic_user() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)
    backend.users.add(User(id="@gen:example.org", name="Generic"))

    user = await backend.fetch_user("@gen:example.org")

    assert isinstance(user, MatrixUser)
    assert user.name == "Generic"
    assert client.calls_to("get_profile") == []


@pytest.mark.asyncio
async def test_fetch_channel_prefers_cache_by_name_and_id() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)
    cached = MatrixChannel(id="!c:example.org", name="Cached")
    backend.channels.add(cached)

    assert (await backend.fetch_channel(name="Cached")).id == "!c:example.org"
    assert (await backend.fetch_channel("!c:example.org")).id == "!c:example.org"
    assert (await backend.fetch_channel(id="!c:example.org", name="Missing")).id == "!c:example.org"
    assert await backend.fetch_channel() is None
    assert client.calls == []


@pytest.mark.asyncio
async def test_fetch_channel_accepts_channel_objects() -> None:
    backend = _live_backend(FakeMatrixClient())
    room = MatrixChannel(id="!m:example.org", name="Direct")

    assert await backend.fetch_channel(room) is room

    backend.channels.add(Channel(id="!g:example.org", name="Generic"))
    converted = await backend.fetch_channel(Channel(id="!g:example.org", name="Generic"))
    assert isinstance(converted, MatrixChannel)
    assert converted.name == "Generic"


@pytest.mark.asyncio
async def test_fetch_channel_loads_joined_room_by_id() -> None:
    client = FakeMatrixClient()
    client.rooms = {"!r1:example.org": _nio_room()}
    backend = _live_backend(client)

    channel = await backend.fetch_channel("!r1:example.org")

    assert channel.name == "Room One"
    assert backend.channels.get_by_id("!r1:example.org") is not None
    assert await backend.fetch_channel("!other:example.org") is None


@pytest.mark.asyncio
async def test_fetch_channel_resolves_alias() -> None:
    client = FakeMatrixClient(room_resolve_alias=_Response(room_id="!r1:example.org"))
    client.rooms = {"!r1:example.org": _nio_room()}
    backend = _live_backend(client)

    channel = await backend.fetch_channel("#r1:example.org")

    assert channel.id == "!r1:example.org"
    assert client.calls_to("room_resolve_alias") == [(("#r1:example.org",), {})]


@pytest.mark.asyncio
async def test_fetch_channel_alias_error_returns_none() -> None:
    backend = _live_backend(FakeMatrixClient(room_resolve_alias=FakeError(message="unknown alias")))

    assert await backend.fetch_channel("#nope:example.org") is None


@pytest.mark.asyncio
async def test_fetch_channel_by_name_scans_joined_rooms() -> None:
    client = FakeMatrixClient()
    client.rooms = {"!r1:example.org": _nio_room()}
    backend = _live_backend(client)

    found = await backend.fetch_channel(name="Room One")
    missing = await backend.fetch_channel(name="No Such Room")

    assert found.id == "!r1:example.org"
    assert missing is None


def test_parse_event_ignores_non_message_events() -> None:
    backend = MatrixBackend()
    member_event = {"type": "m.room.member", "event_id": "$m", "sender": "@alice:example.org", "content": {}}

    assert backend._parse_message_event(member_event, "!room:example.org") is None


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ({"body": "chatom-bot: /help", "m.mentions": {"user_ids": ["@bot:example.org", "@bot:example.org"]}}, ["@bot:example.org"]),
        (
            {"body": "bot: hi", "formatted_body": '<a href="https://matrix.to/#/@bot:example.org">bot</a>: hi'},
            ["@bot:example.org"],
        ),
        ({"body": "no one", "m.mentions": {}}, []),
    ],
)
def test_parse_event_reads_mentions(content, expected) -> None:
    backend = MatrixBackend()
    event = {"type": "m.room.message", "event_id": "$m", "sender": "@alice:example.org", "content": {"msgtype": "m.text", **content}}

    message = backend._parse_message_event(event, "!room:example.org")

    assert [user.id for user in message.mentions] == expected


def test_parse_event_reads_attribute_style_events() -> None:
    backend = MatrixBackend()
    event = types.SimpleNamespace(
        event_id="$attr",
        sender="@alice:example.org",
        body="plain text",
        server_timestamp=1_700_000_000_000,
    )

    message = backend._parse_message_event(event, "!room:example.org")

    assert message.id == "$attr"
    assert message.content == "plain text"
    assert message.author_id == "@alice:example.org"
    assert message.created_at == datetime.fromtimestamp(1_700_000_000, tz=UTC)
    assert message.channel_id == "!room:example.org"
    assert message.reference is None


def test_parse_event_maps_thread_relation_and_transaction_id() -> None:
    backend = MatrixBackend()
    event = {
        "type": "m.room.message",
        "event_id": "$in-thread",
        "sender": "@alice:example.org",
        "content": {
            "msgtype": "m.notice",
            "body": "in thread",
            "m.relates_to": {"rel_type": "m.thread", "event_id": "$root"},
        },
        "unsigned": {"transaction_id": "txn-1"},
    }

    message = backend._parse_message_event(event, "!room:example.org")

    assert message.thread_id == "$root"
    assert message.reference is None
    assert message.msgtype == "m.notice"
    assert message.transaction_id == "txn-1"
    assert message.created_at is None
    assert message.raw is event


def test_parse_event_applies_replacement_content() -> None:
    backend = MatrixBackend()
    event = {
        "type": "m.room.message",
        "event_id": "$edit",
        "sender": "@alice:example.org",
        "content": {
            "msgtype": "m.text",
            "body": "* fixed",
            "m.new_content": {"msgtype": "m.text", "body": "fixed", "formatted_body": "<b>fixed</b>"},
            "m.relates_to": {"rel_type": "m.replace", "event_id": "$orig"},
        },
    }

    message = backend._parse_message_event(event, "!room:example.org")

    assert message.content == "fixed"
    assert message.formatted_content == "<b>fixed</b>"
    assert message.is_edited


def test_parse_event_without_sender_has_no_author() -> None:
    backend = MatrixBackend()
    event = {"type": "m.room.message", "event_id": "$anon", "content": {"body": "hi"}}

    message = backend._parse_message_event(event, "!room:example.org")

    assert message.author is None


@pytest.mark.asyncio
async def test_fetch_messages_syncs_when_no_batch_token(nio_stub) -> None:
    client = FakeMatrixClient(
        pages=[([_event("$e1", 1_700_000_000_000)], None)],
        syncs=[_Response(next_batch="fresh")],
    )
    backend = _live_backend(client)
    backend._next_batch = None

    messages = await backend.fetch_messages("!room:example.org", limit=5)

    assert [message.id for message in messages] == ["$e1"]
    assert client.calls_to("sync") == [((), {"timeout": 0})]
    assert client.history_requests[0]["start"] == "fresh"
    assert backend._next_batch == "fresh"


@pytest.mark.asyncio
async def test_fetch_messages_returns_empty_without_sync_token(nio_stub) -> None:
    client = FakeMatrixClient(syncs=[_Response()])
    backend = _live_backend(client)
    backend._next_batch = None

    assert await backend.fetch_messages("!room:example.org") == []
    assert client.history_requests == []


@pytest.mark.asyncio
async def test_fetch_messages_raises_on_sync_and_history_errors(nio_stub) -> None:
    backend = _live_backend(FakeMatrixClient(syncs=[FakeError(message="sync down")]))
    backend._next_batch = None
    with pytest.raises(RuntimeError, match="Matrix sync failed: sync down"):
        await backend.fetch_messages("!room:example.org")

    class HistoryClient(FakeMatrixClient):
        async def room_messages(self, room_id, start=None, direction=None, limit=None):
            return FakeError(message="forbidden")

    with pytest.raises(RuntimeError, match="Matrix message history failed: forbidden"):
        await _live_backend(HistoryClient()).fetch_messages("!room:example.org")


@pytest.mark.asyncio
async def test_fetch_messages_skips_non_message_events_and_applies_bounds(nio_stub) -> None:
    member = {"type": "m.room.member", "event_id": "$m", "sender": "@alice:example.org", "content": {}}
    chunk = [_event("$e3", 1_700_000_003_000), member, _event("$e2", 1_700_000_002_000), _event("$e1", 1_700_000_001_000)]

    def backend_with_history():
        return _live_backend(FakeMatrixClient(pages=[(chunk, None)]))

    everything = await backend_with_history().fetch_messages("!room:example.org")
    before_id = await backend_with_history().fetch_messages("!room:example.org", before="$e2")
    after_id = await backend_with_history().fetch_messages("!room:example.org", after="$e2")
    cutoff = datetime.fromtimestamp(1_700_000_002, tz=UTC)
    before_time = await backend_with_history().fetch_messages("!room:example.org", before=cutoff)
    after_time = await backend_with_history().fetch_messages("!room:example.org", after=cutoff)

    assert [m.id for m in everything] == ["$e3", "$e2", "$e1"]
    assert [m.id for m in before_id] == ["$e2", "$e1"]
    assert [m.id for m in after_id] == ["$e3", "$e2"]
    assert [m.id for m in before_time] == ["$e2", "$e1"]
    assert [m.id for m in after_time] == ["$e3", "$e2"]


def test_filter_message_bounds_accepts_message_objects() -> None:
    backend = MatrixBackend()
    first = backend._parse_message_event(_event("$a", 1_700_000_003_000), "!r:example.org")
    second = backend._parse_message_event(_event("$b", 1_700_000_002_000), "!r:example.org")
    third = backend._parse_message_event(_event("$c", 1_700_000_001_000), "!r:example.org")
    messages = [first, second, third]

    assert backend._filter_message_bounds(messages, second, None) == [second, third]
    assert backend._filter_message_bounds(messages, None, second) == [first, second]
    assert backend._filter_message_bounds(messages, "$unknown", "$also-unknown") == messages
    assert backend._filter_message_bounds(messages, None, None) == messages


def test_message_content_plain_text_skips_html() -> None:
    backend = MatrixBackend()

    assert backend._message_content("a <b>literal</b>", formatted=False) == {"msgtype": "m.text", "body": "a <b>literal</b>"}
    assert backend._message_content("a &amp; <b>b</b>") == {
        "msgtype": "m.text",
        "body": "a & b",
        "format": "org.matrix.custom.html",
        "formatted_body": "a &amp; <b>b</b>",
    }


@pytest.mark.asyncio
async def test_send_message_posts_plain_room_event() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    sent = await backend.send_message("!room:example.org", "<b>Hi</b>")

    assert client.sent == [
        {
            "room_id": "!room:example.org",
            "content": {
                "msgtype": "m.text",
                "body": "Hi",
                "format": "org.matrix.custom.html",
                "formatted_body": "<b>Hi</b>",
            },
            "kwargs": {},
        }
    ]
    assert sent.id == "$sent"
    assert sent.content == "Hi"
    assert sent.formatted_content == "<b>Hi</b>"
    assert sent.author_id == "@bot:example.org"
    assert sent.channel_id == "!room:example.org"
    assert sent.thread is None
    assert sent.reference is None
    assert sent.relates_to == {}


@pytest.mark.asyncio
async def test_send_message_unformatted_and_extra_kwargs_pass_through() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    sent = await backend.send_message(MatrixChannel(id="!room:example.org", name="R"), "<b>raw</b>", formatted=False, tx_id="t1")

    assert client.sent[0]["content"] == {"msgtype": "m.text", "body": "<b>raw</b>"}
    assert client.sent[0]["kwargs"] == {"tx_id": "t1"}
    assert sent.content == "<b>raw</b>"
    assert sent.formatted_content == ""


@pytest.mark.asyncio
async def test_send_message_builds_reply_relation() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    sent = await backend.send_message("!room:example.org", "re", reply_to="$parent")

    relation = {"m.in_reply_to": {"event_id": "$parent"}}
    assert client.sent[0]["content"]["m.relates_to"] == relation
    assert sent.relates_to == relation
    assert sent.reference.message_id == "$parent"
    assert sent.thread is None


@pytest.mark.asyncio
async def test_send_message_builds_thread_relation() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    in_thread = await backend.send_message("!room:example.org", "t", thread="$root")
    threaded_reply = await backend.send_message("!room:example.org", "t", thread_id="$root", reply_to="$other")

    assert client.sent[0]["content"]["m.relates_to"] == {
        "rel_type": "m.thread",
        "event_id": "$root",
        "is_falling_back": True,
        "m.in_reply_to": {"event_id": "$root"},
    }
    assert client.sent[1]["content"]["m.relates_to"]["m.in_reply_to"] == {"event_id": "$other"}
    assert in_thread.thread_id == "$root"
    assert in_thread.reference is None
    assert threaded_reply.thread_id == "$root"
    assert threaded_reply.reference.message_id == "$other"


@pytest.mark.asyncio
async def test_send_message_raises_on_error_response() -> None:
    backend = _live_backend(FakeMatrixClient(room_send=FakeError(message="rate limited")))

    with pytest.raises(RuntimeError, match="Matrix send failed: rate limited"):
        await backend.send_message("!room:example.org", "hi")


@pytest.mark.asyncio
async def test_send_and_edit_refuse_known_encrypted_rooms() -> None:
    client = FakeMatrixClient()
    client.rooms = {"!nio-secret:example.org": _nio_room("!nio-secret:example.org", encrypted=True)}
    backend = _live_backend(client)
    backend.channels.add(MatrixChannel(id="!cached-secret:example.org", name="Cached", encrypted=True))

    for room_id in ("!nio-secret:example.org", "!cached-secret:example.org"):
        with pytest.raises(NotImplementedError, match="end-to-end encrypted"):
            await backend.send_message(room_id, "hi")
        with pytest.raises(NotImplementedError, match="end-to-end encrypted"):
            await backend.edit_message("$e", "hi", channel=room_id)

    assert client.sent == []


@pytest.mark.asyncio
async def test_edit_message_unformatted_and_error() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    edited = await backend.edit_message("$orig", "<b>raw</b>", channel="!room:example.org", formatted=False)

    payload = client.sent[0]["content"]
    assert payload["body"] == "* <b>raw</b>"
    assert payload["m.new_content"] == {"msgtype": "m.text", "body": "<b>raw</b>"}
    assert edited.content == "<b>raw</b>"
    assert edited.formatted_content == ""

    failing = _live_backend(FakeMatrixClient(room_send=FakeError(message="denied")))
    with pytest.raises(RuntimeError, match="Matrix edit failed: denied"):
        await failing.edit_message("$orig", "x", channel="!room:example.org")


@pytest.mark.asyncio
async def test_delete_message_redacts_event() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    await backend.delete_message("$gone", channel="!room:example.org")

    assert client.calls_to("room_redact") == [(("!room:example.org", "$gone"), {})]


@pytest.mark.asyncio
async def test_delete_message_raises_on_error_response() -> None:
    backend = _live_backend(FakeMatrixClient(room_redact=FakeError(message="no permission")))

    with pytest.raises(RuntimeError, match="Matrix redaction failed: no permission"):
        await backend.delete_message("$gone", channel="!room:example.org")


@pytest.mark.asyncio
async def test_get_bot_info_fetches_own_profile() -> None:
    client = FakeMatrixClient(get_profile=_Response(displayname="Chat Bot"))
    backend = _live_backend(client)

    info = await backend.get_bot_info()

    assert info.id == "@bot:example.org"
    assert info.name == "Chat Bot"
    assert client.calls_to("get_profile") == [(("@bot:example.org",), {})]

    backend._bot_user_id = None
    assert await backend.get_bot_info() is None


@pytest.mark.asyncio
async def test_get_presence_maps_response_fields() -> None:
    response = _Response(presence="unavailable", status_msg="Lunch", currently_active=True, last_active_ago=1500)
    client = FakeMatrixClient(get_presence=response)
    backend = _live_backend(client)

    presence = await backend.get_presence("@alice:example.org")

    assert client.calls_to("get_presence") == [(("@alice:example.org",), {})]
    assert presence.user.id == "@alice:example.org"
    assert presence.status == PresenceStatus.IDLE
    assert presence.matrix_presence == MatrixPresenceState.UNAVAILABLE
    assert presence.status_text == "Lunch"
    assert presence.currently_active
    assert presence.last_active_ago == 1500


@pytest.mark.asyncio
async def test_get_presence_defaults_and_error() -> None:
    bare = await _live_backend(FakeMatrixClient(get_presence=_Response())).get_presence(User(id="@alice:example.org", name="Alice"))
    assert bare.status == PresenceStatus.OFFLINE
    assert bare.status_text == ""
    assert not bare.currently_active
    assert bare.last_active_ago == 0

    missing = _live_backend(FakeMatrixClient(get_presence=FakeError(message="forbidden")))
    assert await missing.get_presence("@alice:example.org") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("online", "online"),
        ("idle", "unavailable"),
        ("dnd", "unavailable"),
        ("away", "unavailable"),
        ("offline", "offline"),
        ("unavailable", "unavailable"),
    ],
)
async def test_set_presence_translates_status(status, expected) -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    await backend.set_presence(status, "busy")

    assert client.calls_to("set_presence") == [((expected,), {"status_msg": "busy"})]


@pytest.mark.asyncio
async def test_set_presence_rejects_unknown_status_and_surfaces_errors() -> None:
    client = FakeMatrixClient()
    backend = _live_backend(client)

    with pytest.raises(ValueError, match="Unsupported Matrix presence: invisible"):
        await backend.set_presence("invisible")
    assert client.calls_to("set_presence") == []

    failing = _live_backend(FakeMatrixClient(set_presence=FakeError(message="nope")))
    with pytest.raises(RuntimeError, match="Matrix presence update failed: nope"):
        await failing.set_presence("online")


def test_sync_room_events_flattens_joined_timelines() -> None:
    first, second, third = _event("$1", 1), _event("$2", 2), _event("$3", 3)
    response = _sync_response("s1", {"!a:example.org": [first, second], "!b:example.org": [third]})

    assert list(MatrixBackend._sync_room_events(response)) == [
        ("!a:example.org", first),
        ("!a:example.org", second),
        ("!b:example.org", third),
    ]
    assert list(MatrixBackend._sync_room_events(_Response(rooms=None))) == []
    assert list(MatrixBackend._sync_room_events(_Response(rooms=types.SimpleNamespace(join=None)))) == []
    empty_timeline = _Response(rooms=types.SimpleNamespace(join={"!a:example.org": types.SimpleNamespace(timeline=None)}))
    assert list(MatrixBackend._sync_room_events(empty_timeline)) == []


@pytest.mark.asyncio
async def test_stream_messages_filters_and_advances_sync_token() -> None:
    own = {**_event("$own", 1), "sender": "@bot:example.org"}
    member = {"type": "m.room.member", "event_id": "$m", "sender": "@alice:example.org", "content": {}}
    client = FakeMatrixClient(
        syncs=[
            _sync_response(
                "s1",
                {
                    "!room:example.org": [_event("$keep", 2), own, member],
                    "!other:example.org": [_event("$elsewhere", 3)],
                },
            ),
            _sync_response("s2", {"!room:example.org": [_event("$later", 4)]}),
            _Response(rooms=None),
        ]
    )
    backend = _live_backend(client)

    received = [message async for message in backend.stream_messages("!room:example.org")]

    assert [message.id for message in received] == ["$keep", "$later"]
    assert [kwargs for _, kwargs in client.calls_to("sync")] == [
        {"timeout": 30000, "since": "s0", "full_state": False},
        {"timeout": 30000, "since": "s1", "full_state": False},
        {"timeout": 30000, "since": "s2", "full_state": False},
        {"timeout": 30000, "since": "s2", "full_state": False},
    ]
    assert backend._next_batch == "s2"


@pytest.mark.asyncio
async def test_stream_messages_can_include_own_and_history() -> None:
    own = {**_event("$own", 1), "sender": "@bot:example.org"}
    client = FakeMatrixClient(syncs=[_sync_response("s1", {"!room:example.org": [own, _event("$alice", 2)]})])
    backend = _live_backend(client)

    received = [message async for message in backend.stream_messages(skip_own=False, skip_history=False)]

    assert [message.id for message in received] == ["$own", "$alice"]
    assert client.calls_to("sync")[0][1]["since"] is None


@pytest.mark.asyncio
async def test_stream_messages_raises_on_sync_error() -> None:
    backend = _live_backend(FakeMatrixClient(syncs=[FakeError(message="sync lost")]))

    with pytest.raises(RuntimeError, match="Matrix sync failed: sync lost"):
        await anext(backend.stream_messages())


@pytest.mark.asyncio
async def test_listen_for_messages_delegates_to_stream() -> None:
    client = FakeMatrixClient(syncs=[_sync_response("s1", {"!room:example.org": [_event("$one", 1)]})])
    backend = _live_backend(client)

    received = [message async for message in backend.listen_for_messages(channel="!room:example.org")]

    assert [message.id for message in received] == ["$one"]


@pytest.mark.asyncio
async def test_mock_disconnect_clears_connection_state(backend) -> None:
    with pytest.raises(ConnectionError, match="Not connected to Matrix"):
        await backend.fetch_user("@alice:example.org")

    await backend.connect()
    assert backend.bot_user_id == "@bot:example.org"

    await backend.disconnect()
    assert not backend.connected
    assert backend.bot_user_id is None
    assert await backend.get_bot_info() is None


@pytest.mark.asyncio
async def test_mock_fetch_user_resolves_by_id_name_and_handle(backend) -> None:
    await backend.connect()
    alice = backend._mock_users["@alice:example.org"]

    assert await backend.fetch_user("@alice:example.org") is alice
    assert await backend.fetch_user(id="@alice:example.org") is alice
    assert await backend.fetch_user(User(id="@alice:example.org", name="x")) is alice
    assert await backend.fetch_user(alice) is alice
    assert await backend.fetch_user(name="ALICE") is alice
    assert await backend.fetch_user(handle="@ALICE:example.org") is alice
    assert await backend.fetch_user(name="nobody") is None
    assert await backend.fetch_user() is None


@pytest.mark.asyncio
async def test_mock_fetch_channel_resolves_by_id_alias_and_name(backend) -> None:
    await backend.connect()
    general = backend._mock_channels["!general:example.org"]

    assert await backend.fetch_channel("!general:example.org") is general
    assert await backend.fetch_channel(id="!general:example.org") is general
    assert await backend.fetch_channel("#general:example.org") is general
    assert await backend.fetch_channel(Channel(id="!general:example.org", name="x")) is general
    assert await backend.fetch_channel(general) is general
    assert await backend.fetch_channel(name="general") is general
    assert await backend.fetch_channel("#missing:example.org") is None
    assert await backend.fetch_channel(name="missing") is None
    assert await backend.fetch_channel() is None


@pytest.mark.asyncio
async def test_mock_send_records_thread_and_plain_content(backend) -> None:
    await backend.connect()

    sent = await backend.send_message("!general:example.org", "<b>raw</b>", thread="$root", formatted=False)

    assert sent.thread_id == "$root"
    assert sent.content == "<b>raw</b>"
    assert sent.formatted_content == ""
    assert backend.sent_messages == [sent]
    assert backend.sent_messages is not backend._sent_messages


@pytest.mark.asyncio
async def test_mock_edit_unformatted_and_unknown_event(backend) -> None:
    await backend.connect()
    message = backend.add_mock_message("!general:example.org", "@alice:example.org", "orig", event_id="$orig")

    edited = await backend.edit_message("$orig", "<i>raw</i>", channel="!general:example.org", formatted=False)

    assert edited is message
    assert edited.content == "<i>raw</i>"
    with pytest.raises(ValueError, match="Unknown Matrix event: \\$missing"):
        await backend.edit_message("$missing", "x", channel="!general:example.org")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "state"),
    [
        ("online", MatrixPresenceState.ONLINE),
        ("idle", MatrixPresenceState.UNAVAILABLE),
        ("away", MatrixPresenceState.UNAVAILABLE),
        ("offline", MatrixPresenceState.OFFLINE),
    ],
)
async def test_mock_set_presence_updates_bot_presence(backend, status, state) -> None:
    await backend.connect()

    await backend.set_presence(status, "note")

    presence = await backend.get_presence("@bot:example.org")
    assert presence.matrix_presence == state
    assert presence.status_text == "note"


@pytest.mark.asyncio
async def test_mock_set_presence_rejects_unknown_status(backend) -> None:
    await backend.connect()

    with pytest.raises(ValueError, match="Unsupported Matrix presence: dnd"):
        await backend.set_presence("dnd")


@pytest.mark.asyncio
async def test_mock_get_bot_info_returns_profile_or_placeholder(backend) -> None:
    await backend.connect()
    assert (await backend.get_bot_info()).name == "Bot"

    backend._bot_user_id = "@unknown:example.org"
    placeholder = await backend.get_bot_info()
    assert placeholder.id == "@unknown:example.org"
    assert placeholder.is_bot


@pytest.mark.asyncio
async def test_mock_stream_filters_channel_and_own_messages(backend) -> None:
    await backend.connect()
    backend.add_mock_channel("!other:example.org", "Other")
    backend.add_mock_message("!other:example.org", "@alice:example.org", "elsewhere", queue=True)
    backend.add_mock_message("!general:example.org", "@bot:example.org", "mine", queue=True)
    backend.add_mock_message("!general:example.org", "@alice:example.org", "wanted", queue=True)

    stream = backend.stream_messages("!general:example.org")
    first = await asyncio.wait_for(anext(stream), timeout=1)
    await stream.aclose()

    assert first.content == "wanted"


@pytest.mark.asyncio
async def test_mock_stream_can_include_own_messages(backend) -> None:
    await backend.connect()
    backend.add_mock_message("!general:example.org", "@bot:example.org", "mine", queue=True)

    stream = backend.stream_messages(skip_own=False)
    first = await asyncio.wait_for(anext(stream), timeout=1)
    await stream.aclose()

    assert first.content == "mine"
