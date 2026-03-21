"""Telegram-specific Channel model.

This module provides the Telegram-specific Channel class.
"""

from enum import Enum
from typing import Any

from chatom.base import Channel, ChannelType, Field
from chatom.base.conversion import register_backend_type

__all__ = ("TelegramChannel", "TelegramChatType")


class TelegramChatType(str, Enum):
    """Telegram chat types."""

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class TelegramChannel(Channel):
    """Telegram-specific channel (chat) with additional Telegram fields.

    In Telegram, "channels" are called "chats" and can be private (1:1),
    groups, supergroups, or broadcast channels.

    Attributes:
        chat_type: Telegram chat type.
        description: Chat description/bio.
        invite_link: Primary invite link for the chat.
        has_protected_content: Whether messages are protected from forwarding.
        is_forum: Whether this supergroup has forum topics enabled.
        chat_photo_url: URL of the chat's photo if available.
    """

    chat_type: TelegramChatType = Field(
        default=TelegramChatType.PRIVATE,
        description="Telegram chat type.",
    )
    description: str = Field(
        default="",
        description="Chat description/bio.",
    )
    invite_link: str = Field(
        default="",
        description="Primary invite link for the chat.",
    )
    has_protected_content: bool = Field(
        default=False,
        description="Whether messages are protected from forwarding.",
    )
    is_forum: bool = Field(
        default=False,
        description="Whether this supergroup has forum topics enabled.",
    )
    chat_photo_url: str = Field(
        default="",
        description="URL of the chat's photo if available.",
    )
    username: str = Field(
        default="",
        description="Public @username of the chat (without @), if set.",
    )

    @property
    def is_group_chat(self) -> bool:
        """Check if this is a group or supergroup chat."""
        return self.chat_type in (TelegramChatType.GROUP, TelegramChatType.SUPERGROUP)

    @property
    def is_broadcast_channel(self) -> bool:
        """Check if this is a broadcast channel."""
        return self.chat_type == TelegramChatType.CHANNEL

    @classmethod
    def from_telegram_chat(cls, chat: Any) -> "TelegramChannel":
        """Create a TelegramChannel from a python-telegram-bot Chat object.

        Args:
            chat: A telegram.Chat object.

        Returns:
            A TelegramChannel instance.
        """
        # Map Telegram chat type to chatom ChannelType
        type_map = {
            "private": ChannelType.DIRECT,
            "group": ChannelType.GROUP,
            "supergroup": ChannelType.PUBLIC,
            "channel": ChannelType.ANNOUNCEMENT,
        }
        chat_type_str = getattr(chat, "type", "private")

        return cls(
            id=str(chat.id),
            name=getattr(chat, "title", "") or getattr(chat, "first_name", "") or "",
            topic=getattr(chat, "description", "") or "",
            chat_type=TelegramChatType(chat_type_str) if chat_type_str in TelegramChatType.__members__.values() else TelegramChatType.PRIVATE,
            channel_type=type_map.get(chat_type_str, ChannelType.UNKNOWN),
            description=getattr(chat, "description", "") or "",
            invite_link=getattr(chat, "invite_link", "") or "",
            has_protected_content=getattr(chat, "has_protected_content", False) or False,
            is_forum=getattr(chat, "is_forum", False) or False,
            username=getattr(chat, "username", "") or "",
        )


# Register with conversion system
register_backend_type("telegram", Channel, TelegramChannel)
