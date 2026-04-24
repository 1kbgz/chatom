"""Mock Telegram backend for testing.

This module provides a mock implementation of the Telegram backend
for use in testing without requiring an actual Telegram connection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import PrivateAttr

from ..base import Channel, Message, MessageType, Presence, PresenceStatus, User
from ..base.thread import Thread
from .backend import TelegramBackend
from .channel import TelegramChannel, TelegramChatType
from .message import TelegramMessage
from .presence import TelegramPresence
from .user import TelegramUser

__all__ = ("MockTelegramBackend",)


class MockTelegramBackend(TelegramBackend):
    """Mock Telegram backend for testing.

    Stores all data in memory and provides methods to set up
    mock data for tests.

    Example:
        >>> backend = MockTelegramBackend()
        >>> backend.add_mock_user("123", "Alice", "alice")
        >>> backend.add_mock_channel("-100456", "general")
        >>> await backend.connect()
        >>> user = await backend.fetch_user("123")
        >>> assert user.name == "Alice"
    """

    # Mock data stores
    _mock_users: Dict[str, TelegramUser] = PrivateAttr(default_factory=dict)
    _mock_channels: Dict[str, TelegramChannel] = PrivateAttr(default_factory=dict)
    _mock_messages: Dict[str, List[TelegramMessage]] = PrivateAttr(default_factory=dict)
    _mock_presence: Dict[str, TelegramPresence] = PrivateAttr(default_factory=dict)

    # Tracking stores
    _sent_messages: List[TelegramMessage] = PrivateAttr(default_factory=list)
    _edited_messages: List[TelegramMessage] = PrivateAttr(default_factory=list)
    _deleted_messages: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _reactions: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _presence_updates: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _message_counter: int = PrivateAttr(default=0)

    def __init__(self, **data: Any) -> None:
        """Initialize the mock backend."""
        super().__init__(**data)
        self._mock_users = {}
        self._mock_channels = {}
        self._mock_messages = {}
        self._mock_presence = {}
        self._sent_messages = []
        self._edited_messages = []
        self._deleted_messages = []
        self._reactions = []
        self._presence_updates = []
        self._created_dms: List[List[str]] = []
        self._dm_counter = 0
        self._message_counter = 0

    def add_mock_user(
        self,
        id: str,
        name: str,
        handle: str = "",
        *,
        first_name: str = "",
        last_name: str = "",
        username: str = "",
        is_bot: bool = False,
        is_premium: bool = False,
        language_code: str = "",
    ) -> TelegramUser:
        """Add a mock user for testing.

        Args:
            id: The user ID.
            name: The user's display name.
            handle: The username (without @).
            first_name: First name.
            last_name: Last name.
            username: Telegram username (defaults to handle).
            is_bot: Whether the user is a bot.
            is_premium: Whether the user has Telegram Premium.
            language_code: User's language code.

        Returns:
            The created mock user.
        """
        user = TelegramUser(
            id=id,
            name=name,
            handle=handle or username,
            first_name=first_name or name.split()[0] if name else "",
            last_name=last_name or (name.split()[1] if len(name.split()) > 1 else ""),
            username=username or handle,
            is_bot=is_bot,
            is_premium=is_premium,
            language_code=language_code,
        )
        self._mock_users[id] = user
        self.users.add(user)
        return user

    def add_mock_channel(
        self,
        id: str,
        name: str,
        channel_type: str = "supergroup",
        *,
        topic: str = "",
        description: str = "",
        chat_type: Optional[TelegramChatType] = None,
        is_forum: bool = False,
    ) -> TelegramChannel:
        """Add a mock channel for testing.

        Args:
            id: The chat ID.
            name: The chat name/title.
            channel_type: Chat type string ("private", "group", "supergroup", "channel").
            topic: The chat topic.
            description: The chat description.
            chat_type: TelegramChatType enum (overrides channel_type).
            is_forum: Whether the chat is a forum supergroup.

        Returns:
            The created mock channel.
        """
        if chat_type is None:
            type_map = {
                "private": TelegramChatType.PRIVATE,
                "group": TelegramChatType.GROUP,
                "supergroup": TelegramChatType.SUPERGROUP,
                "channel": TelegramChatType.CHANNEL,
            }
            chat_type = type_map.get(channel_type, TelegramChatType.SUPERGROUP)

        channel = TelegramChannel(
            id=id,
            name=name,
            topic=topic or description,
            chat_type=chat_type,
            description=description,
            is_forum=is_forum,
        )
        self._mock_channels[id] = channel
        self.channels.add(channel)
        return channel

    def add_mock_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        *,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        edited: bool = False,
    ) -> str:
        """Add a mock message for testing.

        Args:
            channel_id: The chat containing the message.
            user_id: The author's user ID.
            content: The message content.
            message_id: Optional message ID (auto-generated if not provided).
            timestamp: Message timestamp.
            edited: Whether the message was edited.

        Returns:
            The message ID.
        """
        if message_id is None:
            self._message_counter += 1
            message_id = str(self._message_counter)

        message = TelegramMessage(
            id=message_id,
            content=content,
            message_id=int(message_id),
            chat_id=channel_id,
            created_at=timestamp or datetime.now(timezone.utc),
            author=TelegramUser(id=user_id),
            channel=TelegramChannel(id=channel_id),
            is_edited=edited,
        )
        if channel_id not in self._mock_messages:
            self._mock_messages[channel_id] = []
        self._mock_messages[channel_id].append(message)
        return message_id

    def set_mock_presence(
        self,
        user_id: str,
        status: PresenceStatus = PresenceStatus.ONLINE,
        *,
        last_seen_approximate: str = "",
    ) -> TelegramPresence:
        """Set mock presence for a user.

        Args:
            user_id: The user ID.
            status: The presence status.
            last_seen_approximate: Approximate last seen description.

        Returns:
            The created mock presence.
        """
        user = TelegramUser(id=user_id)
        presence = TelegramPresence(
            user=user,
            status=status,
            last_seen_approximate=last_seen_approximate,
        )
        self._mock_presence[user_id] = presence
        return presence

    @property
    def sent_messages(self) -> List[TelegramMessage]:
        """Get all messages sent through this backend."""
        return self._sent_messages

    @property
    def edited_messages(self) -> List[TelegramMessage]:
        """Get all messages edited through this backend."""
        return self._edited_messages

    @property
    def deleted_messages(self) -> List[Dict[str, str]]:
        """Get all message IDs deleted through this backend."""
        return self._deleted_messages

    def get_sent_messages(self) -> List[TelegramMessage]:
        """Get all messages sent through this backend (copy)."""
        return self._sent_messages.copy()

    def get_edited_messages(self) -> List[TelegramMessage]:
        """Get all messages edited through this backend (copy)."""
        return self._edited_messages.copy()

    def get_deleted_messages(self) -> List[Dict[str, str]]:
        """Get all messages deleted through this backend (copy)."""
        return self._deleted_messages.copy()

    def get_reactions(self) -> List[Dict[str, str]]:
        """Get all reactions added/removed through this backend (copy)."""
        return self._reactions.copy()

    def get_presence_updates(self) -> List[Dict[str, Any]]:
        """Get all presence updates (copy)."""
        return self._presence_updates.copy()

    @property
    def created_dms(self) -> List[List[str]]:
        """Get all DMs created through this backend."""
        return self._created_dms

    def clear(self) -> None:
        """Clear all mock data and tracking stores."""
        self._mock_users.clear()
        self._mock_channels.clear()
        self._mock_messages.clear()
        self._mock_presence.clear()
        self._sent_messages.clear()
        self._edited_messages.clear()
        self._deleted_messages.clear()
        self._reactions.clear()
        self._presence_updates.clear()
        self.users.clear()
        self.channels.clear()

    # Override backend methods for mock behavior

    async def connect(self) -> None:
        """Mock connect - always succeeds."""
        self.connected = True
        self._bot_user_id = "bot_user"
        self._bot_user_name = "test_bot"

    async def disconnect(self) -> None:
        """Mock disconnect."""
        self.connected = False
        self._bot_user_id = None
        self._bot_user_name = None

    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a mock user."""
        if isinstance(identifier, TelegramUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = str(identifier.id)

        if identifier and not id:
            id = str(identifier)

        if id:
            user = self._mock_users.get(id) or self.users.get_by_id(id)
            if user:
                return user

        search_term = name or handle
        if search_term:
            search_lower = search_term.lower()
            for user in self._mock_users.values():
                if user.name.lower() == search_lower or user.handle.lower() == search_lower or user.username.lower() == search_lower:
                    return user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a mock channel."""
        if isinstance(identifier, TelegramChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = str(identifier.id)

        if identifier and not id:
            id = str(identifier)

        if id:
            channel = self._mock_channels.get(id) or self.channels.get_by_id(id)
            if channel:
                return channel

        if name:
            name_lower = name.lower()
            for channel in self._mock_channels.values():
                if channel.name.lower() == name_lower:
                    return channel

        return None

    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[Union[str, Message]] = None,
        after: Optional[Union[str, Message]] = None,
    ) -> List[Message]:
        """Fetch mock messages from a channel."""
        channel_id = channel.id if isinstance(channel, Channel) else str(channel)
        messages = self._mock_messages.get(channel_id, [])

        before_id = before.id if isinstance(before, Message) else before
        after_id = after.id if isinstance(after, Message) else after

        if before_id:
            messages = [m for m in messages if int(m.id) < int(before_id)]
        if after_id:
            messages = [m for m in messages if int(m.id) > int(after_id)]

        messages = sorted(messages, key=lambda m: int(m.id), reverse=True)
        return messages[:limit]

    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> TelegramMessage:
        """Send a mock message."""
        channel_id = channel.id if isinstance(channel, Channel) else str(channel)

        # Normalize thread / reply_to (matches production backend)
        thread_val = self._extract_thread_id(kwargs.pop("thread", None))
        if thread_val is None and "thread_id" in kwargs:
            thread_val = kwargs.pop("thread_id")
        reply_to_id = self._extract_reply_to_id(kwargs.pop("reply_to", None))

        self._message_counter += 1
        message_id = str(1000000 + self._message_counter)

        message = TelegramMessage(
            id=message_id,
            content=content,
            message_id=int(message_id),
            chat_id=channel_id,
            created_at=datetime.now(timezone.utc),
            author=TelegramUser(id="bot_user"),
            channel=TelegramChannel(id=channel_id),
            thread=Thread(id=thread_val) if thread_val else None,
        )
        if reply_to_id:
            message.metadata["reply_to_message_id"] = reply_to_id
        self._sent_messages.append(message)
        return message

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> TelegramMessage:
        """Edit a mock message."""
        if isinstance(message, Message):
            message_id = message.id
            channel_id = message.channel.id if message.channel else (channel.id if isinstance(channel, Channel) else channel or "")
        else:
            message_id = message
            channel_id = channel.id if isinstance(channel, Channel) else (channel or "")

        edited_msg = TelegramMessage(
            id=message_id,
            content=content,
            message_id=int(message_id),
            chat_id=channel_id,
            created_at=datetime.now(timezone.utc),
            author=TelegramUser(id="bot_user"),
            channel=TelegramChannel(id=channel_id) if channel_id else None,
            is_edited=True,
        )
        self._edited_messages.append(edited_msg)
        return edited_msg

    async def delete_message(
        self,
        message: Union[str, Message],
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Delete a mock message."""
        if isinstance(message, Message):
            message_id = message.id
            channel_id = message.channel.id if message.channel else (channel.id if isinstance(channel, Channel) else channel or "")
        else:
            message_id = message
            channel_id = channel.id if isinstance(channel, Channel) else (channel or "")

        self._deleted_messages.append({"channel_id": channel_id, "message_id": message_id})
        if channel_id in self._mock_messages:
            self._mock_messages[channel_id] = [m for m in self._mock_messages[channel_id] if m.id != message_id]

    async def forward_message(
        self,
        message: Union[str, Message],
        to_channel: Union[str, Channel],
        *,
        include_attribution: bool = True,
        prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> TelegramMessage:
        """Forward a mock message."""
        if isinstance(message, str):
            raise ValueError("forward_message requires a Message object, not just a message ID.")

        dest_channel_id = to_channel.id if isinstance(to_channel, Channel) else str(to_channel)

        content_parts = []
        if prefix:
            content_parts.append(prefix)
        if include_attribution:
            author_name = message.author.name if message.author else "Unknown"
            channel_name = message.channel.name if message.channel else "unknown chat"
            content_parts.append(f"<i>Forwarded from {channel_name} by {author_name}</i>\n")
        content_parts.append(message.content)

        forwarded_content = "".join(content_parts)

        self._message_counter += 1
        message_id = str(1000000 + self._message_counter)

        forwarded_msg = TelegramMessage(
            id=message_id,
            content=forwarded_content,
            message_id=int(message_id),
            chat_id=dest_channel_id,
            created_at=datetime.now(timezone.utc),
            author=TelegramUser(id="bot_user"),
            channel=TelegramChannel(id=dest_channel_id),
            message_type=MessageType.FORWARD,
        )
        forwarded_msg.forwarded_from = message

        self._sent_messages.append(forwarded_msg)

        if dest_channel_id not in self._mock_messages:
            self._mock_messages[dest_channel_id] = []
        self._mock_messages[dest_channel_id].append(forwarded_msg)

        return forwarded_msg

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set mock presence."""
        self._presence_updates.append(
            {
                "status": status,
                "status_text": status_text,
                **kwargs,
            }
        )

    async def get_presence(self, user: Union[str, User]) -> Optional[Presence]:
        """Get mock presence for a user."""
        user_id = user.id if isinstance(user, User) else user
        return self._mock_presence.get(user_id)

    async def add_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Add a mock reaction."""
        if isinstance(message, Message):
            message_id = message.id
            channel_id = message.channel.id if message.channel else (channel.id if isinstance(channel, Channel) else channel or "")
        else:
            message_id = message
            channel_id = channel.id if isinstance(channel, Channel) else (channel or "")

        self._reactions.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji,
                "action": "add",
            }
        )

    async def remove_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Remove a mock reaction."""
        if isinstance(message, Message):
            message_id = message.id
            channel_id = message.channel.id if message.channel else (channel.id if isinstance(channel, Channel) else channel or "")
        else:
            message_id = message
            channel_id = channel.id if isinstance(channel, Channel) else (channel or "")

        self._reactions.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji,
                "action": "remove",
            }
        )

    async def create_dm(
        self,
        users: List[Union[str, User]],
    ) -> Optional[str]:
        """Create a mock DM channel."""
        user_ids = []
        for user in users:
            if isinstance(user, TelegramUser):
                user_ids.append(user.id)
            elif hasattr(user, "id"):
                user_ids.append(user.id)
            else:
                user_ids.append(str(user))

        self._created_dms.append(user_ids)

        # In Telegram, DM chat ID is the user's ID
        return user_ids[0] if user_ids else None
