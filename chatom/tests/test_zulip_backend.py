"""Focused tests for Zulip models, API mapping, and mock backend."""

from datetime import UTC, datetime

import pytest

from chatom.base import Channel, Message, Presence, Thread, User
from chatom.base.conversion import get_backend_type
from chatom.zulip import (
    MockZulipBackend,
    ZulipBackend,
    ZulipChannel,
    ZulipConfig,
    ZulipMessage,
    ZulipPresence,
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
