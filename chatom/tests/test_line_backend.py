"""Tests for the LINE backend."""

import asyncio
import base64
import hashlib
import hmac
import json

import pytest

from chatom import ChannelType, Format
from chatom.line import LineBackend, LineConfig, LineMessage, LineSourceType, LineUser, MockLineBackend


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
