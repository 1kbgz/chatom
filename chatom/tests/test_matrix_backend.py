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
