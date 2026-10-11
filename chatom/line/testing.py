"""In-memory LINE backend for tests."""

from datetime import UTC, datetime
from typing import Any

from pydantic import PrivateAttr

from ..base import Channel, Message, User
from .backend import LineBackend
from .channel import LineChannel, LineSourceType
from .message import LineMessage
from .user import LineUser

__all__ = ("MockLineBackend",)


class MockLineBackend(LineBackend):
    """LINE backend with network operations replaced by memory stores."""

    _sent_messages: list[LineMessage] = PrivateAttr(default_factory=list)
    _counter: int = PrivateAttr(default=0)

    async def connect(self) -> None:
        self._bot_user_id = "line-bot"
        self.users.add(LineUser(id="line-bot", name="LINE Bot", is_bot=True))
        self.connected = True

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> User | None:
        user_id = id or (identifier.id if isinstance(identifier, User) else identifier)
        if user_id:
            return self.users.get_by_id(str(user_id))
        return next((user for user in self.users.all() if name and user.name == name), None)

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> Channel | None:
        channel_id = id or (identifier.id if isinstance(identifier, Channel) else identifier)
        if channel_id:
            return self.channels.get_by_id(str(channel_id))
        return next((channel for channel in self.channels.all() if name and channel.name == name), None)

    def add_mock_user(self, id: str, name: str, **kwargs: Any) -> LineUser:
        user = LineUser(id=id, name=name, **kwargs)
        self.users.add(user)
        return user

    def add_mock_channel(self, id: str, name: str, source_type: LineSourceType = LineSourceType.GROUP) -> LineChannel:
        channel = LineChannel(id=id, name=name, source_type=source_type)
        self.channels.add(channel)
        self._message_cache.setdefault(id, [])
        return channel

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> Message:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        self._counter += 1
        cached_channel = self.channels.get_by_id(channel_id)
        line_channel = cached_channel if isinstance(cached_channel, LineChannel) else LineChannel(id=channel_id)
        message = LineMessage(
            id=f"line-{self._counter}",
            message_id=f"line-{self._counter}",
            content=content,
            channel=line_channel,
            author=LineUser(id="line-bot", name="LINE Bot", is_bot=True),
            created_at=datetime.now(UTC),
            backend="line",
        )
        self._message_cache.setdefault(channel_id, []).append(message)
        self._sent_messages.append(message)
        return message
