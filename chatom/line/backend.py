"""LINE Messaging API backend."""

import asyncio
import base64
import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, ClassVar
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import Field, PrivateAttr

from ..backend import BackendBase
from ..base import LINE_CAPABILITIES, BackendCapabilities, Channel, Message, Presence, PresenceStatus, User
from ..format import Format
from .channel import LineChannel
from .config import LineConfig
from .mention import mention_channel as _mention_channel, mention_user as _mention_user
from .message import LineMessage
from .presence import LinePresence
from .user import LineUser

__all__ = ("LINE_CAPABILITIES", "LineBackend")


class LineBackend(BackendBase):
    """Backend for LINE Official Account bots.

    LINE delivers incoming messages only by webhook. ``process_webhook``
    validates and queues those events; ``fetch_messages`` returns events kept
    by this backend process because LINE exposes no history endpoint.
    """

    name: ClassVar[str] = "line"
    display_name: ClassVar[str] = "LINE"
    format: ClassVar[Format] = Format.PLAINTEXT
    user_class: ClassVar[type] = LineUser
    channel_class: ClassVar[type] = LineChannel
    presence_class: ClassVar[type] = LinePresence

    capabilities: BackendCapabilities | None = LINE_CAPABILITIES
    config: LineConfig = Field(default_factory=LineConfig)

    _bot_user_id: str | None = PrivateAttr(default=None)
    _message_queue: asyncio.Queue[LineMessage] = PrivateAttr(default_factory=asyncio.Queue)
    _message_cache: dict[str, list[LineMessage]] = PrivateAttr(default_factory=dict)

    @property
    def bot_user_id(self) -> str | None:
        return self._bot_user_id

    def _request_json(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self.config.channel_access_token_str
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = json.dumps(data).encode() if data is not None else None
        request = Request(f"{self.config.api_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                payload = response.read()
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise ConnectionError(f"LINE API request failed ({exc.code}): {detail}") from exc
        return json.loads(payload) if payload else {}

    async def connect(self) -> None:
        if not self.config.channel_access_token_str:
            raise ValueError("channel_access_token is required in LineConfig")
        bot = await asyncio.to_thread(self._request_json, "GET", "/v2/bot/info")
        self._bot_user_id = str(bot.get("userId", "")) or None
        if self._bot_user_id:
            self.users.add(LineUser.from_api(bot))
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False
        self._bot_user_id = None

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise ConnectionError("Not connected to LINE. Call connect() first.")

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> User | None:
        self._ensure_connected()
        if isinstance(identifier, LineUser):
            return identifier
        user_id = id or (identifier.id if isinstance(identifier, User) else identifier)
        if user_id:
            cached = self.users.get_by_id(str(user_id))
            if cached and cached.name:
                return cached
            try:
                data = await asyncio.to_thread(self._request_json, "GET", f"/v2/bot/profile/{quote(str(user_id))}")
            except ConnectionError:
                return cached
            user = LineUser.from_api(data)
            self.users.add(user)
            return user
        for user in self.users.all():
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
    ) -> Channel | None:
        self._ensure_connected()
        if isinstance(identifier, LineChannel):
            return identifier
        channel_id = id or (identifier.id if isinstance(identifier, Channel) else identifier)
        if channel_id:
            cached = self.channels.get_by_id(str(channel_id))
            if cached and cached.name:
                return cached
            try:
                data = await asyncio.to_thread(self._request_json, "GET", f"/v2/bot/group/{quote(str(channel_id))}/summary")
            except ConnectionError:
                return cached
            channel = LineChannel.from_group_summary(data)
            self.channels.add(channel)
            return channel
        if name:
            for channel in self.channels.all():
                if channel.name.casefold() == name.casefold():
                    return channel
        return None

    @staticmethod
    def _bound_time(value: str | Message | datetime | None) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, Message):
            return value.created_at
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
        messages: list[Message] = list(reversed(self._message_cache.get(channel_id, [])))
        before_time = self._bound_time(before)
        after_time = self._bound_time(after)
        if before_time:
            messages = [message for message in messages if message.created_at and message.created_at <= before_time]
        if after_time:
            messages = [message for message in messages if message.created_at and message.created_at >= after_time]
        if isinstance(before, str):
            messages = (
                messages[messages.index(next(message for message in messages if message.id == before)) + 1 :]
                if any(message.id == before for message in messages)
                else []
            )
        if isinstance(after, str):
            messages = (
                messages[: messages.index(next(message for message in messages if message.id == after))]
                if any(message.id == after for message in messages)
                else []
            )
        return messages[:limit]

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> Message:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        reply_token = kwargs.get("reply_token")
        reply_to = kwargs.get("reply_to")
        native_message: dict[str, Any] = {"type": "text", "text": content}
        if isinstance(reply_to, LineMessage) and reply_to.quote_token:
            native_message["quoteToken"] = reply_to.quote_token
        if reply_token:
            path = "/v2/bot/message/reply"
            payload = {"replyToken": reply_token, "messages": [native_message]}
        else:
            path = "/v2/bot/message/push"
            payload = {"to": channel_id, "messages": [native_message]}
        data = await asyncio.to_thread(self._request_json, "POST", path, payload)
        cached_channel = self.channels.get_by_id(channel_id)
        line_channel = cached_channel if isinstance(cached_channel, LineChannel) else LineChannel(id=channel_id)
        message = LineMessage.from_api_response(data, content=content, channel=line_channel)
        self._message_cache.setdefault(channel_id, []).append(message)
        return message

    def process_webhook(self, body: str | bytes, signature: str) -> list[LineMessage]:
        """Verify a LINE webhook request and enqueue its message events."""
        raw = body.encode() if isinstance(body, str) else body
        secret = self.config.channel_secret_str
        if not secret:
            raise ValueError("channel_secret is required to process LINE webhooks")
        expected = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid LINE webhook signature")

        parsed = json.loads(raw)
        messages: list[LineMessage] = []
        for event in parsed.get("events", []):
            message = LineMessage.from_webhook_event(event)
            if message is None or message.channel is None:
                continue
            channel = message.channel
            if isinstance(channel, LineChannel):
                self.channels.add(channel)
            if isinstance(message.author, LineUser):
                self.users.add(message.author)
            self._message_cache.setdefault(channel.id, []).append(message)
            self._message_queue.put_nowait(message)
            messages.append(message)
        return messages

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[Message]:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel) if channel is not None else None
        while self.connected:
            message = await self._message_queue.get()
            if channel_id and message.channel_id != channel_id:
                continue
            if skip_own and self._bot_user_id and message.author_id == self._bot_user_id:
                continue
            yield message

    async def get_bot_info(self) -> User | None:
        if not self._bot_user_id:
            return None
        return self.users.get_by_id(self._bot_user_id)

    async def get_presence(self, user: str | User) -> Presence | None:
        user_id = await self._resolve_user_id(user)
        return LinePresence(user=LineUser(id=user_id), status=PresenceStatus.UNKNOWN)

    def mention_user(self, user: User) -> str:
        return _mention_user(LineUser.model_validate(user.model_dump()))

    def mention_channel(self, channel: Channel) -> str:
        return _mention_channel(LineChannel.model_validate(channel.model_dump()))
