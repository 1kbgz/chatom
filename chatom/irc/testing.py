"""In-memory IRC backend for tests and consumers."""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import PrivateAttr

from ..base import Channel, PresenceStatus
from .backend import IRCBackend
from .channel import IRCChannel
from .message import IRCMessage
from .presence import IRCPresence
from .user import IRCUser

__all__ = ("MockIRCBackend",)


class MockIRCBackend(IRCBackend):
    """IRC backend with no network connection."""

    _sent_messages: list[IRCMessage] = PrivateAttr(default_factory=list)

    @property
    def sent_messages(self) -> list[IRCMessage]:
        return self._sent_messages

    async def connect(self) -> None:
        self._messages = asyncio.Queue()
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False
        await self._messages.put(None)

    def add_mock_user(self, id: str, name: str | None = None, **kwargs: Any) -> IRCUser:
        user = IRCUser(id=id, name=name or id, handle=id, nickname=id, **kwargs)
        self.users.add(user)
        return user

    def add_mock_channel(self, id: str, topic: str = "") -> IRCChannel:
        channel = IRCChannel(id=id, name=id, topic=topic)
        self.channels.add(channel)
        return channel

    def add_mock_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        *,
        message_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> IRCMessage:
        message = IRCMessage(
            id=message_id or uuid.uuid4().hex,
            content=content,
            author=IRCUser(id=user_id, name=user_id, handle=user_id, nickname=user_id),
            channel=IRCChannel(id=channel_id, name=channel_id),
            created_at=timestamp or datetime.now(UTC),
            backend="irc",
            target=channel_id,
        )
        self._remember_message(message)
        return message

    async def emit_message(self, channel_id: str, user_id: str, content: str) -> IRCMessage:
        message = self.add_mock_message(channel_id, user_id, content)
        await self._messages.put(message)
        return message

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> IRCMessage:
        if not self.connected:
            raise ConnectionError("Not connected to IRC. Call connect() first.")
        channel_id = channel.id if isinstance(channel, Channel) else str(channel)
        message = IRCMessage(
            id=uuid.uuid4().hex,
            content=content,
            author=IRCUser(
                id=self.config.nickname,
                name=self.config.nickname,
                handle=self.config.nickname,
                nickname=self.config.nickname,
                is_bot=True,
            ),
            channel=IRCChannel(id=channel_id, name=channel_id),
            created_at=datetime.now(UTC),
            backend="irc",
            target=channel_id,
        )
        self._sent_messages.append(message)
        self._remember_message(message)
        return message

    def set_mock_presence(self, user_id: str, status: PresenceStatus) -> IRCPresence:
        presence = IRCPresence(user=IRCUser(id=user_id, nickname=user_id), status=status)
        self._presence[user_id] = presence
        return presence
