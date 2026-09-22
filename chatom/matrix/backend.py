"""Matrix backend implementation using matrix-nio."""

import asyncio
import html
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from logging import getLogger
from typing import Any, ClassVar
from urllib.parse import quote

from pydantic import Field, PrivateAttr

from ..backend import BackendBase
from ..base import (
    MATRIX_CAPABILITIES,
    BackendCapabilities,
    Channel,
    ChannelType,
    Message,
    MessageReference,
    MessageType,
    PresenceStatus,
    Thread,
    User,
)
from ..format.variant import Format
from .channel import MatrixChannel
from .config import MatrixConfig
from .message import MatrixMessage
from .presence import MatrixPresence, MatrixPresenceState
from .user import MatrixUser

__all__ = ("MATRIX_CAPABILITIES", "MatrixBackend")

_log = getLogger(__name__)


class MatrixBackend(BackendBase):
    """Unencrypted Matrix client-server backend.

    End-to-end encryption is intentionally excluded from this MVP. Attempts to
    send into a room known to be encrypted fail explicitly.
    """

    name: ClassVar[str] = "matrix"
    display_name: ClassVar[str] = "Matrix"
    format: ClassVar[Format] = Format.HTML
    mention_pattern: ClassVar[re.Pattern[str] | None] = re.compile(r'https://matrix\.to/#/(@[^"<]+)')

    user_class: ClassVar[type] = MatrixUser
    channel_class: ClassVar[type] = MatrixChannel
    presence_class: ClassVar[type] = MatrixPresence

    capabilities: BackendCapabilities | None = MATRIX_CAPABILITIES
    config: MatrixConfig = Field(default_factory=MatrixConfig)

    _client: Any = PrivateAttr(default=None)
    _next_batch: str | None = PrivateAttr(default=None)
    _bot_user_id: str | None = PrivateAttr(default=None)

    @property
    def bot_user_id(self) -> str | None:
        """Return authenticated Matrix user ID."""
        return self._bot_user_id

    @property
    def bot_user_name(self) -> str | None:
        """Return localpart of authenticated Matrix user ID."""
        if not self._bot_user_id:
            return None
        return self._bot_user_id.removeprefix("@").partition(":")[0]

    async def connect(self) -> None:
        """Create a matrix-nio client and authenticate it."""
        try:
            from nio import AsyncClient
        except ImportError as exc:
            raise ImportError("matrix-nio is required for Matrix backend. Install with: pip install matrix-nio") from exc

        if not self.config.homeserver:
            raise ValueError("homeserver is required in MatrixConfig")
        if not self.config.user_id:
            raise ValueError("user_id is required in MatrixConfig")

        self._client = AsyncClient(
            self.config.homeserver,
            self.config.user_id,
            device_id=self.config.device_id or "",
            store_path=self.config.store_path or "",
        )

        if self.config.access_token_str:
            if not self.config.device_id:
                raise ValueError("device_id is required when using access_token")
            self._client.restore_login(
                self.config.user_id,
                self.config.device_id,
                self.config.access_token_str,
            )
        elif self.config.password_str:
            response = await self._client.login(
                self.config.password_str,
                device_name=self.config.device_name,
            )
            self._raise_for_error(response, "Matrix login failed")
        else:
            raise ValueError("access_token or password is required in MatrixConfig")

        response = await self._client.sync(timeout=0, full_state=True)
        self._raise_for_error(response, "Initial Matrix sync failed")
        self._next_batch = getattr(response, "next_batch", None)
        self._bot_user_id = getattr(self._client, "user_id", None) or self.config.user_id
        self._cache_nio_rooms()
        self.connected = True

    async def disconnect(self) -> None:
        """Close the Matrix HTTP session."""
        if self._client is not None:
            await self._client.close()
        self._client = None
        self._next_batch = None
        self._bot_user_id = None
        self.connected = False

    def _ensure_connected(self) -> None:
        if not self.connected or self._client is None:
            raise ConnectionError("Not connected to Matrix. Call connect() first.")

    @staticmethod
    def _raise_for_error(response: Any, prefix: str) -> None:
        if response.__class__.__name__.endswith("Error"):
            message = getattr(response, "message", None) or repr(response)
            raise RuntimeError(f"{prefix}: {message}")

    @staticmethod
    def _source(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        source = getattr(value, "source", None)
        return source if isinstance(source, dict) else {}

    def _room_from_nio(self, room: Any) -> MatrixChannel:
        room_id = getattr(room, "room_id", "")
        channel = MatrixChannel(
            id=room_id,
            name=getattr(room, "display_name", None) or getattr(room, "name", None) or room_id,
            topic=getattr(room, "topic", None) or "",
            canonical_alias=getattr(room, "canonical_alias", None) or "",
            encrypted=bool(getattr(room, "encrypted", False)),
            member_count=len(getattr(room, "users", {}) or {}),
            channel_type=ChannelType.PRIVATE,
        )
        return channel

    def _cache_nio_rooms(self) -> None:
        for room in (getattr(self._client, "rooms", {}) or {}).values():
            channel = self._room_from_nio(room)
            self.channels.add(channel)

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> MatrixUser | None:
        """Fetch a Matrix profile by MXID, or search cached profiles."""
        self._ensure_connected()
        if isinstance(identifier, MatrixUser):
            return identifier
        if identifier is not None and hasattr(identifier, "id"):
            id = str(identifier.id)
        elif isinstance(identifier, str) and not id:
            id = identifier

        cached = self.users.lookup(id=id, name=name, handle=handle, email=email)
        if cached:
            return cached if isinstance(cached, MatrixUser) else MatrixUser.model_validate(cached.model_dump())
        if not id:
            return None

        response = await self._client.get_profile(id)
        if response.__class__.__name__.endswith("Error"):
            return None
        display_name = getattr(response, "displayname", None) or id
        user = MatrixUser(
            id=id,
            name=display_name,
            display_name=display_name,
            handle=id,
            avatar_mxc=getattr(response, "avatar_url", None) or "",
        )
        self.users.add(user)
        return user

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> MatrixChannel | None:
        """Fetch a joined Matrix room by room ID, alias, or cached name."""
        self._ensure_connected()
        if isinstance(identifier, MatrixChannel):
            return identifier
        if identifier is not None and hasattr(identifier, "id"):
            id = str(identifier.id)
        elif isinstance(identifier, str) and not id:
            id = identifier

        if name:
            cached = self.channels.lookup(name=name)
            if cached:
                return cached if isinstance(cached, MatrixChannel) else MatrixChannel.model_validate(cached.model_dump())
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached if isinstance(cached, MatrixChannel) else MatrixChannel.model_validate(cached.model_dump())

        if id and id.startswith("#"):
            response = await self._client.room_resolve_alias(id)
            if response.__class__.__name__.endswith("Error"):
                return None
            id = getattr(response, "room_id", None)
        if id:
            room = (getattr(self._client, "rooms", {}) or {}).get(id)
            if room is None:
                return None
            channel = self._room_from_nio(room)
            self.channels.add(channel)
            return channel

        if name:
            self._cache_nio_rooms()
            cached = self.channels.lookup(name=name)
            return cached if isinstance(cached, MatrixChannel) else None
        return None

    def _parse_message_event(self, event: Any, room_id: str) -> MatrixMessage | None:
        source = self._source(event)
        event_type = source.get("type") or getattr(event, "type", "m.room.message")
        if event_type != "m.room.message":
            return None
        content = source.get("content") or {}
        body = content.get("body", getattr(event, "body", ""))
        event_id = source.get("event_id") or getattr(event, "event_id", "")
        sender = source.get("sender") or getattr(event, "sender", "")
        timestamp = source.get("origin_server_ts") or getattr(event, "server_timestamp", None)
        created_at = None
        if timestamp is not None:
            created_at = datetime.fromtimestamp(float(timestamp) / 1000, tz=UTC)

        relation = content.get("m.relates_to") or {}
        reply_event_id = (relation.get("m.in_reply_to") or {}).get("event_id")
        thread_id = relation.get("event_id") if relation.get("rel_type") == "m.thread" else None
        new_content = content.get("m.new_content") if relation.get("rel_type") == "m.replace" else None
        if new_content:
            body = new_content.get("body", body)

        return MatrixMessage(
            id=event_id,
            content=body,
            formatted_content=(new_content or content).get("formatted_body", ""),
            author=MatrixUser(id=sender, name=sender, handle=sender) if sender else None,
            channel=MatrixChannel(id=room_id, name=room_id),
            thread=Thread(id=thread_id) if thread_id else None,
            reference=(MessageReference(message_id=reply_event_id, channel_id=room_id) if reply_event_id else None),
            message_type=MessageType.REPLY if reply_event_id else MessageType.DEFAULT,
            created_at=created_at,
            is_edited=bool(new_content),
            msgtype=(new_content or content).get("msgtype", "m.text"),
            event_type=event_type,
            transaction_id=(source.get("unsigned") or {}).get("transaction_id", ""),
            relates_to=relation,
            backend="matrix",
            raw=source,
        )

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | Message | datetime | None = None,
        after: str | Message | datetime | None = None,
    ) -> list[Message]:
        """Fetch recent unencrypted room messages, newest first."""
        self._ensure_connected()
        from nio import MessageDirection

        room_id = await self._resolve_channel_id(channel)
        if not self._next_batch:
            response = await self._client.sync(timeout=0)
            self._raise_for_error(response, "Matrix sync failed")
            self._next_batch = getattr(response, "next_batch", None)
        if not self._next_batch:
            return []

        response = await self._client.room_messages(
            room_id,
            start=self._next_batch,
            direction=MessageDirection.back,
            limit=max(limit, 1),
        )
        self._raise_for_error(response, "Matrix message history failed")
        messages: list[Message] = []
        for event in getattr(response, "chunk", []):
            message = self._parse_message_event(event, room_id)
            if message is not None:
                messages.append(message)
        return self._filter_message_bounds(messages, before, after)[:limit]

    @staticmethod
    def _filter_message_bounds(
        messages: list[Message],
        before: str | Message | datetime | None,
        after: str | Message | datetime | None,
    ) -> list[Message]:
        def bound_id(value: Any) -> str | None:
            if isinstance(value, Message):
                return value.id
            return value if isinstance(value, str) else None

        before_id = bound_id(before)
        after_id = bound_id(after)
        if before_id and any(message.id == before_id for message in messages):
            messages = messages[next(i for i, message in enumerate(messages) if message.id == before_id) :]
        if after_id and any(message.id == after_id for message in messages):
            messages = messages[: next(i for i, message in enumerate(messages) if message.id == after_id) + 1]
        if isinstance(before, datetime):
            messages = [message for message in messages if message.created_at and message.created_at <= before]
        if isinstance(after, datetime):
            messages = [message for message in messages if message.created_at and message.created_at >= after]
        return messages

    @staticmethod
    def _plain_fallback(content: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", "", content))

    @staticmethod
    def _translate_mentions(content: str) -> str:
        """Translate generic HTML mention nodes to Matrix matrix.to links."""

        def user_replacement(match: re.Match[str]) -> str:
            user_id, label = match.groups()
            href = f"https://matrix.to/#/{quote(html.unescape(user_id), safe=':@')}"
            return f'<a href="{href}">{label}</a>'

        def channel_replacement(match: re.Match[str]) -> str:
            channel_id, label = match.groups()
            href = f"https://matrix.to/#/{quote(html.unescape(channel_id), safe=':!#')}"
            return f'<a href="{href}">{label}</a>'

        content = re.sub(
            r'<span class="mention" data-user-id="([^"]+)">(.*?)</span>',
            user_replacement,
            content,
        )
        return re.sub(
            r'<span class="channel-mention" data-channel-id="([^"]+)">(.*?)</span>',
            channel_replacement,
            content,
        )

    def _ensure_unencrypted(self, room_id: str) -> None:
        cached = self.channels.get_by_id(room_id)
        room = (getattr(self._client, "rooms", {}) or {}).get(room_id)
        encrypted = bool(getattr(cached, "encrypted", False) or getattr(room, "encrypted", False))
        if encrypted:
            raise NotImplementedError("MatrixBackend MVP does not support end-to-end encrypted rooms")

    def _message_content(self, content: str, formatted: bool = True) -> dict:
        if not formatted:
            return {"msgtype": "m.text", "body": content}
        content = self._translate_mentions(content)
        return {
            "msgtype": "m.text",
            "body": self._plain_fallback(content),
            "format": "org.matrix.custom.html",
            "formatted_body": content,
        }

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> MatrixMessage:
        """Send an HTML-formatted Matrix room message."""
        self._ensure_connected()
        room_id = await self._resolve_channel_id(channel)
        self._ensure_unencrypted(room_id)
        payload = self._message_content(content, kwargs.pop("formatted", True))

        thread_id = self._extract_thread_id(kwargs.pop("thread", None)) or kwargs.pop("thread_id", None)
        reply_id = self._extract_reply_to_id(kwargs.pop("reply_to", None))
        if thread_id:
            payload["m.relates_to"] = {
                "rel_type": "m.thread",
                "event_id": thread_id,
                "is_falling_back": True,
                "m.in_reply_to": {"event_id": reply_id or thread_id},
            }
        elif reply_id:
            payload["m.relates_to"] = {"m.in_reply_to": {"event_id": reply_id}}

        response = await self._client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=payload,
            **kwargs,
        )
        self._raise_for_error(response, "Matrix send failed")
        event_id = getattr(response, "event_id", "")
        return MatrixMessage(
            id=event_id,
            content=payload["body"],
            formatted_content=payload.get("formatted_body", ""),
            author=MatrixUser(id=self._bot_user_id or self.config.user_id),
            channel=MatrixChannel(id=room_id, name=room_id),
            thread=Thread(id=thread_id) if thread_id else None,
            reference=(MessageReference(message_id=reply_id, channel_id=room_id) if reply_id else None),
            message_type=MessageType.REPLY if reply_id else MessageType.DEFAULT,
            relates_to=payload.get("m.relates_to", {}),
            backend="matrix",
        )

    async def edit_message(
        self,
        message: str | Message,
        content: str,
        channel: str | Channel | None = None,
        **kwargs: Any,
    ) -> MatrixMessage:
        """Replace a Matrix room message using an m.replace relation."""
        self._ensure_connected()
        room_id, event_id = await self._resolve_message_id(message, channel)
        self._ensure_unencrypted(room_id)
        new_content = self._message_content(content, kwargs.pop("formatted", True))
        payload = {
            "msgtype": "m.text",
            "body": f"* {new_content['body']}",
            "m.new_content": new_content,
            "m.relates_to": {"rel_type": "m.replace", "event_id": event_id},
        }
        response = await self._client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=payload,
            **kwargs,
        )
        self._raise_for_error(response, "Matrix edit failed")
        return MatrixMessage(
            id=getattr(response, "event_id", ""),
            content=new_content["body"],
            formatted_content=new_content.get("formatted_body", ""),
            author=MatrixUser(id=self._bot_user_id or self.config.user_id),
            channel=MatrixChannel(id=room_id, name=room_id),
            is_edited=True,
            relates_to=payload["m.relates_to"],
            backend="matrix",
        )

    async def delete_message(
        self,
        message: str | Message,
        channel: str | Channel | None = None,
    ) -> None:
        """Redact a Matrix event."""
        self._ensure_connected()
        room_id, event_id = await self._resolve_message_id(message, channel)
        response = await self._client.room_redact(room_id, event_id)
        self._raise_for_error(response, "Matrix redaction failed")

    async def get_bot_info(self) -> MatrixUser | None:
        """Return authenticated Matrix user profile."""
        if not self._bot_user_id:
            return None
        return await self.fetch_user(id=self._bot_user_id)

    async def get_presence(self, user: str | User) -> MatrixPresence | None:
        """Fetch Matrix presence for a user."""
        self._ensure_connected()
        user_id = await self._resolve_user_id(user)
        response = await self._client.get_presence(user_id)
        if response.__class__.__name__.endswith("Error"):
            return None
        state = MatrixPresenceState(getattr(response, "presence", "offline"))
        return MatrixPresence(
            user=MatrixUser(id=user_id),
            status=state.generic,
            status_text=getattr(response, "status_msg", None) or "",
            matrix_presence=state,
            currently_active=bool(getattr(response, "currently_active", False)),
            last_active_ago=getattr(response, "last_active_ago", None) or 0,
        )

    async def set_presence(
        self,
        status: str,
        status_text: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Set authenticated Matrix user's presence."""
        self._ensure_connected()
        state = {
            PresenceStatus.ONLINE.value: MatrixPresenceState.ONLINE.value,
            PresenceStatus.IDLE.value: MatrixPresenceState.UNAVAILABLE.value,
            PresenceStatus.DND.value: MatrixPresenceState.UNAVAILABLE.value,
            PresenceStatus.OFFLINE.value: MatrixPresenceState.OFFLINE.value,
            "away": MatrixPresenceState.UNAVAILABLE.value,
        }.get(status, status)
        if state not in {item.value for item in MatrixPresenceState}:
            raise ValueError(f"Unsupported Matrix presence: {status}")
        response = await self._client.set_presence(state, status_msg=status_text)
        self._raise_for_error(response, "Matrix presence update failed")

    @staticmethod
    def _sync_room_events(response: Any):
        rooms = getattr(response, "rooms", None)
        joined = getattr(rooms, "join", {}) if rooms is not None else {}
        for room_id, room_info in (joined or {}).items():
            timeline = getattr(room_info, "timeline", None)
            for event in getattr(timeline, "events", []) or []:
                yield room_id, event

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[MatrixMessage]:
        """Stream Matrix timeline events via /sync long polling."""
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel) if channel is not None else None
        since = self._next_batch if skip_history else None

        while True:
            try:
                response = await self._client.sync(
                    timeout=self.config.sync_timeout,
                    since=since,
                    full_state=False,
                )
                self._raise_for_error(response, "Matrix sync failed")
                since = getattr(response, "next_batch", None) or since
                self._next_batch = since
                for room_id, event in self._sync_room_events(response):
                    if channel_id and room_id != channel_id:
                        continue
                    message = self._parse_message_event(event, room_id)
                    if message is None:
                        continue
                    if skip_own and message.author_id == self._bot_user_id:
                        continue
                    yield message
            except asyncio.CancelledError:
                return

    async def listen_for_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
    ) -> AsyncIterator[MatrixMessage]:
        """Compatibility alias for real-time Matrix event listening."""
        async for message in self.stream_messages(channel=channel, skip_own=skip_own):
            yield message
