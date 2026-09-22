"""Zulip backend implementation."""

import asyncio
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import Field, PrivateAttr

from ..backend import BackendBase
from ..base import (
    ZULIP_CAPABILITIES,
    Avatar,
    BackendCapabilities,
    Channel,
    ChannelType,
    Emoji,
    Message,
    PresenceStatus,
    Reaction,
    Thread,
    User,
)
from ..format.variant import Format
from .channel import ZulipChannel
from .config import ZulipConfig
from .message import ZulipMessage
from .presence import ZulipPresence, ZulipPresenceStatus
from .user import ZulipUser

__all__ = ("ZULIP_CAPABILITIES", "ZulipBackend")


class ZulipBackend(BackendBase):
    """Backend using Zulip's official synchronous Python client."""

    name: ClassVar[str] = "zulip"
    display_name: ClassVar[str] = "Zulip"
    format: ClassVar[Format] = Format.MARKDOWN
    mention_pattern: ClassVar[re.Pattern[str] | None] = re.compile(r"@\*\*[^*|]+\|([0-9]+)\*\*")

    user_class: ClassVar[type] = ZulipUser
    channel_class: ClassVar[type] = ZulipChannel
    message_class: ClassVar[type] = ZulipMessage
    presence_class: ClassVar[type] = ZulipPresence

    capabilities: BackendCapabilities | None = ZULIP_CAPABILITIES
    config: ZulipConfig = Field(default_factory=ZulipConfig)

    _client: Any = PrivateAttr(default=None)
    _bot_user_id: str | None = PrivateAttr(default=None)
    _bot_user: ZulipUser | None = PrivateAttr(default=None)

    async def _call(self, method: Any, *args: Any, **kwargs: Any) -> dict:
        response = await asyncio.to_thread(method, *args, **kwargs)
        if not isinstance(response, dict):
            raise TypeError("Zulip client returned a non-object response")
        if response.get("result") == "error":
            raise RuntimeError(f"Zulip API error: {response.get('msg', 'unknown error')}")
        return response

    def _ensure_connected(self) -> None:
        if not self.connected or self._client is None:
            raise ConnectionError("Not connected to Zulip. Call connect() first.")

    async def connect(self) -> None:
        """Create the SDK client and verify credentials with ``get_profile``."""
        if self._client is None:
            try:
                import zulip
            except ImportError as exc:
                raise ImportError("zulip is required for the Zulip backend. Install with: pip install zulip") from exc

            if self.config.config_file:
                self._client = zulip.Client(config_file=self.config.config_file, client=self.config.client_name)
            else:
                if not self.config.site or not self.config.email or not self.config.api_key_str:
                    raise ValueError("site, email, and api_key are required when config_file is not set")
                self._client = zulip.Client(
                    site=self.config.site,
                    email=self.config.email,
                    api_key=self.config.api_key_str,
                    client=self.config.client_name,
                    insecure=self.config.insecure,
                )

        profile = await self._call(self._client.get_profile)
        self._bot_user = self._user_from_api(profile)
        self._bot_user_id = self._bot_user.id
        self.users.add(self._bot_user)
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False
        self._client = None
        self._bot_user = None
        self._bot_user_id = None

    @staticmethod
    def _user_from_api(data: dict) -> ZulipUser:
        email = data.get("email", data.get("delivery_email", "")) or ""
        avatar_url = data.get("avatar_url") or ""
        return ZulipUser(
            id=str(data.get("user_id", data.get("id", ""))),
            name=data.get("full_name", data.get("name", "")) or "",
            display_name=data.get("full_name", data.get("name", "")) or "",
            handle=email.split("@", 1)[0] if email else "",
            email=email,
            avatar=Avatar(url=avatar_url) if avatar_url else None,
            is_bot=bool(data.get("is_bot", False)),
            role=data.get("role"),
            is_active=bool(data.get("is_active", True)),
            is_admin=bool(data.get("is_admin", False)),
            is_owner=bool(data.get("is_owner", False)),
            timezone=data.get("timezone", "") or "",
        )

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> ZulipUser | None:
        self._ensure_connected()
        if isinstance(identifier, ZulipUser):
            id = identifier.id
        elif isinstance(identifier, User):
            id = identifier.id or id
        elif identifier is not None:
            id = str(identifier)

        if id:
            cached = self.users.get_by_id(id)
            if isinstance(cached, ZulipUser):
                return cached
            response = await self._call(self._client.get_user_by_id, int(id))
            data = response.get("user")
            if data:
                user = self._user_from_api(data)
                self.users.add(user)
                return user
            return None

        response = await self._call(self._client.get_users)
        users = response.get("members", response.get("users", []))
        for data in users:
            user = self._user_from_api(data)
            self.users.add(user)
            if email and user.email.casefold() == email.casefold():
                return user
            if handle and user.handle.casefold() == handle.lstrip("@").casefold():
                return user
            if name and user.name.casefold() == name.casefold():
                return user
        return None

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> ZulipChannel | None:
        self._ensure_connected()
        if isinstance(identifier, Channel):
            id = identifier.id or id
            name = identifier.name or name
        elif identifier is not None:
            id = str(identifier)

        if id:
            cached = self.channels.get_by_id(id)
            if isinstance(cached, ZulipChannel):
                return cached

        response = await self._call(self._client.get_streams, include_all_active=True, include_default=True)
        for data in response.get("streams", []):
            channel = ZulipChannel.from_api(data)
            self.channels.add(channel)
            if id and channel.id == id:
                return channel
            if name and channel.name.casefold() == name.casefold():
                return channel
        return None

    @staticmethod
    def _topic_thread(channel: ZulipChannel, topic: str) -> Thread:
        return Thread(id=f"{channel.id}:{topic}", name=topic, parent_channel=channel)

    def _direct_channel(self, recipients: list[dict]) -> ZulipChannel:
        users = [self._user_from_api(item) for item in recipients]
        if self._bot_user_id:
            users = [user for user in users if user.id != self._bot_user_id]
        channel_id = "dm:" + ",".join(sorted(user.id for user in users))
        channel_type = ChannelType.DIRECT if len(users) == 1 else ChannelType.GROUP
        return ZulipChannel(id=channel_id, name=", ".join(user.name for user in users), channel_type=channel_type, users=users)

    def _message_from_api(self, data: dict) -> ZulipMessage:
        message_type = data.get("type", "stream")
        author = self._user_from_api(
            {
                "user_id": data.get("sender_id", ""),
                "full_name": data.get("sender_full_name", ""),
                "email": data.get("sender_email", ""),
                "avatar_url": data.get("avatar_url", ""),
            }
        )
        self.users.add(author)

        topic = data.get("topic", data.get("subject", "")) or ""
        if message_type in ("stream", "channel"):
            channel = ZulipChannel(
                id=str(data.get("stream_id", "")),
                name=data.get("display_recipient", "") if isinstance(data.get("display_recipient"), str) else "",
            )
            thread = self._topic_thread(channel, topic)
        else:
            recipients = data.get("display_recipient", [])
            channel = self._direct_channel(recipients if isinstance(recipients, list) else [])
            thread = None
        self.channels.add(channel)

        grouped_reactions: dict[tuple[str, str, str], list[ZulipUser]] = {}
        for item in data.get("reactions", []) or []:
            key = (item.get("emoji_name", ""), item.get("emoji_code", ""), item.get("reaction_type", ""))
            grouped_reactions.setdefault(key, []).append(self._user_from_api(item))
        reactions = [
            Reaction(emoji=Emoji(name=name, id=code, is_custom=reaction_type == "realm_emoji"), count=len(users), users=users)
            for (name, code, reaction_type), users in grouped_reactions.items()
        ]

        timestamp = data.get("timestamp")
        created_at = datetime.fromtimestamp(timestamp, tz=UTC) if timestamp is not None else None
        content = data.get("content", "") or ""
        is_html = data.get("content_type") == "text/html"
        return ZulipMessage(
            id=str(data.get("id", "")),
            content=content,
            formatted_content=content if is_html else "",
            author=author,
            channel=channel,
            thread=thread,
            created_at=created_at,
            is_edited=bool(data.get("last_edit_timestamp") or data.get("edit_history")),
            backend="zulip",
            raw=data,
            topic=topic,
            recipient_id=data.get("recipient_id"),
            sender_email=data.get("sender_email", "") or "",
            client=data.get("client", "") or "",
            flags=data.get("flags", []) or [],
            zulip_reactions=data.get("reactions", []) or [],
            reactions=reactions,
        )

    @staticmethod
    def _bound_id(value: str | Message | datetime | None) -> str | None:
        if value is None or isinstance(value, datetime):
            return None
        return value.id if isinstance(value, Message) else str(value)

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | Message | datetime | None = None,
        after: str | Message | datetime | None = None,
    ) -> list[Message]:
        """Fetch channel history and return newest messages first."""
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        before_id = self._bound_id(before)
        after_id = self._bound_id(after)
        request: dict[str, Any] = {
            "anchor": before_id or after_id or "newest",
            "num_before": 0 if after_id and not before_id else limit,
            "num_after": limit if after_id and not before_id else 0,
            "include_anchor": not (before_id or after_id),
            "narrow": [{"operator": "channel", "operand": int(channel_id) if channel_id.isdigit() else channel_id}],
            "apply_markdown": False,
        }
        response = await self._call(self._client.get_messages, request)
        messages: list[Message] = [self._message_from_api(item) for item in response.get("messages", [])]
        if after_id:
            messages = [message for message in messages if int(message.id) > int(after_id)]
        if before_id:
            messages = [message for message in messages if int(message.id) < int(before_id)]
        if isinstance(after, datetime):
            after_dt = after if after.tzinfo else after.replace(tzinfo=UTC)
            messages = [message for message in messages if message.created_at and message.created_at >= after_dt]
        if isinstance(before, datetime):
            before_dt = before if before.tzinfo else before.replace(tzinfo=UTC)
            messages = [message for message in messages if message.created_at and message.created_at <= before_dt]
        return sorted(messages, key=lambda message: int(message.id or 0), reverse=True)[:limit]

    @staticmethod
    def _topic_from_thread(thread: Any) -> str | None:
        if isinstance(thread, Thread):
            return thread.name or (thread.id.split(":", 1)[1] if ":" in thread.id else thread.id)
        if isinstance(thread, Message):
            return thread.thread.name if thread.thread else getattr(thread, "topic", "") or None
        if thread is not None:
            value = str(thread)
            return value.split(":", 1)[1] if ":" in value else value
        return None

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> ZulipMessage:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        thread = kwargs.pop("thread", None)
        reply_to = kwargs.pop("reply_to", None)
        topic = kwargs.pop("topic", None) or self._topic_from_thread(thread) or self._topic_from_thread(reply_to)

        if isinstance(channel, Channel) and channel.is_dm:
            recipients = [int(user.id) if user.id.isdigit() else user.email for user in channel.users]
            request = {"type": "private", "to": recipients, "content": content}
            message_channel = ZulipChannel.model_validate(channel.model_dump())
            message_thread = None
        elif channel_id.startswith("dm:"):
            recipients = [int(value) if value.isdigit() else value for value in channel_id[3:].split(",") if value]
            request = {"type": "private", "to": recipients, "content": content}
            message_channel = ZulipChannel(id=channel_id, channel_type=ChannelType.GROUP)
            message_thread = None
        else:
            destination: int | str = int(channel_id) if channel_id.isdigit() else channel_id
            topic = topic or self.config.default_topic
            request = {"type": "stream", "to": destination, "topic": topic, "content": content}
            channel_obj = channel if isinstance(channel, ZulipChannel) else await self.fetch_channel(id=channel_id)
            message_channel = channel_obj or ZulipChannel(id=channel_id)
            message_thread = self._topic_thread(message_channel, topic)

        response = await self._call(self._client.send_message, request)
        return ZulipMessage(
            id=str(response.get("id", response.get("message_id", ""))),
            content=content,
            author=self._bot_user,
            channel=message_channel,
            thread=message_thread,
            created_at=datetime.now(UTC),
            backend="zulip",
            topic=topic or "",
        )

    async def edit_message(
        self,
        message: str | Message,
        content: str,
        channel: str | Channel | None = None,
        **kwargs: Any,
    ) -> ZulipMessage:
        self._ensure_connected()
        message_id = message.id if isinstance(message, Message) else str(message)
        await self._call(self._client.update_message, {"message_id": int(message_id), "content": content, **kwargs})
        if isinstance(channel, Channel):
            message_channel: Channel | None = channel
        elif channel is not None:
            message_channel = Channel(id=str(channel))
        else:
            message_channel = None
        return ZulipMessage(
            id=message_id,
            content=content,
            channel=message.channel if isinstance(message, Message) else message_channel,
            thread=message.thread if isinstance(message, Message) else None,
            created_at=message.created_at if isinstance(message, Message) else None,
            is_edited=True,
            backend="zulip",
            topic=getattr(message, "topic", "") if isinstance(message, Message) else "",
        )

    async def delete_message(self, message: str | Message, channel: str | Channel | None = None) -> None:
        self._ensure_connected()
        message_id = message.id if isinstance(message, Message) else str(message)
        await self._call(self._client.delete_message, int(message_id))

    async def add_reaction(self, message: str | Message, emoji: str, channel: str | Channel | None = None) -> None:
        self._ensure_connected()
        message_id = message.id if isinstance(message, Message) else str(message)
        await self._call(self._client.add_reaction, {"message_id": int(message_id), "emoji_name": emoji.strip(":")})

    async def remove_reaction(self, message: str | Message, emoji: str, channel: str | Channel | None = None) -> None:
        self._ensure_connected()
        message_id = message.id if isinstance(message, Message) else str(message)
        await self._call(self._client.remove_reaction, {"message_id": int(message_id), "emoji_name": emoji.strip(":")})

    async def get_bot_info(self) -> ZulipUser | None:
        self._ensure_connected()
        return self._bot_user

    async def get_presence(self, user: str | User) -> ZulipPresence | None:
        self._ensure_connected()
        resolved = user if isinstance(user, User) else await self.fetch_user(id=str(user))
        if resolved is None or not resolved.email:
            return None
        response = await self._call(self._client.get_user_presence, resolved.email)
        entries = response.get("presence", {})
        selected_name = "aggregated" if "aggregated" in entries else max(entries, key=lambda key: entries[key].get("timestamp", 0), default="")
        selected = entries.get(selected_name, {})
        try:
            zulip_status = ZulipPresenceStatus(selected.get("status", "offline"))
        except ValueError:
            zulip_status = ZulipPresenceStatus.OFFLINE
        timestamp = selected.get("timestamp")
        return ZulipPresence(
            user=resolved,
            status=zulip_status.generic,
            zulip_status=zulip_status,
            client=selected_name or "aggregated",
            last_seen=datetime.fromtimestamp(timestamp, tz=UTC) if timestamp is not None else None,
        )

    async def set_presence(self, status: str, status_text: str | None = None, **kwargs: Any) -> None:
        self._ensure_connected()
        base_status = PresenceStatus(status) if status in PresenceStatus._value2member_map_ else PresenceStatus.UNKNOWN
        zulip_status = ZulipPresenceStatus.from_base(base_status)
        native_status = "active" if zulip_status == ZulipPresenceStatus.ACTIVE else "idle"
        await self._call(self._client.update_presence, {"status": native_status, "ping_only": False, "new_user_input": True})

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[ZulipMessage]:
        """Long-poll Zulip's registered message event queue."""
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel) if channel is not None else None
        channel_obj = await self.fetch_channel(id=channel_id) if channel_id else None
        narrow = [["stream", channel_obj.name if channel_obj and channel_obj.name else channel_id]] if channel_id else []
        registration = await self._call(self._client.register, ["message"], narrow)
        queue_id = registration["queue_id"]
        last_event_id = registration.get("last_event_id", -1)
        try:
            while True:
                response = await self._call(self._client.get_events, queue_id=queue_id, last_event_id=last_event_id)
                for event in response.get("events", []):
                    last_event_id = max(last_event_id, event.get("id", last_event_id))
                    if event.get("type") != "message":
                        continue
                    message = self._message_from_api(event.get("message", {}))
                    if channel_id and message.channel_id != channel_id:
                        continue
                    if skip_own and self._bot_user_id and message.author_id == self._bot_user_id:
                        continue
                    yield message
        finally:
            deregister = getattr(self._client, "deregister", None)
            if deregister is not None:
                await self._call(deregister, queue_id)
