"""LINE-specific message model and webhook conversion."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Optional

from ..base import Attachment, AttachmentType, Field, Message, MessageReference, MessageType
from .channel import LineChannel
from .user import LineUser

__all__ = ("LineMessage",)


_ATTACHMENT_TYPES = {
    "image": AttachmentType.IMAGE,
    "video": AttachmentType.VIDEO,
    "audio": AttachmentType.AUDIO,
    "file": AttachmentType.FILE,
}


class LineMessage(Message):
    """Message received from or sent through LINE."""

    message_id: str = Field(default="")
    quote_token: str = Field(default="")
    reply_token: str = Field(default="")
    webhook_event_id: str = Field(default="")
    is_redelivery: bool = Field(default=False)

    @classmethod
    def from_webhook_event(cls, event: Mapping[str, Any]) -> Optional["LineMessage"]:
        """Convert a LINE message webhook event into a chatom message."""
        if event.get("type") != "message":
            return None

        native = event.get("message") or {}
        source = event.get("source") or {}
        message_id = str(native.get("id", ""))
        native_type = str(native.get("type", "text"))
        channel = LineChannel.from_source(source)
        user_id = str(source.get("userId", ""))
        author = LineUser(id=user_id) if user_id else None
        content = str(native.get("text", "")) if native_type == "text" else str(native.get("fileName", ""))
        attachments: list[Attachment] = []
        if native_type in _ATTACHMENT_TYPES:
            attachments.append(
                Attachment(
                    id=message_id,
                    filename=str(native.get("fileName", "")),
                    size=native.get("fileSize"),
                    attachment_type=_ATTACHMENT_TYPES[native_type],
                )
            )

        quoted_id = str(native.get("quotedMessageId", ""))
        reference = MessageReference(message_id=quoted_id, channel_id=channel.id) if quoted_id else None
        timestamp = event.get("timestamp")
        created_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC) if isinstance(timestamp, (int, float)) else None
        mentions = [
            LineUser(id=str(item.get("userId", "")))
            for item in (native.get("mention") or {}).get("mentionees", [])
            if item.get("type") == "user" and item.get("userId")
        ]

        return cls(
            id=message_id,
            message_id=message_id,
            content=content,
            author=author,
            channel=channel,
            created_at=created_at,
            message_type=MessageType.REPLY if quoted_id else MessageType.DEFAULT,
            reference=reference,
            mentions=mentions,
            attachments=attachments,
            quote_token=str(native.get("quoteToken", "")),
            reply_token=str(event.get("replyToken", "")),
            webhook_event_id=str(event.get("webhookEventId", "")),
            is_redelivery=bool((event.get("deliveryContext") or {}).get("isRedelivery", False)),
            backend="line",
            raw=dict(event),
        )

    @classmethod
    def from_api_response(
        cls,
        data: Mapping[str, Any],
        *,
        content: str,
        channel: LineChannel,
    ) -> "LineMessage":
        """Build a sent message from a Messaging API response."""
        sent = (data.get("sentMessages") or [{}])[0]
        message_id = str(sent.get("id", ""))
        return cls(
            id=message_id,
            message_id=message_id,
            content=content,
            channel=channel,
            quote_token=str(sent.get("quoteToken", "")),
            created_at=datetime.now(UTC),
            backend="line",
            raw=dict(data),
        )
