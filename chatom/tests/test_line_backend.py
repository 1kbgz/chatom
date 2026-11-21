"""Tests for the LINE backend."""

import asyncio
import base64
import hashlib
import hmac
import io
import json
from datetime import UTC, datetime
from typing import Self
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from chatom import ChannelType, Format
from chatom.backend.backend import AttachmentDownloadLimitError
from chatom.base import Attachment, Channel, PresenceStatus, User
from chatom.line import LineBackend, LineChannel, LineConfig, LineMessage, LinePresence, LineSourceType, LineUser, MockLineBackend


def _signed_payload(secret: str) -> tuple[str, str]:
    payload = json.dumps(
        {
            "events": [
                {
                    "type": "message",
                    "webhookEventId": "event-1",
                    "replyToken": "reply-1",
                    "timestamp": 1_700_000_000_000,
                    "source": {"type": "group", "groupId": "group-1", "userId": "user-1"},
                    "deliveryContext": {"isRedelivery": False},
                    "message": {
                        "id": "message-1",
                        "type": "text",
                        "text": "hello @Bot",
                        "quoteToken": "quote-1",
                        "mention": {"mentionees": [{"type": "user", "userId": "bot-1", "isSelf": True}]},
                    },
                }
            ]
        }
    )
    signature = base64.b64encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()).decode()
    return payload, signature


def test_line_config_and_profile_mapping() -> None:
    config = LineConfig(channel_access_token="token", channel_secret="secret")
    assert config.channel_access_token_str == "token"
    assert config.channel_secret_str == "secret"

    user = LineUser.from_api({"userId": "U1", "displayName": "Ada", "pictureUrl": "https://example.com/a.png"})
    assert user.name == "Ada"
    assert user.avatar_url == "https://example.com/a.png"


def test_line_webhook_mapping_and_signature() -> None:
    backend = LineBackend(config=LineConfig(channel_secret="secret"))
    payload, signature = _signed_payload("secret")

    messages = backend.process_webhook(payload, signature)

    assert len(messages) == 1
    message = messages[0]
    assert isinstance(message, LineMessage)
    assert message.content == "hello @Bot"
    assert message.channel_id == "group-1"
    assert message.author_id == "user-1"
    assert message.quote_token == "quote-1"
    assert message.mentions[0].id == "bot-1"
    assert message.channel is not None
    assert message.channel.channel_type == ChannelType.GROUP


def test_line_webhook_rejects_invalid_signature() -> None:
    backend = LineBackend(config=LineConfig(channel_secret="secret"))
    payload, _ = _signed_payload("secret")
    with pytest.raises(ValueError, match="Invalid LINE webhook signature"):
        backend.process_webhook(payload, "invalid")


@pytest.mark.asyncio
async def test_mock_line_backend_send_and_fetch() -> None:
    backend = MockLineBackend()
    backend.add_mock_user("user-1", "Ada")
    backend.add_mock_channel("group-1", "General", LineSourceType.GROUP)
    await backend.connect()

    sent = await backend.send_message("group-1", "hello")
    fetched = await backend.fetch_messages("group-1")

    assert sent.content == "hello"
    assert fetched == [sent]
    assert backend.get_format() == Format.PLAINTEXT
    assert backend.mention_user(LineUser(id="user-1", name="Ada")) == "@Ada"


def _signed_event(secret: str, *, event_id: str, message_id: str, channel_id: str) -> tuple[str, str]:
    payload = json.dumps(
        {
            "events": [
                {
                    "type": "message",
                    "webhookEventId": event_id,
                    "timestamp": 1_700_000_000_000,
                    "source": {"type": "group", "groupId": channel_id, "userId": "user-1"},
                    "deliveryContext": {"isRedelivery": False},
                    "message": {"id": message_id, "type": "text", "text": "hi"},
                }
            ]
        }
    )
    signature = base64.b64encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()).decode()
    return payload, signature


def test_webhook_redelivery_is_deduplicated() -> None:
    """LINE retries webhooks, so the same event must not duplicate.

    Regression: process_webhook enqueued and cached every delivery.
    """
    backend = LineBackend(config=LineConfig(channel_secret="secret"))
    payload, signature = _signed_event("secret", event_id="e1", message_id="m1", channel_id="group-1")

    first = backend.process_webhook(payload, signature)
    second = backend.process_webhook(payload, signature)

    assert len(first) == 1
    assert second == []
    assert len(backend._message_cache["group-1"]) == 1


@pytest.mark.asyncio
async def test_channel_filtered_stream_does_not_discard_other_channels() -> None:
    """Each consumer gets its own queue.

    Regression: a single shared queue meant a stream filtered to one channel
    consumed and dropped every other channel's messages.
    """
    backend = LineBackend(config=LineConfig(channel_secret="secret", channel_access_token="token"))
    backend.connected = True

    stream_a = backend.stream_messages(channel="group-a")
    stream_b = backend.stream_messages(channel="group-b")
    task_a = asyncio.ensure_future(anext(stream_a))
    task_b = asyncio.ensure_future(anext(stream_b))
    await asyncio.sleep(0)  # let both consumers subscribe

    for channel_id in ("group-a", "group-b"):
        payload, signature = _signed_event(
            "secret",
            event_id=f"e-{channel_id}",
            message_id=f"m-{channel_id}",
            channel_id=channel_id,
        )
        backend.process_webhook(payload, signature)

    message_a = await asyncio.wait_for(task_a, timeout=1)
    message_b = await asyncio.wait_for(task_b, timeout=1)

    assert message_a.channel_id == "group-a"
    assert message_b.channel_id == "group-b"

    await stream_a.aclose()
    await stream_b.aclose()
    assert backend._subscribers == []


@pytest.mark.asyncio
async def test_upload_file_requires_hosted_https_url() -> None:
    """LINE has no byte-upload endpoint, so the error must say so."""
    backend = MockLineBackend()
    await backend.connect()

    with pytest.raises(ValueError, match="original_content_url"):
        await backend.upload_file("group-1", b"bytes", filename="photo.png")

    with pytest.raises(ValueError, match="HTTPS"):
        await backend.upload_file(
            "group-1",
            b"bytes",
            filename="photo.png",
            original_content_url="http://example.com/photo.png",
        )


def test_media_type_inference() -> None:
    assert LineBackend._media_type("image/png", "x") == "image"
    assert LineBackend._media_type("", "clip.mp4") == "video"
    assert LineBackend._media_type("", "take.m4a") == "audio"
    assert LineBackend._media_type("", "notes.txt") == "file"


class _FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self.headers = headers or {}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]


class _FakeUrlopen:
    """Records requests and replays queued responses (or raises queued exceptions)."""

    def __init__(self) -> None:
        self.queue: list = []
        self.requests: list = []
        self.timeouts: list = []

    def push(self, item: object) -> None:
        self.queue.append(item)

    def push_json(self, data: dict) -> None:
        self.queue.append(_FakeResponse(json.dumps(data).encode()))

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def urlopen(monkeypatch: pytest.MonkeyPatch) -> _FakeUrlopen:
    fake = _FakeUrlopen()
    monkeypatch.setattr("chatom.line.backend.urlopen", fake)
    monkeypatch.setattr("urllib.request.urlopen", fake)
    return fake


def _backend(**config: object) -> LineBackend:
    config.setdefault("channel_access_token", "token")
    config.setdefault("channel_secret", "secret")
    backend = LineBackend(config=LineConfig(**config))
    backend.connected = True
    return backend


def _body(request) -> dict:
    return json.loads(request.data)


def _text_event(message_id: str, timestamp: int, *, channel_id: str = "group-1", user_id: str = "user-1", event_id: str | None = None) -> dict:
    return {
        "type": "message",
        "webhookEventId": event_id or f"event-{message_id}",
        "timestamp": timestamp,
        "source": {"type": "group", "groupId": channel_id, "userId": user_id},
        "message": {"id": message_id, "type": "text", "text": f"text {message_id}"},
    }


def _sign(secret: str, raw: bytes) -> str:
    return base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()


def _deliver(backend: LineBackend, *events: dict) -> list[LineMessage]:
    raw = json.dumps({"events": list(events)}).encode()
    return backend.process_webhook(raw, _sign("secret", raw))


def test_config_reads_secret_from_file(tmp_path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("file-token\n")
    config = LineConfig(channel_access_token=str(token_file))
    assert config.channel_access_token_str == "file-token"

    assert LineConfig().channel_secret_str == ""
    assert LineConfig(channel_secret=SecretStr("direct")).channel_secret_str == "direct"


@pytest.mark.asyncio
async def test_connect_requires_access_token() -> None:
    backend = LineBackend(config=LineConfig())
    with pytest.raises(ValueError, match="channel_access_token"):
        await backend.connect()
    assert not backend.connected


@pytest.mark.asyncio
async def test_connect_fetches_bot_info_and_disconnect_resets(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"userId": "U-bot", "displayName": "Helper"})
    backend = LineBackend(config=LineConfig(channel_access_token="token", api_url="https://api.example.test/", timeout=7))

    await backend.connect()

    request = urlopen.requests[0]
    assert request.full_url == "https://api.example.test/v2/bot/info"
    assert request.get_method() == "GET"
    assert request.data is None
    assert request.get_header("Authorization") == "Bearer token"
    assert urlopen.timeouts == [7]
    assert backend.connected
    assert backend.bot_user_id == "U-bot"
    bot = await backend.get_bot_info()
    assert bot is not None and bot.name == "Helper"

    await backend.disconnect()
    assert not backend.connected
    assert backend.bot_user_id is None
    assert await backend.get_bot_info() is None


@pytest.mark.asyncio
async def test_connect_without_bot_user_id(urlopen: _FakeUrlopen) -> None:
    urlopen.push(_FakeResponse(b""))
    backend = LineBackend(config=LineConfig(channel_access_token="token"))

    await backend.connect()

    assert backend.connected
    assert backend.bot_user_id is None
    assert backend.users.all() == []


@pytest.mark.asyncio
async def test_http_error_surfaces_status_and_body(urlopen: _FakeUrlopen) -> None:
    urlopen.push(HTTPError("https://api.line.me/v2/bot/info", 401, "Unauthorized", {}, io.BytesIO(b'{"message":"bad token"}')))
    backend = LineBackend(config=LineConfig(channel_access_token="token"))

    with pytest.raises(ConnectionError, match=r"\(401\).*bad token"):
        await backend.connect()
    assert not backend.connected


@pytest.mark.asyncio
async def test_operations_require_connection() -> None:
    backend = LineBackend(config=LineConfig(channel_access_token="token"))
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.fetch_user("U1")
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.fetch_channel("C1")
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.fetch_messages("C1")
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.send_message("C1", "hi")
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.upload_file("C1", b"x", original_content_url="https://example.com/a.png")
    with pytest.raises(ConnectionError, match="Not connected"):
        await backend.download_attachment(Attachment(id="m1"))


@pytest.mark.asyncio
async def test_fetch_user_requests_profile_and_caches(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"userId": "U?1", "displayName": "Ada", "pictureUrl": "https://example.com/a.png"})
    backend = _backend()

    user = await backend.fetch_user("U?1")

    assert isinstance(user, LineUser)
    assert user.name == "Ada"
    assert user.picture_url == "https://example.com/a.png"
    assert urlopen.requests[0].full_url == "https://api.line.me/v2/bot/profile/U%3F1"
    assert backend.users.get_by_id("U?1") is user

    again = await backend.fetch_user(id="U?1")
    assert again is user
    assert len(urlopen.requests) == 1


@pytest.mark.asyncio
async def test_fetch_user_accepts_user_objects(urlopen: _FakeUrlopen) -> None:
    backend = _backend()
    line_user = LineUser(id="U1", name="Ada")
    assert await backend.fetch_user(line_user) is line_user
    assert urlopen.requests == []

    urlopen.push_json({"userId": "U2", "displayName": "Grace"})
    resolved = await backend.fetch_user(User(id="U2"))
    assert resolved is not None and resolved.name == "Grace"
    assert urlopen.requests[0].full_url.endswith("/v2/bot/profile/U2")


@pytest.mark.asyncio
async def test_fetch_user_api_failure_falls_back_to_cache(urlopen: _FakeUrlopen) -> None:
    backend = _backend()
    nameless = LineUser(id="U1")
    backend.users.add(nameless)
    urlopen.push(HTTPError("u", 404, "Not Found", {}, io.BytesIO(b"nope")))
    urlopen.push(HTTPError("u", 404, "Not Found", {}, io.BytesIO(b"nope")))

    assert await backend.fetch_user("U1") is nameless
    assert await backend.fetch_user("missing") is None


@pytest.mark.asyncio
async def test_fetch_user_by_name_or_handle_without_id() -> None:
    backend = _backend()
    backend.users.add(LineUser(id="U1", name="Ada", handle="ada_l"))

    by_name = await backend.fetch_user(name="ADA")
    by_handle = await backend.fetch_user(handle="ADA_L")

    assert by_name is not None and by_name.id == "U1"
    assert by_handle is not None and by_handle.id == "U1"
    assert await backend.fetch_user(name="nobody") is None
    assert await backend.fetch_user() is None


@pytest.mark.asyncio
async def test_fetch_channel_requests_group_summary_and_caches(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"groupId": "C1", "groupName": "General", "pictureUrl": "https://example.com/g.png"})
    backend = _backend()

    channel = await backend.fetch_channel("C1")

    assert isinstance(channel, LineChannel)
    assert channel.name == "General"
    assert channel.source_type == LineSourceType.GROUP
    assert urlopen.requests[0].full_url == "https://api.line.me/v2/bot/group/C1/summary"
    assert urlopen.requests[0].get_header("Authorization") == "Bearer token"

    assert await backend.fetch_channel(id="C1") is channel
    assert len(urlopen.requests) == 1


@pytest.mark.asyncio
async def test_fetch_channel_objects_failure_and_name_lookup(urlopen: _FakeUrlopen) -> None:
    backend = _backend()
    line_channel = LineChannel(id="C1", name="General")
    assert await backend.fetch_channel(line_channel) is line_channel

    nameless = LineChannel(id="C2")
    backend.channels.add(nameless)
    urlopen.push(HTTPError("u", 404, "Not Found", {}, io.BytesIO(b"nope")))
    assert await backend.fetch_channel(Channel(id="C2")) is nameless

    backend.channels.add(line_channel)
    found = await backend.fetch_channel(name="general")
    assert found is line_channel
    assert await backend.fetch_channel(name="missing") is None
    assert await backend.fetch_channel() is None


@pytest.mark.asyncio
async def test_fetch_messages_newest_first_with_limit() -> None:
    backend = _backend()
    _deliver(backend, *(_text_event(f"m{i}", 1_700_000_000_000 + i * 1000) for i in range(1, 5)))

    newest_first = await backend.fetch_messages("group-1")
    assert [m.id for m in newest_first] == ["m4", "m3", "m2", "m1"]
    assert [m.id for m in await backend.fetch_messages("group-1", limit=2)] == ["m4", "m3"]
    assert await backend.fetch_messages("other-group") == []


@pytest.mark.asyncio
async def test_fetch_messages_time_bounds() -> None:
    backend = _backend()
    _deliver(backend, *(_text_event(f"m{i}", 1_700_000_000_000 + i * 1000) for i in range(1, 5)))
    by_id = {m.id: m for m in await backend.fetch_messages("group-1")}

    cutoff = datetime.fromtimestamp(1_700_000_002, tz=UTC)
    assert [m.id for m in await backend.fetch_messages("group-1", before=cutoff)] == ["m2", "m1"]
    assert [m.id for m in await backend.fetch_messages("group-1", after=cutoff)] == ["m4", "m3", "m2"]
    assert [m.id for m in await backend.fetch_messages("group-1", before=by_id["m3"])] == ["m3", "m2", "m1"]
    assert [m.id for m in await backend.fetch_messages("group-1", after=by_id["m3"])] == ["m4", "m3"]


@pytest.mark.asyncio
async def test_fetch_messages_id_bounds() -> None:
    backend = _backend()
    _deliver(backend, *(_text_event(f"m{i}", 1_700_000_000_000 + i * 1000) for i in range(1, 5)))

    assert [m.id for m in await backend.fetch_messages("group-1", before="m3")] == ["m2", "m1"]
    assert [m.id for m in await backend.fetch_messages("group-1", after="m2")] == ["m4", "m3"]
    assert await backend.fetch_messages("group-1", before="unknown") == []
    assert await backend.fetch_messages("group-1", after="unknown") == []


@pytest.mark.asyncio
async def test_send_message_pushes_to_channel(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"sentMessages": [{"id": "sent-1", "quoteToken": "qt-1"}]})
    backend = _backend()
    backend.channels.add(LineChannel(id="group-1", name="General"))

    message = await backend.send_message("group-1", "hello")

    request = urlopen.requests[0]
    assert request.full_url == "https://api.line.me/v2/bot/message/push"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer token"
    assert request.get_header("Content-type") == "application/json"
    assert _body(request) == {"to": "group-1", "messages": [{"type": "text", "text": "hello"}]}
    assert message.id == "sent-1"
    assert message.content == "hello"
    assert message.quote_token == "qt-1"
    assert message.channel is not None and message.channel.name == "General"
    assert [m.id for m in await backend.fetch_messages("group-1")] == ["sent-1"]


@pytest.mark.asyncio
async def test_send_message_replies_with_token_and_quote(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"sentMessages": [{"id": "sent-2"}]})
    backend = _backend()
    original = LineMessage(id="m1", content="hi", quote_token="qt-orig")

    message = await backend.send_message(LineChannel(id="user-9"), "pong", reply_token="rt-1", reply_to=original)

    request = urlopen.requests[0]
    assert request.full_url == "https://api.line.me/v2/bot/message/reply"
    assert _body(request) == {
        "replyToken": "rt-1",
        "messages": [{"type": "text", "text": "pong", "quoteToken": "qt-orig"}],
    }
    assert message.channel_id == "user-9"


@pytest.mark.asyncio
async def test_send_message_ignores_reply_to_without_quote_token(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"sentMessages": [{"id": "sent-3"}]})
    backend = _backend()

    await backend.send_message("group-1", "x", reply_to=LineMessage(id="m1", content="hi"))

    assert _body(urlopen.requests[0])["messages"] == [{"type": "text", "text": "x"}]


def test_webhook_requires_channel_secret() -> None:
    backend = LineBackend(config=LineConfig())
    with pytest.raises(ValueError, match="channel_secret is required"):
        backend.process_webhook(b"{}", "sig")


def test_webhook_accepts_bytes_and_rejects_tampered_body() -> None:
    backend = _backend()
    raw = json.dumps({"events": [_text_event("m1", 1_700_000_000_000)]}).encode()
    signature = _sign("secret", raw)

    with pytest.raises(ValueError, match="Invalid LINE webhook signature"):
        backend.process_webhook(raw + b" ", signature)
    assert backend._message_cache == {}

    assert [m.id for m in backend.process_webhook(raw, signature)] == ["m1"]


def test_webhook_caches_users_and_channels_and_skips_other_events() -> None:
    backend = _backend()
    follow = {"type": "follow", "source": {"type": "user", "userId": "user-2"}}

    messages = _deliver(backend, follow, _text_event("m1", 1_700_000_000_000), _text_event("m2", 1_700_000_001_000, user_id="user-3"))

    assert [m.id for m in messages] == ["m1", "m2"]
    assert backend.channels.get_by_id("group-1") is not None
    assert backend.users.get_by_id("user-1") is not None
    assert backend.users.get_by_id("user-3") is not None
    assert backend.users.get_by_id("user-2") is None


def test_webhook_events_without_ids_are_not_deduplicated() -> None:
    backend = _backend()
    event = _text_event("", 1_700_000_000_000, event_id="e1")

    assert len(_deliver(backend, event)) == 1
    assert len(_deliver(backend, event)) == 1
    assert len(backend._message_cache["group-1"]) == 2
    assert backend._seen_event_ids == set()


def test_webhook_without_events_returns_nothing() -> None:
    assert _deliver(_backend()) == []


@pytest.mark.asyncio
async def test_stream_skips_own_messages_by_default() -> None:
    backend = _backend()
    backend._bot_user_id = "bot-1"
    stream = backend.stream_messages()
    task = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)

    _deliver(backend, _text_event("own", 1_700_000_000_000, user_id="bot-1"), _text_event("other", 1_700_000_001_000, user_id="user-1"))
    message = await asyncio.wait_for(task, timeout=1)

    assert message.id == "other"
    await stream.aclose()
    assert backend._subscribers == []


@pytest.mark.asyncio
async def test_stream_can_include_own_messages() -> None:
    backend = _backend()
    backend._bot_user_id = "bot-1"
    stream = backend.stream_messages(channel=LineChannel(id="group-1"), skip_own=False)
    task = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)

    _deliver(backend, _text_event("own", 1_700_000_000_000, user_id="bot-1"))
    message = await asyncio.wait_for(task, timeout=1)

    assert message.id == "own"
    assert backend._subscribers[0][0] == "group-1"
    await stream.aclose()


@pytest.mark.asyncio
async def test_upload_image_pushes_media_message(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"sentMessages": [{"id": "img-1"}]})
    backend = _backend()

    message = await backend.upload_file(
        "group-1",
        b"",
        filename="photo.png",
        title="A photo",
        original_content_url="https://cdn.example.com/photo.png",
    )

    request = urlopen.requests[0]
    assert request.full_url == "https://api.line.me/v2/bot/message/push"
    assert _body(request) == {
        "to": "group-1",
        "messages": [
            {
                "type": "image",
                "originalContentUrl": "https://cdn.example.com/photo.png",
                "previewImageUrl": "https://cdn.example.com/photo.png",
            }
        ],
    }
    assert message.id == "img-1"
    assert message.content == "A photo"
    assert [m.id for m in await backend.fetch_messages("group-1")] == ["img-1"]


@pytest.mark.asyncio
async def test_upload_video_and_audio_require_duration(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"sentMessages": [{"id": "vid-1"}]})
    urlopen.push_json({"sentMessages": [{"id": "aud-1"}]})
    backend = _backend()

    with pytest.raises(ValueError, match="video messages require duration"):
        await backend.upload_file("group-1", b"", filename="clip.mp4", original_content_url="https://cdn.example.com/clip.mp4")
    with pytest.raises(ValueError, match="audio messages require duration"):
        await backend.upload_file("group-1", b"", content_type="audio/mp4", original_content_url="https://cdn.example.com/a.m4a")
    assert urlopen.requests == []

    await backend.upload_file(
        "group-1",
        b"",
        filename="clip.mp4",
        original_content_url="https://cdn.example.com/clip.mp4",
        preview_image_url="https://cdn.example.com/clip.jpg",
        duration="2500",
    )
    await backend.upload_file(
        "group-1",
        b"",
        content_type="audio/mp4",
        content="voice note",
        original_content_url="https://cdn.example.com/a.m4a",
        duration=1000,
        reply_token="rt-9",
    )

    video, audio = (_body(r) for r in urlopen.requests)
    assert urlopen.requests[0].full_url.endswith("/v2/bot/message/push")
    assert video["messages"] == [
        {
            "type": "video",
            "originalContentUrl": "https://cdn.example.com/clip.mp4",
            "previewImageUrl": "https://cdn.example.com/clip.jpg",
            "duration": 2500,
        }
    ]
    assert urlopen.requests[1].full_url.endswith("/v2/bot/message/reply")
    assert audio == {
        "replyToken": "rt-9",
        "messages": [{"type": "audio", "originalContentUrl": "https://cdn.example.com/a.m4a", "duration": 1000}],
    }


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_media_type(urlopen: _FakeUrlopen) -> None:
    backend = _backend()

    with pytest.raises(ValueError, match="not 'file'"):
        await backend.upload_file("group-1", b"", filename="notes.txt", original_content_url="https://cdn.example.com/notes.txt")
    assert urlopen.requests == []


@pytest.mark.asyncio
async def test_upload_message_type_overrides_inference(urlopen: _FakeUrlopen) -> None:
    urlopen.push_json({"sentMessages": [{"id": "img-2"}]})
    backend = _backend()

    await backend.upload_file(
        "group-1",
        b"",
        filename="blob.bin",
        original_content_url="https://cdn.example.com/blob",
        message_type="IMAGE",
    )

    assert _body(urlopen.requests[0])["messages"][0]["type"] == "image"


def test_media_type_from_extension() -> None:
    assert LineBackend._media_type("", "photo.JPG") == "image"
    assert LineBackend._media_type("", "photo.png") == "image"
    assert LineBackend._media_type("video/mp4", "x") == "video"
    assert LineBackend._media_type("", "song.mp3") == "audio"
    assert LineBackend._media_type("", "noextension") == "file"


@pytest.mark.asyncio
async def test_download_attachment_uses_data_api_with_bearer_token(urlopen: _FakeUrlopen) -> None:
    urlopen.push(_FakeResponse(b"image-bytes"))
    backend = _backend(data_api_url="https://data.example.test/")

    data = await backend.download_attachment(Attachment(id="msg?1"))

    assert data == b"image-bytes"
    request = urlopen.requests[0]
    assert request.full_url == "https://data.example.test/v2/bot/message/msg%3F1/content"
    assert request.get_header("Authorization") == "Bearer token"


@pytest.mark.asyncio
async def test_download_attachment_falls_back_to_message_id(urlopen: _FakeUrlopen) -> None:
    urlopen.push(_FakeResponse(b"abc"))
    backend = _backend()

    data = await backend.download_attachment(Attachment(filename="x.bin"), message=LineMessage(id="m7", content=""))

    assert data == b"abc"
    assert urlopen.requests[0].full_url == "https://api-data.line.me/v2/bot/message/m7/content"


@pytest.mark.asyncio
async def test_download_attachment_enforces_max_bytes(urlopen: _FakeUrlopen) -> None:
    urlopen.push(_FakeResponse(b"0123456789", {"Content-Length": "10"}))
    backend = _backend()

    with pytest.raises(AttachmentDownloadLimitError):
        await backend.download_attachment(Attachment(id="m1"), max_bytes=4)


@pytest.mark.asyncio
async def test_download_attachment_in_memory_data_makes_no_request(urlopen: _FakeUrlopen) -> None:
    backend = _backend()

    assert await backend.download_attachment(Attachment(id="m1", data=b"local")) == b"local"
    with pytest.raises(AttachmentDownloadLimitError):
        await backend.download_attachment(Attachment(id="m1", data=b"local"), max_bytes=2)
    assert urlopen.requests == []


@pytest.mark.asyncio
async def test_download_attachment_without_any_source_raises(urlopen: _FakeUrlopen) -> None:
    backend = _backend()

    with pytest.raises(NotImplementedError, match="no data or url"):
        await backend.download_attachment(Attachment(filename="x.bin"))
    with pytest.raises(NotImplementedError):
        await backend.download_attachment(Attachment(id="  "), message=LineMessage(id="", content=""))
    assert urlopen.requests == []


@pytest.mark.asyncio
async def test_download_attachment_uses_url_when_no_id(urlopen: _FakeUrlopen) -> None:
    urlopen.push(_FakeResponse(b"remote"))
    backend = _backend()

    data = await backend.download_attachment(Attachment(url="https://files.example.com/a.bin"))

    assert data == b"remote"
    assert urlopen.requests[0].full_url == "https://files.example.com/a.bin"
    assert urlopen.requests[0].get_header("Authorization") is None


@pytest.mark.asyncio
async def test_presence_is_unknown_and_mentions_render() -> None:
    backend = _backend()

    presence = await backend.get_presence("U1")
    assert isinstance(presence, LinePresence)
    assert presence.user.id == "U1"
    assert presence.status == PresenceStatus.UNKNOWN

    assert backend.mention_channel(LineChannel(id="C1", name="General")) == "#General"
    assert backend.mention_channel(LineChannel(id="C1")) == "#C1"


def test_webhook_media_event_maps_attachment_and_reply_reference() -> None:
    event = {
        "type": "message",
        "webhookEventId": "e1",
        "replyToken": "rt",
        "timestamp": 1_700_000_000_000,
        "source": {"type": "room", "roomId": "room-1", "userId": "user-1"},
        "deliveryContext": {"isRedelivery": True},
        "message": {"id": "m1", "type": "file", "fileName": "report.pdf", "fileSize": 42, "quotedMessageId": "m0"},
    }

    message = LineMessage.from_webhook_event(event)

    assert message is not None
    assert message.content == "report.pdf"
    assert message.is_redelivery is True
    assert message.reply_token == "rt"
    assert message.channel is not None and message.channel.source_type == LineSourceType.ROOM
    assert message.reference is not None and message.reference.message_id == "m0"
    assert message.reference.channel_id == "room-1"
    assert len(message.attachments) == 1
    attachment = message.attachments[0]
    assert (attachment.id, attachment.filename, attachment.size) == ("m1", "report.pdf", 42)
    assert LineMessage.from_webhook_event({"type": "follow"}) is None


@pytest.mark.asyncio
async def test_mock_backend_name_lookups_and_sent_messages() -> None:
    backend = MockLineBackend()
    ada = backend.add_mock_user("user-1", "Ada")
    general = backend.add_mock_channel("group-1", "General")
    await backend.connect()

    assert await backend.fetch_user(name="Ada") is ada
    assert await backend.fetch_user(name="Nobody") is None
    assert await backend.fetch_user(id="user-1") is ada
    assert await backend.fetch_channel(name="General") is general
    assert await backend.fetch_channel(name="Nobody") is None
    assert await backend.fetch_channel("group-1") is general

    first = await backend.send_message("group-1", "one")
    second = await backend.send_message(general, "two")
    assert (first.id, second.id) == ("line-1", "line-2")
    assert backend._sent_messages == [first, second]
    assert first.author_id == "line-bot"


@pytest.mark.asyncio
async def test_stream_ends_after_disconnect_and_unsubscribes() -> None:
    backend = _backend()
    stream = backend.stream_messages()
    task = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)

    await backend.disconnect()
    _deliver(backend, _text_event("last", 1_700_000_000_000))
    assert (await asyncio.wait_for(task, timeout=1)).id == "last"

    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert backend._subscribers == []
