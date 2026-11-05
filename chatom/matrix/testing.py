"""In-memory Matrix backend for tests."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from pydantic import PrivateAttr

from ..base import Channel, ChannelType, Message, MessageReference, MessageType, Thread, User
from .backend import MatrixBackend
from .channel import MatrixChannel
from .message import MatrixMessage
from .presence import MatrixPresence, MatrixPresenceState
from .user import MatrixUser

__all__ = ("MockMatrixBackend",)


class MockMatrixBackend(MatrixBackend):
    """Matrix backend with in-memory rooms, profiles, and events."""

    _mock_users: dict[str, MatrixUser] = PrivateAttr(default_factory=dict)
    _mock_channels: dict[str, MatrixChannel] = PrivateAttr(default_factory=dict)
    _mock_messages: dict[str, list[MatrixMessage]] = PrivateAttr(default_factory=dict)
    _mock_presence: dict[str, MatrixPresence] = PrivateAttr(default_factory=dict)
    _sent_messages: list[MatrixMessage] = PrivateAttr(default_factory=list)
    _edited_messages: list[MatrixMessage] = PrivateAttr(default_factory=list)
    _deleted_messages: list[tuple[str, str]] = PrivateAttr(default_factory=list)
    _event_queue: asyncio.Queue[MatrixMessage] = PrivateAttr(default_factory=asyncio.Queue)
    _message_counter: int = PrivateAttr(default=0)

    async def connect(self) -> None:
        """Connect without network access or matrix-nio."""
        self.connected = True
        self._bot_user_id = self.config.user_id or "@chatom:example.org"

    async def disconnect(self) -> None:
        """Disconnect mock backend."""
        self.connected = False
        self._bot_user_id = None

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise ConnectionError("Not connected to Matrix. Call connect() first.")

    def add_mock_user(
        self,
        id: str,
        name: str = "",
        *,
        avatar_mxc: str = "",
        is_bot: bool = False,
    ) -> MatrixUser:
        """Add a Matrix user profile."""
        user = MatrixUser(
            id=id,
            name=name or id,
            display_name=name or id,
            handle=id,
            avatar_mxc=avatar_mxc,
            is_bot=is_bot,
        )
        self._mock_users[id] = user
        self.users.add(user)
        return user

    def add_mock_channel(
        self,
        id: str,
        name: str = "",
        *,
        canonical_alias: str = "",
        topic: str = "",
        encrypted: bool = False,
    ) -> MatrixChannel:
        """Add a Matrix room."""
        channel = MatrixChannel(
            id=id,
            name=name or id,
            topic=topic,
            canonical_alias=canonical_alias,
            encrypted=encrypted,
            channel_type=ChannelType.PRIVATE,
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
        event_id: str | None = None,
        created_at: datetime | None = None,
        thread_id: str | None = None,
        reply_to: str | None = None,
        queue: bool = False,
    ) -> MatrixMessage:
        """Add an existing Matrix room message."""
        if event_id is None:
            self._message_counter += 1
            event_id = f"$event{self._message_counter}"
        message = MatrixMessage(
            id=event_id,
            content=content,
            author=self._mock_users.get(user_id) or MatrixUser(id=user_id),
            channel=self._mock_channels.get(channel_id) or MatrixChannel(id=channel_id),
            thread=Thread(id=thread_id) if thread_id else None,
            reference=(MessageReference(message_id=reply_to, channel_id=channel_id) if reply_to else None),
            message_type=MessageType.REPLY if reply_to else MessageType.DEFAULT,
            created_at=created_at or datetime.now(UTC),
            backend="matrix",
        )
        self._mock_messages.setdefault(channel_id, []).insert(0, message)
        if queue:
            self._event_queue.put_nowait(message)
        return message

    @property
    def sent_messages(self) -> list[MatrixMessage]:
        return list(self._sent_messages)

    @property
    def edited_messages(self) -> list[MatrixMessage]:
        return list(self._edited_messages)

    @property
    def deleted_messages(self) -> list[tuple[str, str]]:
        return list(self._deleted_messages)

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> MatrixUser | None:
        self._ensure_connected()
        if isinstance(identifier, MatrixUser):
            return identifier
        if identifier is not None and hasattr(identifier, "id"):
            id = str(identifier.id)
        elif isinstance(identifier, str) and not id:
            id = identifier
        if id:
            return self._mock_users.get(id)
        for user in self._mock_users.values():
            if name and user.name.casefold() == name.casefold():
                return user
            if handle and user.handle.casefold() == handle.casefold():
                return user
        return None

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> MatrixChannel | None:
        self._ensure_connected()
        if isinstance(identifier, MatrixChannel):
            return identifier
        if identifier is not None and hasattr(identifier, "id"):
            id = str(identifier.id)
        elif isinstance(identifier, str) and not id:
            id = identifier
        if id:
            if id.startswith("#"):
                return next((room for room in self._mock_channels.values() if room.canonical_alias == id), None)
            return self._mock_channels.get(id)
        if name:
            return next((room for room in self._mock_channels.values() if room.name.casefold() == name.casefold()), None)
        return None

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | Message | datetime | None = None,
        after: str | Message | datetime | None = None,
    ) -> list[Message]:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        messages: list[Message] = []
        messages.extend(self._mock_messages.get(channel_id, []))
        return self._filter_message_bounds(messages, before, after)[:limit]

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> MatrixMessage:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        room = self._mock_channels.get(channel_id)
        if room and room.encrypted:
            raise NotImplementedError("MatrixBackend MVP does not support end-to-end encrypted rooms")
        thread_id = self._extract_thread_id(kwargs.pop("thread", None)) or kwargs.pop("thread_id", None)
        reply_id = self._extract_reply_to_id(kwargs.pop("reply_to", None))
        formatted = kwargs.pop("formatted", True)
        payload = self._message_content(content, formatted)
        message = self.add_mock_message(
            channel_id,
            self._bot_user_id or "@chatom:example.org",
            payload["body"],
            thread_id=thread_id,
            reply_to=reply_id,
        )
        message.formatted_content = payload.get("formatted_body", "")
        self._sent_messages.append(message)
        return message

    async def edit_message(
        self,
        message: str | Message,
        content: str,
        channel: str | Channel | None = None,
        **kwargs: Any,
    ) -> MatrixMessage:
        self._ensure_connected()
        room_id, event_id = await self._resolve_message_id(message, channel)
        existing = next((item for item in self._mock_messages.get(room_id, []) if item.id == event_id), None)
        if existing is None:
            raise ValueError(f"Unknown Matrix event: {event_id}")
        existing.content = self._plain_fallback(content) if kwargs.pop("formatted", True) else content
        existing.formatted_content = content
        existing.is_edited = True
        existing.edited_at = datetime.now(UTC)
        self._edited_messages.append(existing)
        return existing

    async def delete_message(
        self,
        message: str | Message,
        channel: str | Channel | None = None,
    ) -> None:
        self._ensure_connected()
        room_id, event_id = await self._resolve_message_id(message, channel)
        self._mock_messages[room_id] = [item for item in self._mock_messages.get(room_id, []) if item.id != event_id]
        self._deleted_messages.append((room_id, event_id))

    def set_mock_presence(
        self,
        user_id: str,
        state: MatrixPresenceState = MatrixPresenceState.ONLINE,
        status_text: str = "",
    ) -> MatrixPresence:
        """Set a mock user's presence."""
        presence = MatrixPresence(
            user=self._mock_users.get(user_id) or MatrixUser(id=user_id),
            status=state.generic,
            status_text=status_text,
            matrix_presence=state,
            currently_active=state == MatrixPresenceState.ONLINE,
        )
        self._mock_presence[user_id] = presence
        return presence

    async def get_presence(self, user: str | User) -> MatrixPresence | None:
        self._ensure_connected()
        user_id = await self._resolve_user_id(user)
        return self._mock_presence.get(user_id)

    async def set_presence(
        self,
        status: str,
        status_text: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._ensure_connected()
        state = {
            "online": MatrixPresenceState.ONLINE,
            "idle": MatrixPresenceState.UNAVAILABLE,
            "away": MatrixPresenceState.UNAVAILABLE,
            "offline": MatrixPresenceState.OFFLINE,
        }.get(status)
        if state is None:
            raise ValueError(f"Unsupported Matrix presence: {status}")
        self.set_mock_presence(self._bot_user_id or "@chatom:example.org", state, status_text or "")

    async def get_bot_info(self) -> MatrixUser | None:
        if not self._bot_user_id:
            return None
        return self._mock_users.get(self._bot_user_id) or MatrixUser(id=self._bot_user_id, is_bot=True)

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[MatrixMessage]:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel) if channel is not None else None
        while True:
            message = await self._event_queue.get()
            if channel_id and message.channel_id != channel_id:
                continue
            if skip_own and message.author_id == self._bot_user_id:
                continue
            yield message
