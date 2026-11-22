"""Tests for the encrypted Matrix backend, with matrix-sdk-python's client replaced by fakes."""

import asyncio
import json
import time

import pytest

sdk = pytest.importorskip("matrix_sdk_python")

from chatom.matrix import MatrixConfig, MatrixE2EEBackend
from chatom.matrix.e2ee import _apply_diff

BOT = "@bot:example.org"
ROOM = "!room:example.org"


class FakeHandle:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeEvent:
    def __init__(self, event_id, sender, body, timestamp=None, raw=None):
        self.is_remote = True
        self.event_or_transaction_id = sdk.EventOrTransactionId.EVENT_ID(event_id=event_id)
        self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000) + 1000
        raw = raw or {
            "type": "m.room.message",
            "event_id": event_id,
            "sender": sender,
            "origin_server_ts": self.timestamp,
            "content": {"msgtype": "m.text", "body": body, "m.mentions": {"user_ids": [BOT]} if "bot" in body else {}},
        }
        info = type("Info", (), {"original_json": json.dumps(raw)})()
        self.lazy_provider = type("Lazy", (), {"debug_info": lambda self: info})()


class FakeItem:
    def __init__(self, event):
        self.event = event

    def as_event(self):
        return self.event


def item(event_id, sender="@alice:example.org", body="hi bot", **kwargs):
    return FakeItem(FakeEvent(event_id, sender, body, **kwargs))


class FakeTimeline:
    def __init__(self, room):
        self.room = room
        self.listener = None
        self.sent = []
        self.history = []

    async def add_listener(self, listener):
        self.listener = listener
        return FakeHandle()

    async def send(self, message):
        self.sent.append(("send", message, None))
        self.room.queue_send()

    async def send_reply(self, message, event_id):
        self.sent.append(("reply", message, event_id))
        self.room.queue_send()

    async def paginate_backwards(self, count):
        if self.history:
            self.listener.on_update([sdk.TimelineDiff.PUSH_FRONT(value=self.history.pop())])
        return not self.history


class FakeRoom:
    def __init__(self, room_id=ROOM, encrypted=True):
        self.room_id = room_id
        self.encrypted = encrypted
        self.timeline_obj = FakeTimeline(self)
        self.send_queue = None
        self.count = 0
        self.edits = []
        self.redactions = []

    def id(self):
        return self.room_id

    def display_name(self):
        return "general"

    def topic(self):
        return None

    def canonical_alias(self):
        return None

    def joined_members_count(self):
        return 2

    async def is_encrypted(self):
        return self.encrypted

    async def timeline(self):
        return self.timeline_obj

    async def subscribe_to_send_queue_updates(self, listener):
        self.send_queue = listener
        return FakeHandle()

    def queue_send(self):
        self.count += 1
        txn = f"txn{self.count}"
        self.send_queue.on_update(sdk.RoomSendQueueUpdate.NEW_LOCAL_EVENT(transaction_id=txn))
        self.send_queue.on_update(sdk.RoomSendQueueUpdate.SENT_EVENT(transaction_id=txn, event_id=f"$sent{self.count}"))

    async def edit(self, event_id, content):
        self.edits.append(event_id)
        self.queue_send()

    async def redact(self, event_id, reason):
        self.redactions.append(event_id)


class FakeEncryption:
    def __init__(self, verified):
        self.verified = verified
        self.recovered_with = None

    async def wait_for_e2ee_initialization_tasks(self):
        pass

    def verification_state(self):
        return sdk.VerificationState.VERIFIED if self.verified else sdk.VerificationState.UNVERIFIED

    async def recover(self, key):
        self.recovered_with = key
        self.verified = True


class FakeClient:
    def __init__(self, rooms, verified=True):
        self._rooms = {room.id(): room for room in rooms}
        self.encryption_obj = FakeEncryption(verified)
        self.logins = []
        self.restored = None
        self.sync_handle = FakeHandle()
        self.sync_listener = None

    async def login(self, user, password, device_name, device_id):
        self.logins.append((user, device_id))

    async def restore_session(self, session):
        self.restored = session

    def session(self):
        return sdk.Session(
            access_token="token",
            refresh_token=None,
            user_id=BOT,
            device_id="DEV",
            homeserver_url="https://example.org",
            oauth_data=None,
            sliding_sync_version=sdk.SlidingSyncVersion.NONE,
        )

    async def sync_once_v2(self, settings):
        pass

    def sync_v2(self, settings, listener):
        self.sync_listener = listener
        return self.sync_handle

    def encryption(self):
        return self.encryption_obj

    def user_id(self):
        return BOT

    def device_id(self):
        return "DEV"

    def rooms(self):
        return list(self._rooms.values())

    def get_room(self, room_id):
        return self._rooms.get(room_id)

    async def get_profile(self, user_id):
        return type("Profile", (), {"display_name": "Alice", "avatar_url": None})()


class FakeBuilder:
    client = None

    def __getattr__(self, name):
        return lambda *args: self

    async def build(self):
        return FakeBuilder.client


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient([FakeRoom()])
    FakeBuilder.client = fake
    monkeypatch.setattr(sdk, "ClientBuilder", FakeBuilder)
    return fake


def backend_for(tmp_path, **config):
    return MatrixE2EEBackend(
        config=MatrixConfig(homeserver="https://example.org", user_id=BOT, store_path=str(tmp_path / "store"), **config),
    )


async def settle():
    for _ in range(3):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_password_login_saves_session_and_restart_restores_it(client, tmp_path):
    backend = backend_for(tmp_path, password="pw", device_id="DEV")
    await backend.connect()
    assert client.logins == [(BOT, "DEV")]
    session_file = tmp_path / "store" / "session.json"
    assert session_file.stat().st_mode & 0o777 == 0o600
    assert json.loads(session_file.read_text())["sliding_sync_version"] == "NONE"
    await backend.disconnect()
    assert client.sync_handle.cancelled

    restarted = backend_for(tmp_path, password="pw", device_id="DEV")
    await restarted.connect()
    assert client.logins == [(BOT, "DEV")]
    assert client.restored.access_token == "token"
    await restarted.disconnect()


@pytest.mark.asyncio
async def test_connect_requires_store_path(client):
    backend = MatrixE2EEBackend(config=MatrixConfig(homeserver="https://example.org", user_id=BOT, password="pw"))
    with pytest.raises(ValueError, match="store_path"):
        await backend.connect()


@pytest.mark.asyncio
async def test_unverified_device_recovers_with_key(client, tmp_path):
    client.encryption_obj.verified = False
    backend = backend_for(tmp_path, password="pw", recovery_key="key words")
    await backend.connect()
    assert client.encryption_obj.recovered_with == "key words"
    await backend.disconnect()


@pytest.mark.asyncio
async def test_stream_yields_decrypted_messages(client, tmp_path):
    backend = backend_for(tmp_path, password="pw")
    await backend.connect()
    timeline = client.get_room(ROOM).timeline_obj
    received = []

    async def consume():
        async for message in backend.stream_messages():
            received.append(message)

    task = asyncio.ensure_future(consume())
    await settle()
    undecrypted = item("$late", raw={"type": "m.room.encrypted", "event_id": "$late", "sender": "@alice:example.org", "content": {}})
    timeline.listener.on_update(
        [
            sdk.TimelineDiff.RESET(values=[item("$old", timestamp=0)]),
            sdk.TimelineDiff.PUSH_BACK(value=item("$own", sender=BOT)),
            sdk.TimelineDiff.PUSH_BACK(value=undecrypted),
            sdk.TimelineDiff.PUSH_BACK(value=item("$new", body="hello bot")),
            sdk.TimelineDiff.SET(index=3, value=item("$new", body="hello bot")),
        ]
    )
    await settle()
    timeline.listener.on_update([sdk.TimelineDiff.SET(index=2, value=item("$late", body="decrypted later"))])
    await settle()
    task.cancel()
    await settle()

    assert [message.id for message in received] == ["$new", "$late"]
    assert received[0].content == "hello bot"
    assert [user.id for user in received[0].mentions] == [BOT]
    assert received[0].channel_id == ROOM
    await backend.disconnect()


@pytest.mark.asyncio
async def test_send_reply_edit_and_delete_use_event_ids(client, tmp_path):
    backend = backend_for(tmp_path, password="pw")
    await backend.connect()
    room = client.get_room(ROOM)

    sent = await backend.send_message(ROOM, 'hi <span class="mention" data-user-id="@alice:example.org">Alice</span>')
    assert sent.id == "$sent1"
    assert sent.content == "hi Alice"
    assert "matrix.to/#/@alice:example.org" in sent.formatted_content

    reply = await backend.send_message(ROOM, "plain", reply_to="$question", formatted=False)
    assert reply.id == "$sent2"
    assert reply.reference.message_id == "$question"
    assert room.timeline_obj.sent[1][0] == "reply"
    assert room.timeline_obj.sent[1][2] == "$question"

    edited = await backend.edit_message(sent, "changed")
    assert edited.id == "$sent1"
    assert edited.replacement_event_id == "$sent3"
    assert room.edits == ["$sent1"]

    await backend.delete_message(sent)
    assert room.redactions == ["$sent1"]
    await backend.disconnect()


@pytest.mark.asyncio
async def test_fetch_messages_paginates_back(client, tmp_path):
    backend = backend_for(tmp_path, password="pw")
    await backend.connect()
    timeline = client.get_room(ROOM).timeline_obj
    timeline.listener.on_update([sdk.TimelineDiff.RESET(values=[item("$3", body="three", timestamp=3)])])
    timeline.history = [item("$1", body="one", timestamp=1), item("$2", body="two", timestamp=2)]
    await settle()

    messages = await backend.fetch_messages(ROOM, limit=3)
    assert [message.content for message in messages] == ["three", "two", "one"]
    channel = await backend.fetch_channel(ROOM)
    assert channel.encrypted
    user = await backend.fetch_user("@alice:example.org")
    assert user.display_name == "Alice"
    await backend.disconnect()


@pytest.mark.asyncio
async def test_rooms_joined_later_are_attached(client, tmp_path):
    backend = backend_for(tmp_path, password="pw")
    await backend.connect()
    client._rooms["!new:example.org"] = FakeRoom("!new:example.org", encrypted=False)
    rooms = sdk.SyncResponseRoomsV2(invited=[], joined=["!new:example.org"], left=[], knocked=[])
    client.sync_listener.on_update(sdk.SyncResponseV2(next_batch="b", rooms=rooms))
    await settle()
    channel = await backend.fetch_channel("!new:example.org")
    assert channel is not None and not channel.encrypted
    await backend.disconnect()


def test_apply_diff_tracks_timeline():
    items = []
    for diff in [
        sdk.TimelineDiff.RESET(values=["b"]),
        sdk.TimelineDiff.APPEND(values=["c", "d"]),
        sdk.TimelineDiff.PUSH_FRONT(value="a"),
        sdk.TimelineDiff.PUSH_BACK(value="e"),
        sdk.TimelineDiff.INSERT(index=1, value="x"),
        sdk.TimelineDiff.SET(index=1, value="y"),
        sdk.TimelineDiff.REMOVE(index=1),
        sdk.TimelineDiff.POP_FRONT(),
        sdk.TimelineDiff.POP_BACK(),
    ]:
        _apply_diff(items, diff)
    assert items == ["b", "c", "d"]
    _apply_diff(items, sdk.TimelineDiff.TRUNCATE(length=1))
    assert items == ["b"]
    _apply_diff(items, sdk.TimelineDiff.CLEAR())
    assert items == []
