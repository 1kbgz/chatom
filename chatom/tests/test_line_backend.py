"""Tests for the LINE backend."""

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
