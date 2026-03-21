"""Telegram-specific Message model.

This module provides the Telegram-specific Message class.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from chatom.base import Field, Message, User
from chatom.telegram.channel import TelegramChannel
from chatom.telegram.user import TelegramUser

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = ("TelegramMessage",)


class TelegramMessage(Message):
    """Telegram-specific message with additional Telegram fields.

    Attributes:
        message_id: Telegram's integer message ID within the chat.
        chat_id: The chat ID this message belongs to.
        message_thread_id: Thread (topic) ID in a forum supergroup.
        reply_to_message_id: ID of the message being replied to.
        forward_origin: Information about the original forwarded message.
        entities: List of special entities (mentions, URLs, etc.) from the API.
        has_protected_content: Whether the message is protected from forwarding.
    """

    message_id: int = Field(
        default=0,
        description="Telegram's integer message ID within the chat.",
    )
    chat_id: str = Field(
        default="",
        description="The chat ID this message belongs to.",
    )
    message_thread_id: Optional[int] = Field(
        default=None,
        description="Thread (topic) ID in a forum supergroup.",
    )
    reply_to_message_id: Optional[int] = Field(
        default=None,
        description="ID of the message being replied to.",
    )
    forward_origin: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Information about the original forwarded message.",
    )
    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of message entities from the API.",
    )
    has_protected_content: bool = Field(
        default=False,
        description="Whether the message is protected from forwarding.",
    )

    def to_formatted(self) -> "FormattedMessage":
        """Convert this Telegram message to a FormattedMessage.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedAttachment, FormattedMessage

        fm = FormattedMessage()

        if self.content:
            fm.add_text(self.content)

        for att in self.attachments:
            fm.attachments.append(
                FormattedAttachment(
                    filename=att.filename,
                    url=att.url,
                    content_type=att.content_type,
                    size=att.size,
                )
            )

        fm.metadata["source_backend"] = "telegram"
        fm.metadata["message_id"] = self.id
        if self.chat_id:
            fm.metadata["chat_id"] = self.chat_id

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        backend: str = "",
        **kwargs: Any,
    ) -> "TelegramMessage":
        """Create a TelegramMessage from a FormattedMessage.

        Args:
            formatted: The FormattedMessage to convert.
            backend: Target backend (ignored, always uses HTML format).
            **kwargs: Additional message attributes.

        Returns:
            TelegramMessage: A new TelegramMessage instance.
        """
        from chatom.format import Format

        content = formatted.render(Format.HTML)

        return cls(
            content=content,
            backend="telegram",
            metadata=dict(formatted.metadata),
            **kwargs,
        )

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "TelegramMessage":
        """Create a TelegramMessage from a Telegram API response dict.

        Args:
            data: The API response data (message dict).

        Returns:
            A TelegramMessage instance.
        """
        from datetime import datetime, timezone

        from_data = data.get("from", {})
        author = (
            TelegramUser(
                id=str(from_data.get("id", "")),
                name=from_data.get("first_name", ""),
                handle=from_data.get("username", ""),
                first_name=from_data.get("first_name", ""),
                last_name=from_data.get("last_name", ""),
                username=from_data.get("username", ""),
                is_bot=from_data.get("is_bot", False),
            )
            if from_data
            else None
        )

        chat_data = data.get("chat", {})
        chat_id = str(chat_data.get("id", ""))
        channel = (
            TelegramChannel(
                id=chat_id,
                name=chat_data.get("title", "") or chat_data.get("first_name", "") or "",
            )
            if chat_data
            else None
        )

        msg_id = data.get("message_id", 0)
        date = data.get("date")
        created_at = datetime.fromtimestamp(date, tz=timezone.utc) if isinstance(date, (int, float)) else None

        # Extract mention entities
        mention_users: List[User] = []
        for entity in data.get("entities", []):
            if entity.get("type") == "text_mention" and entity.get("user"):
                u = entity["user"]
                mention_users.append(
                    TelegramUser(
                        id=str(u.get("id", "")),
                        name=u.get("first_name", ""),
                        handle=u.get("username", ""),
                    )
                )

        return cls(
            id=str(msg_id),
            content=data.get("text", "") or data.get("caption", "") or "",
            message_id=msg_id,
            chat_id=chat_id,
            channel=channel,
            author=author,
            is_bot=author.is_bot if author else False,
            created_at=created_at,
            is_edited=data.get("edit_date") is not None,
            message_thread_id=data.get("message_thread_id"),
            reply_to_message_id=data.get("reply_to_message", {}).get("message_id") if data.get("reply_to_message") else None,
            entities=data.get("entities", []),
            has_protected_content=data.get("has_protected_content", False),
            tags=mention_users,
            raw=data,
            backend="telegram",
        )

    @classmethod
    def from_telegram_message(cls, msg: Any) -> "TelegramMessage":
        """Create a TelegramMessage from a python-telegram-bot Message object.

        Args:
            msg: A telegram.Message object.

        Returns:
            A TelegramMessage instance.
        """
        from datetime import timezone

        author = TelegramUser.from_telegram_user(msg.from_user) if msg.from_user else None
        channel = TelegramChannel.from_telegram_chat(msg.chat) if msg.chat else None

        # Extract mention entities
        mention_users: List[User] = []
        if msg.entities:
            for entity in msg.entities:
                if entity.type == "text_mention" and entity.user:
                    mention_users.append(TelegramUser.from_telegram_user(entity.user))

        return cls(
            id=str(msg.message_id),
            content=msg.text or msg.caption or "",
            message_id=msg.message_id,
            chat_id=str(msg.chat.id) if msg.chat else "",
            channel=channel,
            author=author,
            is_bot=author.is_bot if author else False,
            created_at=msg.date.replace(tzinfo=timezone.utc) if msg.date and msg.date.tzinfo is None else msg.date,
            is_edited=msg.edit_date is not None,
            message_thread_id=msg.message_thread_id,
            reply_to_message_id=msg.reply_to_message.message_id if msg.reply_to_message else None,
            entities=[{"type": e.type, "offset": e.offset, "length": e.length} for e in (msg.entities or [])],
            has_protected_content=getattr(msg, "has_protected_content", False) or False,
            tags=mention_users,
            backend="telegram",
        )

    def mentions_user(self, user: User) -> bool:
        """Check if this message mentions a specific user.

        Args:
            user: The User to check for.

        Returns:
            True if the message mentions the user.
        """
        user_id = str(user.id)
        for m in self.mentions:
            if str(m.id) == user_id:
                return True
        return False
