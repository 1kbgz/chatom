"""Focused tests for Zulip models, API mapping, and mock backend."""

import base64
import sys
import types
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr, ValidationError

from chatom import AttachmentDownloadLimitError
from chatom.base import Attachment, Channel, ChannelType, Message, Presence, PresenceStatus, Thread, User
from chatom.base.conversion import get_backend_type
from chatom.zulip import (
    MockZulipBackend,
    ZulipBackend,
    ZulipChannel,
    ZulipConfig,
    ZulipMessage,
    ZulipPresence,
    ZulipPresenceStatus,
    ZulipUser,
    mention_channel,
    mention_user,
)


class FakeZulipClient:
    def __init__(self) -> None:
        self.last_message_request = None
        self.sent_request = None
        self.deregistered = None

    def get_profile(self):
        return {
            "result": "success",
            "user_id": 1,
            "full_name": "Chatom Bot",
            "email": "chatom@example.com",
            "is_bot": True,
        }

    def get_user_by_id(self, user_id):
        return {
            "result": "success",
            "user": {"user_id": user_id, "full_name": "Iago", "email": "iago@example.com"},
        }

    def get_users(self):
        return {
            "result": "success",
            "members": [
                {"user_id": 2, "full_name": "Iago", "email": "iago@example.com"},
                {"user_id": 3, "full_name": "Cordelia", "email": "cordelia@example.com"},
            ],
        }

    def get_streams(self, **kwargs):
        return {
            "result": "success",
            "streams": [
                {"stream_id": 7, "name": "Denmark", "description": "Court news", "invite_only": False},
                {"stream_id": 8, "name": "Secret", "description": "", "invite_only": True},
            ],
        }

    def get_messages(self, request):
        self.last_message_request = request
        return {
            "result": "success",
            "messages": [
                {
                    "id": 40,
                    "type": "stream",
                    "stream_id": 7,
                    "display_recipient": "Denmark",
                    "subject": "Castle",
                    "content": "First",
                    "content_type": "text/x-markdown",
                    "sender_id": 2,
                    "sender_full_name": "Iago",
                    "sender_email": "iago@example.com",
                    "timestamp": 1700000000,
                },
                {
                    "id": 41,
                    "type": "stream",
                    "stream_id": 7,
                    "display_recipient": "Denmark",
                    "subject": "Castle",
                    "content": "Second",
                    "content_type": "text/x-markdown",
                    "sender_id": 3,
                    "sender_full_name": "Cordelia",
                    "sender_email": "cordelia@example.com",
                    "timestamp": 1700000001,
                },
            ],
        }

    def send_message(self, request):
        self.sent_request = request
        return {"result": "success", "id": 42}

    def register(self, event_types, narrow):
        return {"result": "success", "queue_id": "queue-1", "last_event_id": -1}

    def get_events(self, **kwargs):
        return {
            "result": "success",
            "events": [
                {
                    "id": 1,
                    "type": "message",
                    "message": {
                        "id": 43,
                        "type": "stream",
                        "stream_id": 7,
                        "display_recipient": "Denmark",
                        "subject": "Castle",
                        "content": "Live",
                        "content_type": "text/html",
                        "sender_id": 2,
                        "sender_full_name": "Iago",
                        "sender_email": "iago@example.com",
                        "timestamp": 1700000002,
                    },
                }
            ],
        }

    def deregister(self, queue_id):
        self.deregistered = queue_id
        return {"result": "success"}


@pytest.fixture
def backend():
    instance = ZulipBackend(config=ZulipConfig(site="https://example.zulipchat.com", email="chatom@example.com", api_key="secret"))
    instance._client = FakeZulipClient()
    return instance


def test_models_mentions_and_local_conversion_registration():
    user = ZulipUser(id="2", name="Iago")
    channel = ZulipChannel(id="7", name="Denmark")

    assert mention_user(user) == "@**Iago|2**"
    assert mention_channel(channel) == "#**Denmark**"
    assert get_backend_type(User, "zulip") is ZulipUser
    assert get_backend_type(Channel, "zulip") is ZulipChannel
    assert get_backend_type(Message, "zulip") is ZulipMessage
    assert get_backend_type(Presence, "zulip") is ZulipPresence


def test_config_loads_api_key_file(tmp_path):
    key_file = tmp_path / "zulip.key"
    key_file.write_text("file-secret\n")
    assert ZulipConfig(api_key=str(key_file)).api_key_str == "file-secret"


@pytest.mark.asyncio
async def test_connect_and_lookup(backend):
    await backend.connect()

    assert backend.connected
    assert (await backend.get_bot_info()).id == "1"
    assert (await backend.fetch_user(handle="iago")).email == "iago@example.com"
    assert (await backend.fetch_channel(name="Secret")).is_private


@pytest.mark.asyncio
async def test_fetch_messages_maps_topics_to_threads(backend):
    await backend.connect()

    messages = await backend.fetch_messages("7", limit=2)

    assert [message.id for message in messages] == ["41", "40"]
    assert messages[0].thread == Thread(id="7:Castle", name="Castle", parent_channel=messages[0].channel)
    assert messages[0].topic == "Castle"
    assert backend._client.last_message_request["apply_markdown"] is False
    assert backend._client.last_message_request["narrow"] == [{"operator": "channel", "operand": 7}]


@pytest.mark.asyncio
async def test_send_message_uses_thread_topic(backend):
    await backend.connect()
    await backend.fetch_channel(id="7")

    message = await backend.send_message("7", "Status", thread=Thread(id="7:release", name="release"))

    assert backend._client.sent_request == {"type": "stream", "to": 7, "topic": "release", "content": "Status"}
    assert message.id == "42"
    assert message.thread.id == "7:release"


@pytest.mark.asyncio
async def test_stream_messages_uses_event_queue(backend):
    await backend.connect()
    stream = backend.stream_messages(channel="7")

    message = await anext(stream)
    await stream.aclose()

    assert message.content == "Live"
    assert message.formatted_content == "Live"
    assert message.thread.id == "7:Castle"
    assert backend._client.deregistered == "queue-1"


@pytest.mark.asyncio
async def test_mock_backend_preserves_topic_and_tracks_operations():
    backend = MockZulipBackend()
    await backend.connect()
    backend.add_mock_user("2", "Iago", "iago@example.com")
    backend.add_mock_channel("7", "Denmark")
    backend.add_mock_message("7", "2", "Earlier", topic="Castle", timestamp=datetime.now(UTC))

    sent = await backend.send_message("7", "Later", topic="Castle")
    await backend.add_reaction(sent, ":thumbsup:")
    await backend.delete_message(sent)

    assert sent.thread.id == "7:Castle"
    assert backend.sent_messages == [sent]
    assert backend.added_reactions == [(sent.id, "thumbsup")]
    assert backend.deleted_messages == [sent.id]
    assert [message.content for message in await backend.fetch_messages("7")] == ["Earlier"]


class PagingZulipClient(FakeZulipClient):
    """Fake client that serves channel history one message per request."""

    def __init__(self, total: int) -> None:
        super().__init__()
        self.requests: list[dict] = []
        self._by_id = {
            message_id: {
                "id": message_id,
                "type": "stream",
                "stream_id": 7,
                "display_recipient": "Denmark",
                "subject": "Castle",
                "content": f"message {message_id}",
                "content_type": "text/x-markdown",
                "sender_id": 2,
                "sender_full_name": "Iago",
                "sender_email": "iago@example.com",
                "timestamp": 1_700_000_000 + message_id,
            }
            for message_id in range(1, total + 1)
        }

    def get_messages(self, request):
        self.requests.append(dict(request))
        anchor = request["anchor"]
        newest = max(self._by_id)
        anchor_id = newest if anchor == "newest" else int(anchor)
        if request["num_after"]:
            candidates = sorted(mid for mid in self._by_id if mid >= anchor_id)
        else:
            candidates = sorted((mid for mid in self._by_id if mid <= anchor_id), reverse=True)
        # One message per page, so a correct implementation has to keep paging.
        page = candidates[:1]
        return {
            "result": "success",
            "messages": [self._by_id[mid] for mid in page],
            "found_oldest": not request["num_after"] and min(self._by_id) in page,
            "found_newest": bool(request["num_after"]) and newest in page,
        }


@pytest.mark.asyncio
async def test_fetch_messages_pages_until_limit_is_satisfied():
    """History must page rather than return one request's worth.

    Regression: a single get_messages call was filtered client-side, so
    fewer than `limit` messages came back even when more existed.
    """
    instance = ZulipBackend(config=ZulipConfig(site="https://example.zulipchat.com", email="chatom@example.com", api_key="secret"))
    instance._client = PagingZulipClient(total=5)
    instance.connected = True

    messages = await instance.fetch_messages("7", limit=3)

    assert [message.id for message in messages] == ["5", "4", "3"]
    assert len(instance._client.requests) >= 3


@pytest.mark.asyncio
async def test_fetch_messages_stops_at_oldest_message():
    """Paging terminates on found_oldest instead of spinning."""
    instance = ZulipBackend(config=ZulipConfig(site="https://example.zulipchat.com", email="chatom@example.com", api_key="secret"))
    instance._client = PagingZulipClient(total=2)
    instance.connected = True

    messages = await instance.fetch_messages("7", limit=50)

    assert [message.id for message in messages] == ["2", "1"]


@pytest.mark.asyncio
async def test_upload_file_posts_upload_then_links_it(backend):
    """FILES is declared, so upload_file must actually work."""
    uploaded = {}

    def upload_file(file_obj):
        uploaded["name"] = file_obj.name
        uploaded["data"] = file_obj.read()
        return {"result": "success", "uri": "/user_uploads/1/ab/report.pdf"}

    backend._client.upload_file = upload_file
    backend.connected = True

    await backend.upload_file("7", b"PDF-BYTES", filename="report.pdf", content="Latest numbers")

    assert uploaded == {"name": "report.pdf", "data": b"PDF-BYTES"}
    assert backend._client.sent_request["content"] == "Latest numbers\n\n[report.pdf](/user_uploads/1/ab/report.pdf)"


@pytest.mark.asyncio
async def test_download_attachment_authenticates_relative_uri(backend, monkeypatch):
    """Zulip uploads are realm-relative and need the bot's credentials."""
    captured = {}

    async def fake_download(self, url, headers=None, max_bytes=None):
        captured["url"] = url
        captured["headers"] = headers
        return b"PDF-BYTES"

    monkeypatch.setattr(ZulipBackend, "_download_url", fake_download)
    backend.connected = True

    data = await backend.download_attachment(Attachment(id="1", url="/user_uploads/1/ab/report.pdf"))

    assert data == b"PDF-BYTES"
    assert captured["url"] == "https://example.zulipchat.com/user_uploads/1/ab/report.pdf"
    expected = base64.b64encode(b"chatom@example.com:secret").decode()
    assert captured["headers"] == {"Authorization": f"Basic {expected}"}


class RecordingZulipClient(FakeZulipClient):
    """Fake client that records mutating calls and serves scripted presence."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, object]] = []
        self.presence_response: dict = {"result": "success", "presence": {}}
        self.register_args = None
        self.event_batches: list[list[dict]] | None = None
        self.event_kwargs: list[dict] = []

    def update_message(self, request):
        self.calls.append(("update_message", request))
        return {"result": "success"}

    def delete_message(self, message_id):
        self.calls.append(("delete_message", message_id))
        return {"result": "success"}

    def add_reaction(self, request):
        self.calls.append(("add_reaction", request))
        return {"result": "success"}

    def remove_reaction(self, request):
        self.calls.append(("remove_reaction", request))
        return {"result": "success"}

    def update_presence(self, request):
        self.calls.append(("update_presence", request))
        return {"result": "success"}

    def get_user_presence(self, email):
        self.calls.append(("get_user_presence", email))
        return self.presence_response

    def register(self, event_types, narrow):
        self.register_args = (event_types, narrow)
        return super().register(event_types, narrow)

    def get_events(self, **kwargs):
        if self.event_batches is None:
            return super().get_events(**kwargs)
        self.event_kwargs.append(kwargs)
        return {"result": "success", "events": self.event_batches.pop(0)}


def stream_event(event_id, message_id, *, stream_id=7, sender_id=2, event_type="message"):
    return {
        "id": event_id,
        "type": event_type,
        "message": {
            "id": message_id,
            "type": "stream",
            "stream_id": stream_id,
            "display_recipient": "Denmark",
            "subject": "Castle",
            "content": f"body {message_id}",
            "sender_id": sender_id,
            "sender_full_name": "Iago",
            "sender_email": "iago@example.com",
        },
    }


@pytest.fixture
def recording(backend):
    backend._client = RecordingZulipClient()
    return backend


class FakeZulipModule(types.ModuleType):
    """Stand-in for the ``zulip`` package that records Client construction."""

    def __init__(self) -> None:
        super().__init__("zulip")
        self.client_kwargs: list[dict] = []
        module = self

        class Client(RecordingZulipClient):
            def __init__(self, **kwargs) -> None:
                super().__init__()
                module.client_kwargs.append(kwargs)

        self.Client = Client


@pytest.fixture
def fake_zulip(monkeypatch):
    module = FakeZulipModule()
    monkeypatch.setitem(sys.modules, "zulip", module)
    return module


@pytest.mark.asyncio
async def test_connect_builds_client_from_explicit_credentials(fake_zulip):
    instance = ZulipBackend(
        config=ZulipConfig(site="https://z.example.com", email="bot@example.com", api_key="k", client_name="tester", insecure=True)
    )

    await instance.connect()

    assert fake_zulip.client_kwargs == [
        {"site": "https://z.example.com", "email": "bot@example.com", "api_key": "k", "client": "tester", "insecure": True}
    ]
    assert instance.connected
    assert instance._bot_user_id == "1"
    assert instance.users.get_by_id("1").name == "Chatom Bot"


@pytest.mark.asyncio
async def test_connect_prefers_config_file(fake_zulip):
    instance = ZulipBackend(config=ZulipConfig(config_file="/etc/zuliprc", site="ignored", email="ignored", api_key="ignored"))

    await instance.connect()

    assert fake_zulip.client_kwargs == [{"config_file": "/etc/zuliprc", "client": "chatom"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [{"email": "e", "api_key": "k"}, {"site": "s", "api_key": "k"}, {"site": "s", "email": "e"}])
async def test_connect_requires_all_credentials_without_config_file(fake_zulip, config):
    instance = ZulipBackend(config=ZulipConfig(**config))

    with pytest.raises(ValueError, match="site, email, and api_key are required"):
        await instance.connect()

    assert fake_zulip.client_kwargs == []
    assert not instance.connected


@pytest.mark.asyncio
async def test_connect_without_zulip_package_raises_helpful_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "zulip", None)
    instance = ZulipBackend(config=ZulipConfig(site="s", email="e", api_key="k"))

    with pytest.raises(ImportError, match="pip install zulip"):
        await instance.connect()


@pytest.mark.asyncio
async def test_disconnect_clears_client_and_bot_state(backend):
    await backend.connect()

    await backend.disconnect()

    assert not backend.connected
    assert backend._client is None
    assert backend._bot_user is None
    assert backend._bot_user_id is None
    with pytest.raises(ConnectionError, match="Not connected to Zulip"):
        await backend.get_bot_info()


@pytest.mark.asyncio
async def test_operations_require_connection(backend):
    for call in (
        lambda: backend.fetch_user(id="2"),
        lambda: backend.fetch_channel(id="7"),
        lambda: backend.fetch_messages("7"),
        lambda: backend.send_message("7", "hi"),
        lambda: backend.edit_message("1", "hi"),
        lambda: backend.delete_message("1"),
        lambda: backend.add_reaction("1", "smile"),
        lambda: backend.remove_reaction("1", "smile"),
        lambda: backend.get_presence("2"),
        lambda: backend.set_presence("online"),
        lambda: backend.upload_file("7", b"x"),
    ):
        with pytest.raises(ConnectionError, match="Not connected to Zulip"):
            await call()
    with pytest.raises(ConnectionError):
        await anext(backend.stream_messages())


@pytest.mark.asyncio
async def test_api_errors_and_malformed_responses_raise(recording):
    recording.connected = True
    recording._client.delete_message = lambda message_id: {"result": "error", "msg": "Message not found"}
    with pytest.raises(RuntimeError, match="Zulip API error: Message not found"):
        await recording.delete_message("5")

    recording._client.delete_message = lambda message_id: {"result": "error"}
    with pytest.raises(RuntimeError, match="Zulip API error: unknown error"):
        await recording.delete_message("5")

    recording._client.delete_message = lambda message_id: ["not", "a", "dict"]
    with pytest.raises(TypeError, match="non-object response"):
        await recording.delete_message("5")


@pytest.mark.asyncio
async def test_fetch_user_by_id_caches_lookup(backend):
    await backend.connect()
    calls = []
    original = backend._client.get_user_by_id
    backend._client.get_user_by_id = lambda user_id: calls.append(user_id) or original(user_id)

    first = await backend.fetch_user(id="9")
    second = await backend.fetch_user("9")

    assert (first.id, first.name, first.handle) == ("9", "Iago", "iago")
    assert second is first
    assert calls == [9]


@pytest.mark.asyncio
async def test_fetch_user_accepts_user_objects(backend):
    await backend.connect()

    from_zulip_user = await backend.fetch_user(ZulipUser(id="4", name="x"))
    from_generic_user = await backend.fetch_user(User(id="5", name="y"))

    assert from_zulip_user.id == "4"
    assert from_generic_user.id == "5"


@pytest.mark.asyncio
async def test_fetch_user_by_id_missing_returns_none(backend):
    await backend.connect()
    backend._client.get_user_by_id = lambda user_id: {"result": "success"}

    assert await backend.fetch_user(id="99") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_id"),
    [
        ({"email": "CORDELIA@example.com"}, "3"),
        ({"handle": "@Cordelia"}, "3"),
        ({"name": "iago"}, "2"),
        ({"name": "nobody"}, None),
        ({}, None),
    ],
)
async def test_fetch_user_scans_directory(backend, kwargs, expected_id):
    await backend.connect()

    user = await backend.fetch_user(**kwargs)

    assert (user.id if user else None) == expected_id


@pytest.mark.asyncio
async def test_fetch_user_scan_caches_every_member_seen(backend):
    await backend.connect()

    await backend.fetch_user(name="nobody")

    assert backend.users.get_by_id("2").name == "Iago"
    assert backend.users.get_by_id("3").name == "Cordelia"


@pytest.mark.asyncio
async def test_fetch_channel_variants(backend):
    await backend.connect()

    by_object = await backend.fetch_channel(Channel(id="8"))
    by_name_object = await backend.fetch_channel(Channel(name="denmark"))
    by_string = await backend.fetch_channel("7")
    missing = await backend.fetch_channel(id="404")

    assert by_object.name == "Secret"
    assert by_name_object.id == "7"
    assert by_string == await backend.fetch_channel(id="7")
    assert missing is None
    assert await backend.fetch_channel() is None


@pytest.mark.asyncio
async def test_fetch_channel_uses_cache_without_api_call(backend):
    await backend.connect()
    await backend.fetch_channel(id="7")
    backend._client.get_streams = lambda **kwargs: pytest.fail("cache should satisfy lookup")

    assert (await backend.fetch_channel("7")).name == "Denmark"


@pytest.mark.asyncio
async def test_fetch_messages_non_numeric_channel_uses_name_narrow(backend):
    await backend.connect()

    await backend.fetch_messages("general", limit=1)

    assert backend._client.last_message_request["narrow"] == [{"operator": "channel", "operand": "general"}]


def paging_backend(total=6):
    instance = ZulipBackend(config=ZulipConfig(site="https://example.zulipchat.com", email="chatom@example.com", api_key="secret"))
    instance._client = PagingZulipClient(total=total)
    instance.connected = True
    return instance


@pytest.mark.asyncio
async def test_fetch_messages_before_string_pages_backwards():
    instance = paging_backend()

    messages = await instance.fetch_messages("7", limit=2, before="4")

    assert [message.id for message in messages] == ["3", "2"]
    first = instance._client.requests[0]
    assert first["anchor"] == "4"
    assert first["include_anchor"] is False
    assert first["num_before"] == 2
    assert first["num_after"] == 0


@pytest.mark.asyncio
async def test_fetch_messages_after_message_pages_forwards():
    instance = paging_backend()

    messages = await instance.fetch_messages("7", limit=2, after=Message(id="3"))

    assert [message.id for message in messages] == ["5", "4"]
    first = instance._client.requests[0]
    assert (first["anchor"], first["num_before"], first["num_after"]) == ("3", 0, 2)


@pytest.mark.asyncio
async def test_fetch_messages_filters_by_datetime_bounds():
    instance = paging_backend()
    after = datetime.fromtimestamp(1_700_000_004, UTC)
    before = datetime.fromtimestamp(1_700_000_003, UTC).replace(tzinfo=None)

    newer = await instance.fetch_messages("7", limit=10, after=after)
    older = await instance.fetch_messages("7", limit=10, before=before)

    assert [message.id for message in newer] == ["6", "5", "4"]
    assert [message.id for message in older] == ["3", "2", "1"]


@pytest.mark.asyncio
async def test_fetch_messages_stops_when_page_has_no_message_ids():
    instance = paging_backend()
    instance._client.get_messages = lambda request: {"result": "success", "messages": [{"type": "stream", "stream_id": 7, "content": "x"}]}

    messages = await instance.fetch_messages("7", limit=5)

    assert [message.content for message in messages] == ["x"]


@pytest.mark.asyncio
async def test_fetch_messages_stops_when_anchor_does_not_advance():
    instance = paging_backend()
    requests = []

    def repeating_page(request):
        requests.append(request["anchor"])
        return {"result": "success", "messages": [instance._client._by_id[5]]}

    instance._client.get_messages = repeating_page

    messages = await instance.fetch_messages("7", limit=3)

    assert [message.id for message in messages] == ["5"]
    assert requests == ["newest", 4]


@pytest.mark.asyncio
async def test_message_from_api_maps_direct_message_and_reactions(backend):
    await backend.connect()
    data = {
        "id": 9,
        "type": "private",
        "display_recipient": [
            {"id": 1, "full_name": "Chatom Bot", "email": "chatom@example.com"},
            {"id": 2, "full_name": "Iago", "email": "iago@example.com"},
        ],
        "content": "<p>hi</p>",
        "content_type": "text/html",
        "sender_id": 2,
        "sender_full_name": "Iago",
        "sender_email": "iago@example.com",
        "timestamp": 1700000000,
        "last_edit_timestamp": 1700000100,
        "recipient_id": 12,
        "client": "website",
        "flags": ["read"],
        "reactions": [
            {"emoji_name": "smile", "emoji_code": "1f642", "reaction_type": "unicode_emoji", "user_id": 2},
            {"emoji_name": "smile", "emoji_code": "1f642", "reaction_type": "unicode_emoji", "user_id": 3},
            {"emoji_name": "party", "emoji_code": "9", "reaction_type": "realm_emoji", "user_id": 2},
        ],
    }

    message = backend._message_from_api(data)

    assert message.channel.id == "dm:2"
    assert message.channel.channel_type == ChannelType.DIRECT
    assert message.channel.name == "Iago"
    assert message.thread is None
    assert message.formatted_content == "<p>hi</p>"
    assert message.is_edited
    assert (message.recipient_id, message.client, message.flags) == (12, "website", ["read"])
    assert message.created_at == datetime.fromtimestamp(1700000000, UTC)
    smile, party = message.reactions
    assert (smile.emoji.name, smile.emoji.id, smile.emoji.is_custom, smile.count) == ("smile", "1f642", False, 2)
    assert [user.id for user in smile.users] == ["2", "3"]
    assert (party.emoji.name, party.emoji.is_custom, party.count) == ("party", True, 1)
    assert len(message.zulip_reactions) == 3


@pytest.mark.asyncio
async def test_message_from_api_group_message_excludes_bot_and_sorts_ids(backend):
    await backend.connect()
    data = {
        "id": 10,
        "type": "private",
        "display_recipient": [
            {"id": 3, "full_name": "Cordelia", "email": "c@example.com"},
            {"id": 1, "full_name": "Chatom Bot", "email": "chatom@example.com"},
            {"id": 2, "full_name": "Iago", "email": "i@example.com"},
        ],
        "sender_id": 3,
    }

    message = backend._message_from_api(data)

    assert message.channel.id == "dm:2,3"
    assert message.channel.channel_type == ChannelType.GROUP
    assert message.channel.name == "Cordelia, Iago"
    assert message.created_at is None
    assert not message.is_edited
    assert message.formatted_content == ""


@pytest.mark.asyncio
async def test_message_from_api_tolerates_malformed_private_recipient(backend):
    message = backend._message_from_api({"id": 11, "type": "private", "display_recipient": "oops", "sender_id": 2})

    assert message.channel.id == "dm:"
    assert message.thread is None


@pytest.mark.asyncio
async def test_upload_file_requires_returned_uri(recording):
    recording.connected = True
    recording._client.upload_file = lambda file_obj: {"result": "success"}

    with pytest.raises(RuntimeError, match="did not return a URI"):
        await recording.upload_file("7", b"data", filename="a.txt")

    assert recording._client.sent_request is None


@pytest.mark.asyncio
async def test_upload_file_without_content_posts_titled_link_to_topic(recording):
    recording.connected = True
    recording._client.upload_file = lambda file_obj: {"result": "success", "url": "/user_uploads/x"}

    await recording.upload_file("7", b"data", filename="a.txt", title="Notes", topic="files")

    assert recording._client.sent_request == {"type": "stream", "to": 7, "topic": "files", "content": "[Notes](/user_uploads/x)"}


@pytest.mark.asyncio
async def test_download_attachment_uses_inline_data_and_enforces_limit(recording):
    attachment = Attachment(id="1", data=b"abcdef")

    assert await recording.download_attachment(attachment) == b"abcdef"
    with pytest.raises(AttachmentDownloadLimitError):
        await recording.download_attachment(attachment, max_bytes=3)


@pytest.mark.asyncio
async def test_download_attachment_without_data_or_url_is_unsupported(recording):
    with pytest.raises(NotImplementedError, match="no data or url"):
        await recording.download_attachment(Attachment(id="1", url="  "))


@pytest.mark.asyncio
async def test_download_attachment_keeps_absolute_url_and_forwards_limit(recording, monkeypatch):
    captured = {}

    async def fake_download(self, url, headers=None, max_bytes=None):
        captured.update(url=url, max_bytes=max_bytes)
        return b"ok"

    monkeypatch.setattr(ZulipBackend, "_download_url", fake_download)

    data = await recording.download_attachment(Attachment(id="1", url="https://cdn.example.com/f.png"), max_bytes=10)

    assert data == b"ok"
    assert captured == {"url": "https://cdn.example.com/f.png", "max_bytes": 10}


@pytest.mark.parametrize(
    ("thread", "expected"),
    [
        (Thread(id="7:release", name="release"), "release"),
        (Thread(id="7:release"), "release"),
        (Thread(id="plain"), "plain"),
        (Message(id="1", thread=Thread(id="7:a", name="from-thread")), "from-thread"),
        (ZulipMessage(id="1", topic="from-topic"), "from-topic"),
        (Message(id="1"), None),
        ("7:typed", "typed"),
        ("bare", "bare"),
        (None, None),
    ],
)
def test_topic_from_thread(thread, expected):
    assert ZulipBackend._topic_from_thread(thread) == expected


@pytest.mark.asyncio
async def test_send_message_to_direct_channel_object_uses_user_ids_or_emails(backend):
    await backend.connect()
    channel = Channel(id="dm:2", channel_type=ChannelType.GROUP, users=[User(id="2"), User(id="ext", email="ext@example.com")])

    message = await backend.send_message(channel, "hello")

    assert backend._client.sent_request == {"type": "private", "to": [2, "ext@example.com"], "content": "hello"}
    assert message.channel.id == "dm:2"
    assert message.thread is None
    assert message.topic == ""
    assert message.author.id == "1"


@pytest.mark.asyncio
async def test_send_message_to_dm_channel_id_string(backend):
    await backend.connect()

    message = await backend.send_message("dm:2,3", "hello")

    assert backend._client.sent_request == {"type": "private", "to": [2, 3], "content": "hello"}
    assert message.channel.id == "dm:2,3"
    assert message.channel.channel_type == ChannelType.GROUP
    assert message.thread is None


@pytest.mark.asyncio
async def test_send_message_defaults_topic_and_accepts_message_id_key(backend):
    await backend.connect()
    backend._client.send_message = lambda request: {"result": "success", "message_id": 77}

    message = await backend.send_message("999", "hi")

    assert message.id == "77"
    assert message.topic == "chatom"
    assert message.channel.id == "999"
    assert message.thread.id == "999:chatom"


@pytest.mark.asyncio
async def test_send_message_topic_precedence(backend):
    await backend.connect()
    reply = ZulipMessage(id="1", topic="reply-topic", thread=Thread(id="7:reply-topic", name="reply-topic"))

    await backend.send_message("7", "a", reply_to=reply)
    assert backend._client.sent_request["topic"] == "reply-topic"

    await backend.send_message("7", "b", thread=Thread(id="7:thread-topic", name="thread-topic"), reply_to=reply)
    assert backend._client.sent_request["topic"] == "thread-topic"

    await backend.send_message("7", "c", topic="explicit", thread=Thread(id="7:thread-topic", name="thread-topic"))
    assert backend._client.sent_request["topic"] == "explicit"


@pytest.mark.asyncio
async def test_send_message_to_named_channel_object_keeps_string_destination(backend):
    await backend.connect()
    channel = ZulipChannel(id="general", name="general")

    message = await backend.send_message(channel, "hi")

    assert backend._client.sent_request["to"] == "general"
    assert message.channel is channel


@pytest.mark.asyncio
async def test_edit_message_posts_update_and_preserves_message_context(recording):
    await recording.connect()
    original = await recording.fetch_messages("7", limit=1)

    edited = await recording.edit_message(original[0], "new text", topic="moved")

    assert recording._client.calls == [("update_message", {"message_id": 41, "content": "new text", "topic": "moved"})]
    assert edited.id == "41"
    assert edited.content == "new text"
    assert edited.is_edited
    assert edited.channel.id == "7"
    assert edited.thread == original[0].thread
    assert edited.topic == "Castle"
    assert edited.created_at == original[0].created_at


@pytest.mark.asyncio
async def test_edit_message_by_id_resolves_channel_argument(recording):
    recording.connected = True

    with_string = await recording.edit_message("5", "x", channel="7")
    with_channel = await recording.edit_message("6", "y", channel=Channel(id="8", name="Secret"))
    bare = await recording.edit_message("7", "z")

    assert [call[1]["message_id"] for call in recording._client.calls] == [5, 6, 7]
    assert (with_string.channel.id, with_string.thread, with_string.topic) == ("7", None, "")
    assert with_channel.channel.id == "8"
    assert bare.channel is None


@pytest.mark.asyncio
async def test_delete_and_reactions_call_client_with_normalised_ids(recording):
    recording.connected = True
    message = Message(id="12")

    await recording.delete_message(message)
    await recording.delete_message("13")
    await recording.add_reaction(message, ":thumbsup:")
    await recording.remove_reaction("12", ":thumbsup:")

    assert recording._client.calls == [
        ("delete_message", 12),
        ("delete_message", 13),
        ("add_reaction", {"message_id": 12, "emoji_name": "thumbsup"}),
        ("remove_reaction", {"message_id": 12, "emoji_name": "thumbsup"}),
    ]


@pytest.mark.asyncio
async def test_get_presence_prefers_aggregated_entry(recording):
    await recording.connect()
    recording._client.presence_response = {
        "result": "success",
        "presence": {
            "website": {"status": "idle", "timestamp": 1700000500},
            "aggregated": {"status": "active", "timestamp": 1700000000},
        },
    }

    presence = await recording.get_presence("2")

    assert recording._client.calls == [("get_user_presence", "iago@example.com")]
    assert presence.user.id == "2"
    assert presence.status == PresenceStatus.ONLINE
    assert presence.zulip_status == ZulipPresenceStatus.ACTIVE
    assert presence.client == "aggregated"
    assert presence.last_seen == datetime.fromtimestamp(1700000000, UTC)


@pytest.mark.asyncio
async def test_get_presence_without_aggregate_uses_latest_client(recording):
    await recording.connect()
    recording._client.presence_response = {
        "result": "success",
        "presence": {"web": {"status": "active", "timestamp": 10}, "mobile": {"status": "idle", "timestamp": 20}},
    }

    presence = await recording.get_presence(User(id="2", name="Iago", email="iago@example.com"))

    assert presence.client == "mobile"
    assert presence.status == PresenceStatus.IDLE


@pytest.mark.asyncio
async def test_get_presence_unknown_or_missing_status_is_offline(recording):
    await recording.connect()
    user = User(id="2", name="Iago", email="iago@example.com")

    recording._client.presence_response = {"result": "success", "presence": {"aggregated": {"status": "weird"}}}
    unknown = await recording.get_presence(user)
    recording._client.presence_response = {"result": "success", "presence": {}}
    empty = await recording.get_presence(user)

    assert (unknown.zulip_status, unknown.status, unknown.last_seen) == (ZulipPresenceStatus.OFFLINE, PresenceStatus.OFFLINE, None)
    assert (empty.zulip_status, empty.client, empty.last_seen) == (ZulipPresenceStatus.OFFLINE, "aggregated", None)


@pytest.mark.asyncio
async def test_get_presence_returns_none_without_email_or_user(recording):
    await recording.connect()

    assert await recording.get_presence(User(id="5", name="No Email")) is None
    recording._client.get_user_by_id = lambda user_id: {"result": "success"}
    assert await recording.get_presence("404") is None
    assert recording._client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "native"),
    [("online", "active"), ("idle", "idle"), ("dnd", "idle"), ("not-a-status", "idle")],
)
async def test_set_presence_maps_to_native_status(recording, status, native):
    recording.connected = True

    await recording.set_presence(status, status_text="ignored")

    assert recording._client.calls == [("update_presence", {"status": native, "ping_only": False, "new_user_input": True})]


@pytest.mark.asyncio
async def test_stream_messages_filters_events_and_advances_cursor(recording):
    await recording.connect()
    recording._client.event_batches = [
        [
            {"id": 1, "type": "heartbeat"},
            stream_event(2, 50, stream_id=9),
            stream_event(3, 51, sender_id=1),
            stream_event(4, 52),
        ],
        [stream_event(5, 53)],
    ]
    stream = recording.stream_messages(channel="7")

    first = await anext(stream)
    second = await anext(stream)
    await stream.aclose()

    assert (first.id, second.id) == ("52", "53")
    assert recording._client.register_args == (["message"], [["stream", "Denmark"]])
    assert [kwargs["last_event_id"] for kwargs in recording._client.event_kwargs] == [-1, 4]
    assert recording._client.deregistered == "queue-1"


@pytest.mark.asyncio
async def test_stream_messages_can_include_own_messages_across_all_channels(recording):
    await recording.connect()
    recording._client.event_batches = [[stream_event(1, 60, stream_id=9, sender_id=1)]]
    stream = recording.stream_messages(skip_own=False)

    message = await anext(stream)
    await stream.aclose()

    assert message.id == "60"
    assert message.author.id == "1"
    assert recording._client.register_args == (["message"], [])


@pytest.mark.asyncio
async def test_stream_messages_tolerates_client_without_deregister(recording):
    await recording.connect()
    recording._client.deregister = None
    stream = recording.stream_messages(channel="7")

    await anext(stream)
    await stream.aclose()

    assert recording._client.deregistered is None


def test_config_api_key_validation(tmp_path):
    assert ZulipConfig(api_key=None).api_key_str == ""
    assert ZulipConfig(api_key=SecretStr("kept")).api_key_str == "kept"
    assert ZulipConfig(api_key="literal-key").api_key_str == "literal-key"
    assert ZulipConfig().api_key_str == ""
    with pytest.raises(ValidationError, match="api_key must be a string"):
        ZulipConfig(api_key=123)


@pytest.mark.parametrize(
    ("base", "native", "generic"),
    [
        (PresenceStatus.ONLINE, ZulipPresenceStatus.ACTIVE, PresenceStatus.ONLINE),
        (PresenceStatus.IDLE, ZulipPresenceStatus.IDLE, PresenceStatus.IDLE),
        (PresenceStatus.DND, ZulipPresenceStatus.IDLE, PresenceStatus.IDLE),
        (PresenceStatus.OFFLINE, ZulipPresenceStatus.OFFLINE, PresenceStatus.OFFLINE),
        (PresenceStatus.INVISIBLE, ZulipPresenceStatus.OFFLINE, PresenceStatus.OFFLINE),
    ],
)
def test_presence_status_conversions(base, native, generic):
    assert ZulipPresenceStatus.from_base(base) is native
    assert native.generic is generic


def test_message_subject_aliases_topic():
    assert ZulipMessage(id="1", topic="Castle").subject == "Castle"


@pytest.mark.asyncio
async def test_mock_backend_lookups_and_history_bounds():
    backend = MockZulipBackend()
    await backend.connect()
    backend.add_mock_user("2", "Iago", "iago@example.com")
    backend.add_mock_user("3", "Cordelia Smith")
    backend.add_mock_channel("7", "Denmark")
    backend.add_mock_channel("8", "Secret", invite_only=True)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    for index in range(1, 5):
        backend.add_mock_message("7", "2", f"m{index}", timestamp=base.replace(day=index))

    assert (await backend.fetch_user("2")).name == "Iago"
    assert (await backend.fetch_user(User(id="3"))).handle == "cordeliasmith"
    assert (await backend.fetch_user(email="IAGO@example.com")).id == "2"
    assert (await backend.fetch_user(handle="@iago")).id == "2"
    assert (await backend.fetch_user(name="cordelia smith")).id == "3"
    assert await backend.fetch_user(name="ghost") is None
    assert (await backend.fetch_channel(Channel(id="8"))).is_private
    assert (await backend.fetch_channel(name="DENMARK")).id == "7"
    assert await backend.fetch_channel(name="nowhere") is None
    assert await backend.fetch_channel() is None

    assert [m.content for m in await backend.fetch_messages("7")] == ["m4", "m3", "m2", "m1"]
    assert [m.content for m in await backend.fetch_messages(Channel(id="7"), limit=2)] == ["m4", "m3"]
    assert [m.content for m in await backend.fetch_messages("7", before="3")] == ["m2", "m1"]
    assert [m.content for m in await backend.fetch_messages("7", after="2")] == ["m4", "m3"]
    assert [m.content for m in await backend.fetch_messages("7", before=base.replace(day=2))] == ["m2", "m1"]
    assert [m.content for m in await backend.fetch_messages("7", after=base.replace(day=3))] == ["m4", "m3"]
    assert await backend.fetch_messages("unknown") == []


@pytest.mark.asyncio
async def test_mock_backend_edit_and_reaction_tracking():
    backend = MockZulipBackend()
    await backend.connect()
    backend.add_mock_channel("7", "Denmark")
    sent = await backend.send_message("7", "v1", thread=Thread(id="7:release", name="release"))

    edited = await backend.edit_message(sent.id, "v2")
    await backend.add_reaction(sent.id, ":tada:")
    await backend.remove_reaction(sent, ":tada:")

    assert edited.content == "v2"
    assert edited.is_edited
    assert sent.topic == "release"
    assert backend.added_reactions == [(sent.id, "tada")]
    assert backend._removed_reactions == [(sent.id, "tada")]
    with pytest.raises(RuntimeError, match="Message 999 not found"):
        await backend.edit_message("999", "nope")


@pytest.mark.asyncio
async def test_mock_backend_presence_round_trip():
    backend = MockZulipBackend()
    await backend.set_presence("online")
    assert await backend.get_presence("1") is None

    await backend.connect()
    await backend.set_presence("dnd", status_text="busy")
    presence = await backend.get_presence(User(id="1"))

    assert presence.status == PresenceStatus.DND
    assert presence.zulip_status == ZulipPresenceStatus.IDLE
    assert presence.status_text == "busy"
    assert await backend.get_presence("2") is None


@pytest.mark.asyncio
async def test_mock_backend_stream_filters_channel_and_own_messages():
    backend = MockZulipBackend()
    await backend.connect()
    backend.add_mock_user("2", "Iago")
    backend.add_mock_channel("7", "Denmark")
    backend.add_mock_channel("8", "Secret")
    await backend.queue_message(backend.add_mock_message("8", "2", "other channel"))
    await backend.queue_message(backend.add_mock_message("7", "1", "from bot"))
    await backend.queue_message(backend.add_mock_message("7", "2", "wanted"))
    stream = backend.stream_messages(channel=Channel(id="7"))

    message = await anext(stream)
    await stream.aclose()

    assert message.content == "wanted"

    await backend.queue_message(backend.add_mock_message("7", "1", "own again"))
    unfiltered = backend.stream_messages(skip_own=False)
    assert (await anext(unfiltered)).content == "own again"
    await unfiltered.aclose()


@pytest.mark.asyncio
async def test_mock_backend_reconnect_keeps_bot_identity_and_disconnect_flips_state():
    backend = MockZulipBackend()
    await backend.connect()
    bot = backend._bot_user

    await backend.disconnect()
    assert not backend.connected
    await backend.connect()

    assert backend.connected
    assert backend._bot_user is bot
