"""In-memory Zulip backend for tests and local development."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import PrivateAttr

from ..base import Channel, ChannelType, Message, PresenceStatus, User
from .backend import ZulipBackend
from .channel import ZulipChannel
from .message import ZulipMessage
from .presence import ZulipPresence, ZulipPresenceStatus
from .user import ZulipUser

__all__ = ("MockZulipBackend",)


class MockZulipBackend(ZulipBackend):
    """Network-free Zulip backend preserving stream/topic semantics."""

    name: ClassVar[str] = "mock_zulip"
    display_name: ClassVar[str] = "Mock Zulip"

    _mock_users: dict[str, ZulipUser] = PrivateAttr(default_factory=dict)
    _mock_channels: dict[str, ZulipChannel] = PrivateAttr(default_factory=dict)
    _mock_messages: dict[str, list[ZulipMessage]] = PrivateAttr(default_factory=dict)
    _mock_presence: dict[str, ZulipPresence] = PrivateAttr(default_factory=dict)
    _sent_messages: list[ZulipMessage] = PrivateAttr(default_factory=list)
    _deleted_messages: list[str] = PrivateAttr(default_factory=list)
    _added_reactions: list[tuple[str, str]] = PrivateAttr(default_factory=list)
    _removed_reactions: list[tuple[str, str]] = PrivateAttr(default_factory=list)
    _event_queue: asyncio.Queue[ZulipMessage] = PrivateAttr(default_factory=asyncio.Queue)
    _message_counter: int = PrivateAttr(default=0)

    @property
    def sent_messages(self) -> list[ZulipMessage]:
        return self._sent_messages

    @property
    def deleted_messages(self) -> list[str]:
        return self._deleted_messages

    @property
    def added_reactions(self) -> list[tuple[str, str]]:
        return self._added_reactions

    async def connect(self) -> None:
        self.connected = True
        if self._bot_user is None:
            self._bot_user = ZulipUser(id="1", name="chatom", email="chatom@example.com", is_bot=True)
            self._bot_user_id = self._bot_user.id
            self._mock_users[self._bot_user.id] = self._bot_user
            self.users.add(self._bot_user)

    async def disconnect(self) -> None:
        self.connected = False

    def add_mock_user(self, id: str, name: str, email: str = "", *, is_bot: bool = False) -> ZulipUser:
        user = ZulipUser(id=id, name=name, email=email, handle=email.split("@", 1)[0] if email else name.casefold().replace(" ", ""), is_bot=is_bot)
        self._mock_users[id] = user
        self.users.add(user)
        return user

    def add_mock_channel(self, id: str, name: str, *, description: str = "", invite_only: bool = False) -> ZulipChannel:
        channel = ZulipChannel(
            id=id,
            name=name,
            topic=description,
            description=description,
            invite_only=invite_only,
            channel_type=ChannelType.PRIVATE if invite_only else ChannelType.PUBLIC,
        )
        self._mock_channels[id] = channel
        self._mock_messages.setdefault(id, [])
        self.channels.add(channel)
        return channel

    def add_mock_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        *,
        topic: str = "chatom",
        message_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> ZulipMessage:
        self._message_counter += 1
        message_id = message_id or str(self._message_counter)
        channel = self._mock_channels.get(channel_id, ZulipChannel(id=channel_id))
        message = ZulipMessage(
            id=message_id,
            content=content,
            author=self._mock_users.get(user_id, ZulipUser(id=user_id)),
            channel=channel,
            thread=self._topic_thread(channel, topic),
            topic=topic,
            created_at=timestamp or datetime.now(UTC),
            backend="zulip",
        )
        self._mock_messages.setdefault(channel_id, []).append(message)
        return message

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> ZulipUser | None:
        if isinstance(identifier, User):
            id = identifier.id or id
        elif identifier is not None:
            id = str(identifier)
        if id:
            return self._mock_users.get(id)
        for user in self._mock_users.values():
            if name and user.name.casefold() == name.casefold():
                return user
            if email and user.email.casefold() == email.casefold():
                return user
            if handle and user.handle.casefold() == handle.lstrip("@").casefold():
                return user
        return None

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> ZulipChannel | None:
        if isinstance(identifier, Channel):
            id = identifier.id or id
            name = identifier.name or name
        elif identifier is not None:
            id = str(identifier)
        if id:
            return self._mock_channels.get(id)
        if name:
            return next((channel for channel in self._mock_channels.values() if channel.name.casefold() == name.casefold()), None)
        return None

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | Message | datetime | None = None,
        after: str | Message | datetime | None = None,
    ) -> list[Message]:
        channel_id = channel.id if isinstance(channel, Channel) else str(channel)
        messages: list[Message] = list(self._mock_messages.get(channel_id, []))
        before_id = before.id if isinstance(before, Message) else before
        after_id = after.id if isinstance(after, Message) else after
        if isinstance(before_id, str):
            messages = [message for message in messages if int(message.id) < int(before_id)]
        elif isinstance(before_id, datetime):
            messages = [message for message in messages if message.created_at and message.created_at <= before_id]
        if isinstance(after_id, str):
            messages = [message for message in messages if int(message.id) > int(after_id)]
        elif isinstance(after_id, datetime):
            messages = [message for message in messages if message.created_at and message.created_at >= after_id]
        return sorted(messages, key=lambda message: int(message.id), reverse=True)[:limit]

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> ZulipMessage:
        channel_id = channel.id if isinstance(channel, Channel) else str(channel)
        topic = kwargs.get("topic") or self._topic_from_thread(kwargs.get("thread")) or self.config.default_topic
        self._message_counter += 1
        channel_obj = self._mock_channels.get(channel_id, ZulipChannel(id=channel_id))
        message = ZulipMessage(
            id=str(self._message_counter),
            content=content,
            author=self._bot_user,
            channel=channel_obj,
            thread=None if channel_obj.is_dm else self._topic_thread(channel_obj, topic),
            topic="" if channel_obj.is_dm else topic,
            created_at=datetime.now(UTC),
            backend="zulip",
        )
        self._sent_messages.append(message)
        self._mock_messages.setdefault(channel_id, []).append(message)
        return message

    async def edit_message(
        self,
        message: str | Message,
        content: str,
        channel: str | Channel | None = None,
        **kwargs: Any,
    ) -> ZulipMessage:
        message_id = message.id if isinstance(message, Message) else str(message)
        for messages in self._mock_messages.values():
            for stored in messages:
                if stored.id == message_id:
                    stored.content = content
                    stored.is_edited = True
                    return stored
        raise RuntimeError(f"Message {message_id} not found")

    async def delete_message(self, message: str | Message, channel: str | Channel | None = None) -> None:
        message_id = message.id if isinstance(message, Message) else str(message)
        self._deleted_messages.append(message_id)
        for channel_id, messages in self._mock_messages.items():
            self._mock_messages[channel_id] = [stored for stored in messages if stored.id != message_id]

    async def add_reaction(self, message: str | Message, emoji: str, channel: str | Channel | None = None) -> None:
        message_id = message.id if isinstance(message, Message) else str(message)
        self._added_reactions.append((message_id, emoji.strip(":")))

    async def remove_reaction(self, message: str | Message, emoji: str, channel: str | Channel | None = None) -> None:
        message_id = message.id if isinstance(message, Message) else str(message)
        self._removed_reactions.append((message_id, emoji.strip(":")))

    async def get_presence(self, user: str | User) -> ZulipPresence | None:
        user_id = user.id if isinstance(user, User) else str(user)
        return self._mock_presence.get(user_id)

    async def set_presence(self, status: str, status_text: str | None = None, **kwargs: Any) -> None:
        if self._bot_user is None:
            return
        base_status = PresenceStatus(status)
        self._mock_presence[self._bot_user.id] = ZulipPresence(
            user=self._bot_user,
            status=base_status,
            status_text=status_text or "",
            zulip_status=ZulipPresenceStatus.from_base(base_status),
        )

    async def queue_message(self, message: ZulipMessage) -> None:
        await self._event_queue.put(message)

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[ZulipMessage]:
        channel_id = channel.id if isinstance(channel, Channel) else str(channel) if channel is not None else None
        while True:
            message = await self._event_queue.get()
            if channel_id and message.channel_id != channel_id:
                continue
            if skip_own and self._bot_user_id and message.author_id == self._bot_user_id:
                continue
            yield message
