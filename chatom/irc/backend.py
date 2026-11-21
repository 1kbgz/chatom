"""Async IRC/IRCv3 backend implemented with Python's stream primitives."""

import asyncio
import re
import ssl
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, ClassVar, cast

from pydantic import Field, PrivateAttr

from ..backend import BackendBase
from ..base import IRC_CAPABILITIES, BackendCapabilities, Channel, ChannelType, Message, MessageType, Presence, PresenceStatus, User
from ..format.variant import Format
from .channel import IRCChannel
from .config import IRCConfig
from .message import IRCMessage
from .presence import IRCPresence
from .user import IRCUser

__all__ = ("IRC_CAPABILITIES", "IRCBackend")

# RPL_ENDOFNAMES, or a numeric saying the JOIN was refused, ends the wait for a
# configured channel.
_JOIN_FINISHED = frozenset({"366", "403", "405", "471", "473", "474", "475"})

# A PRIVMSG is one line of at most 512 bytes, including the prefix the server
# adds when it relays the message, so long text is sent in smaller pieces.
_MAX_TEXT_BYTES = 400
# Characters RFC 2812 allows in a nickname. A nick counts as mentioned only
# when it is not part of a longer nick, the same rule clients use to highlight.
_NICK_CHARS = r"\w\-\[\]\\`^{}|"

# Pause between the lines of a multi-line message so a long reply does not
# trip the server's flood limit and get the bot disconnected.
_LINE_DELAY_SECONDS = 0.3


def _irc_lines(content: str) -> list[str]:
    """Split text into the non-blank pieces IRC can send as separate PRIVMSGs."""
    pieces: list[str] = []
    for line in content.splitlines():
        if not line.strip():
            continue
        while line:
            piece = line.encode()[:_MAX_TEXT_BYTES].decode(errors="ignore")
            pieces.append(piece)
            line = line[len(piece) :]
    return pieces


def _unescape_tag(value: str) -> str:
    replacements = {":": ";", "s": " ", "\\": "\\", "r": "\r", "n": "\n"}
    result: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            index += 1
            result.append(replacements.get(value[index], value[index]))
        else:
            result.append(value[index])
        index += 1
    return "".join(result)


def _parse_line(line: str) -> tuple[dict[str, str], str, str, list[str]]:
    """Parse an IRC protocol line into tags, prefix, command, and params."""
    tags: dict[str, str] = {}
    prefix = ""
    remainder = line.rstrip("\r\n")
    if remainder.startswith("@"):
        raw_tags, remainder = remainder[1:].split(" ", 1)
        for raw_tag in raw_tags.split(";"):
            key, separator, value = raw_tag.partition("=")
            tags[key] = _unescape_tag(value) if separator else ""
    if remainder.startswith(":"):
        prefix, remainder = remainder[1:].split(" ", 1)
    if " :" in remainder:
        leading, trailing = remainder.split(" :", 1)
        parts = leading.split()
        parts.append(trailing)
    else:
        parts = remainder.split()
    if not parts:
        return tags, prefix, "", []
    return tags, prefix, parts[0].upper(), parts[1:]


class IRCBackend(BackendBase):
    """Portable IRC backend with optional IRCv3 history negotiation."""

    name: ClassVar[str] = "irc"
    display_name: ClassVar[str] = "IRC"
    format: ClassVar[Format] = Format.PLAINTEXT
    user_class: ClassVar[type] = IRCUser
    channel_class: ClassVar[type] = IRCChannel
    presence_class: ClassVar[type] = IRCPresence

    capabilities: BackendCapabilities | None = IRC_CAPABILITIES
    config: IRCConfig = Field(default_factory=IRCConfig)

    _reader: asyncio.StreamReader | None = PrivateAttr(default=None)
    _writer: asyncio.StreamWriter | None = PrivateAttr(default=None)
    _reader_task: asyncio.Task[None] | None = PrivateAttr(default=None)
    _welcome: asyncio.Event | None = PrivateAttr(default=None)
    _messages: asyncio.Queue[IRCMessage | None] = PrivateAttr(default_factory=asyncio.Queue)
    _history: dict[str, list[IRCMessage]] = PrivateAttr(default_factory=dict)
    _presence: dict[str, IRCPresence] = PrivateAttr(default_factory=dict)
    _server_capabilities: set[str] = PrivateAttr(default_factory=set)
    _enabled_capabilities: set[str] = PrivateAttr(default_factory=set)
    _history_waiters: dict[str, asyncio.Future[None]] = PrivateAttr(default_factory=dict)
    _history_batches: dict[str, str] = PrivateAttr(default_factory=dict)
    _pending_joins: dict[str, asyncio.Event] = PrivateAttr(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}  # noqa: RUF012

    @property
    def bot_user_id(self) -> str:
        return self.config.nickname

    @property
    def supports_server_history(self) -> bool:
        return bool({"draft/chathistory", "chathistory"} & self._enabled_capabilities)

    async def connect(self) -> None:
        if self.connected:
            return
        if not self.config.server:
            raise ValueError("server is required in IRCConfig")
        ssl_context: ssl.SSLContext | bool | None = None
        if self.config.use_tls:
            ssl_context = ssl.create_default_context()
            if not self.config.tls_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        self._reader, self._writer = await asyncio.open_connection(
            self.config.server,
            self.config.port,
            ssl=ssl_context,
        )
        self._messages = asyncio.Queue()
        self._welcome = asyncio.Event()
        self._pending_joins = {channel.casefold(): asyncio.Event() for channel in self.config.channels}
        self._reader_task = asyncio.create_task(self._read_loop())
        if self.config.password_str:
            await self._send_command("PASS", self.config.password_str)
        await self._send_command("CAP", "LS", "302")
        await self._send_command("NICK", self.config.nickname)
        await self._send_command("USER", self.config.username, "0", "*", trailing=self.config.realname)
        try:
            await asyncio.wait_for(self._welcome.wait(), timeout=self.config.timeout)
        except Exception:
            await self.disconnect()
            raise
        # Wait for each configured channel's member list so fetch_user() can
        # resolve who is there. A channel that never answers does not fail connect.
        try:
            await asyncio.wait_for(
                asyncio.gather(*(event.wait() for event in self._pending_joins.values())),
                timeout=self.config.timeout,
            )
        except TimeoutError:
            pass

    async def disconnect(self) -> None:
        writer, task = self._writer, self._reader_task
        if writer is not None and not writer.is_closing():
            try:
                await self._send_command("QUIT", trailing="chatom disconnect")
            except (ConnectionError, OSError):
                pass
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
        self._writer = None
        self._reader = None
        self._reader_task = None
        self.connected = False
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._messages.put(None)

    def _ensure_connected(self) -> None:
        if not self.connected or self._writer is None:
            raise ConnectionError("Not connected to IRC. Call connect() first.")

    async def _send_command(self, command: str, *params: str, trailing: str | None = None) -> None:
        if self._writer is None:
            raise ConnectionError("IRC connection is not open")
        if any("\r" in value or "\n" in value for value in (command, *params, trailing or "")):
            raise ValueError("IRC commands cannot contain CR or LF")
        line = " ".join((command, *params))
        if trailing is not None:
            line += f" :{trailing}"
        encoded = (line + "\r\n").encode("utf-8")
        if len(encoded) > 512:
            raise ValueError("IRC protocol line exceeds 512 bytes")
        self._writer.write(encoded)
        await self._writer.drain()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while line := await self._reader.readline():
                decoded = line.decode("utf-8", errors="replace").rstrip("\r\n")
                await self._handle_line(decoded)
        finally:
            self.connected = False
            await self._messages.put(None)

    async def _handle_line(self, line: str) -> None:
        tags, prefix, command, params = _parse_line(line)
        if command == "PING":
            await self._send_command("PONG", trailing=params[-1] if params else "")
            return
        if command == "CAP":
            await self._handle_cap(params)
            return
        if command == "001":
            self.connected = True
            if self._welcome is not None:
                self._welcome.set()
            for channel in self.config.channels:
                await self._send_command("JOIN", channel)
            return
        if command == "BATCH":
            self._handle_batch(params)
            return
        if command in {"PRIVMSG", "NOTICE"} and len(params) >= 2:
            message = self._make_message(tags, prefix, command, params[0], params[1])
            self._remember_message(message)
            # Messages replayed inside a CHATHISTORY batch are history, not live
            # traffic; they belong in the store only, or streaming consumers
            # would reprocess them every time fetch_messages() runs.
            if tags.get("batch") not in self._history_batches:
                await self._messages.put(message)
        elif command == "353" and len(params) >= 4:
            # RPL_NAMREPLY: the channel's member list, each nick carrying zero or
            # more membership prefixes such as @ or +.
            for entry in params[-1].split():
                self._remember_nick(entry.lstrip("~&@%+"))
        elif command in _JOIN_FINISHED and len(params) >= 2:
            event = self._pending_joins.pop(params[1].casefold(), None)
            if event is not None:
                event.set()
        elif command == "JOIN" and prefix:
            self._remember_nick(IRCUser.from_prefix(prefix))
        elif command == "NICK" and prefix and params:
            self._remember_nick(params[-1])
        elif command == "AWAY" and prefix:
            user = IRCUser.from_prefix(prefix)
            # AWAY without a message means the user is back.
            self._presence[user.id] = IRCPresence(
                user=user,
                status=PresenceStatus.IDLE if params else PresenceStatus.ONLINE,
                away_message=params[-1] if params else "",
            )

    def _remember_nick(self, user: "str | IRCUser") -> None:
        """Add a nick seen in a channel to the user directory, except the bot itself."""
        if isinstance(user, str):
            # A bare nick must not replace a cached user that has a full hostmask.
            if self.users.get_by_id(user) is not None:
                return
            user = IRCUser(id=user, name=user, handle=user, nickname=user)
        if user.id and user.id.casefold() != self.config.nickname.casefold():
            self.users.add(user)

    async def _handle_cap(self, params: list[str]) -> None:
        if len(params) < 2:
            return
        subcommand = params[1].upper()
        raw_caps = params[-1].lstrip(":")
        capabilities = {cap.split("=", 1)[0] for cap in raw_caps.split()}
        if subcommand == "LS":
            self._server_capabilities.update(capabilities)
            if len(params) >= 4 and params[-2] == "*":
                return
            desired = self._server_capabilities & {
                "batch",
                "chathistory",
                "draft/chathistory",
                "message-tags",
                "server-time",
            }
            if desired:
                await self._send_command("CAP", "REQ", trailing=" ".join(sorted(desired)))
            else:
                await self._send_command("CAP", "END")
        elif subcommand == "ACK":
            self._enabled_capabilities.update(capabilities)
            await self._send_command("CAP", "END")
        elif subcommand == "NAK":
            await self._send_command("CAP", "END")

    def _handle_batch(self, params: list[str]) -> None:
        if not params:
            return
        batch_token = params[0]
        batch_id = batch_token[1:]
        if batch_token.startswith("+") and len(params) >= 3 and "chathistory" in params[1]:
            self._history_batches[batch_id] = params[2]
        elif batch_token.startswith("-"):
            channel_id = self._history_batches.pop(batch_id, "")
            waiter = self._history_waiters.pop(channel_id, None)
            if waiter is not None and not waiter.done():
                waiter.set_result(None)

    def _make_message(self, tags: dict[str, str], prefix: str, command: str, target: str, content: str) -> IRCMessage:
        author = IRCUser.from_prefix(prefix)
        self.users.add(author)
        is_channel = target.startswith(("#", "&", "+", "!"))
        channel_id = target if is_channel else author.id
        channel = IRCChannel(
            id=channel_id,
            name=channel_id,
            channel_type=ChannelType.PUBLIC if is_channel else ChannelType.DIRECT,
        )
        self.channels.add(channel)
        timestamp = datetime.now(UTC)
        if tags.get("time"):
            try:
                timestamp = datetime.fromisoformat(tags["time"])
            except ValueError:
                pass
        message_id = tags.get("msgid") or uuid.uuid4().hex
        self._presence[author.id] = IRCPresence(user=author, status=PresenceStatus.ONLINE, last_seen=timestamp)
        nickname = self.config.nickname
        mentions: list[User] = []
        if author.id.casefold() != nickname.casefold() and re.search(
            rf"(?<![{_NICK_CHARS}]){re.escape(nickname)}(?![{_NICK_CHARS}])", content, re.IGNORECASE
        ):
            mentions.append(IRCUser(id=nickname, name=nickname, handle=nickname, nickname=nickname, is_bot=True))
        return IRCMessage(
            id=message_id,
            content=content,
            author=author,
            channel=channel,
            mentions=mentions,
            created_at=timestamp,
            message_type=MessageType.SYSTEM if command == "NOTICE" else MessageType.DEFAULT,
            is_system=command == "NOTICE",
            backend=self.name,
            command=command,
            target=target,
            irc_tags=tags,
            hostmask=prefix,
            raw={"tags": tags, "prefix": prefix, "command": command, "params": [target, content]},
        )

    def _remember_message(self, message: IRCMessage) -> None:
        assert message.channel is not None
        history = self._history.setdefault(message.channel.id, [])
        if not any(existing.id == message.id for existing in history):
            history.append(message)

    async def fetch_user(
        self,
        identifier: str | User | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> IRCUser | None:
        if isinstance(identifier, IRCUser):
            return identifier
        lookup_id = id or (str(identifier) if identifier is not None else None)
        user = self.users.lookup(id=lookup_id, name=name, email=email, handle=handle)
        if user is not None:
            return IRCUser.model_validate(user.model_dump())
        if lookup_id and lookup_id.casefold() == self.config.nickname.casefold():
            return IRCUser(
                id=self.config.nickname, name=self.config.nickname, handle=self.config.nickname, nickname=self.config.nickname, is_bot=True
            )
        return None

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> IRCChannel | None:
        if isinstance(identifier, IRCChannel):
            return identifier
        channel_id = id or (str(identifier) if identifier is not None else None)
        cached = self.channels.lookup(id=channel_id, name=name)
        if cached is not None:
            return IRCChannel.model_validate(cached.model_dump())
        channel_id = channel_id or name
        if channel_id and channel_id.startswith(("#", "&", "+", "!")):
            channel = IRCChannel(id=channel_id, name=channel_id)
            self.channels.add(channel)
            return channel
        return None

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | Message | datetime | None = None,
        after: str | Message | datetime | None = None,
    ) -> list[Message]:
        channel_id = channel.id if isinstance(channel, Channel) else str(channel)
        if self.connected and self.supports_server_history and before is None and after is None:
            loop = asyncio.get_running_loop()
            waiter = loop.create_future()
            self._history_waiters[channel_id] = waiter
            await self._send_command("CHATHISTORY", "LATEST", channel_id, "*", str(limit))
            try:
                await asyncio.wait_for(waiter, timeout=self.config.timeout)
            except TimeoutError:
                self._history_waiters.pop(channel_id, None)
        messages = list(self._history.get(channel_id, []))

        def bound_time(value: str | Message | datetime | None) -> datetime | None:
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=UTC)
            if isinstance(value, Message):
                return value.created_at
            if isinstance(value, str):
                match = next((message for message in messages if message.id == value), None)
                return match.created_at if match else None
            return None

        before_time, after_time = bound_time(before), bound_time(after)
        if before_time is not None:
            messages = [message for message in messages if message.created_at and message.created_at <= before_time]
        if after_time is not None:
            messages = [message for message in messages if message.created_at and message.created_at >= after_time]
        messages.sort(key=lambda message: message.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        return cast(list[Message], messages[:limit])

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> IRCMessage:
        self._ensure_connected()
        channel_id = await self._resolve_channel_id(channel)
        lines = _irc_lines(content)
        if not lines:
            raise ValueError("IRC message content cannot be empty")
        for index, line in enumerate(lines):
            if index:
                await asyncio.sleep(_LINE_DELAY_SECONDS)
            await self._send_command("PRIVMSG", channel_id, trailing=line)
        timestamp = datetime.now(UTC)
        author = IRCUser(id=self.config.nickname, name=self.config.nickname, handle=self.config.nickname, nickname=self.config.nickname, is_bot=True)
        message = IRCMessage(
            id=uuid.uuid4().hex,
            content=content,
            author=author,
            channel=IRCChannel(id=channel_id, name=channel_id),
            created_at=timestamp,
            backend=self.name,
            target=channel_id,
            hostmask=author.hostmask,
        )
        self._remember_message(message)
        return message

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[IRCMessage]:
        """Stream new messages received from the IRC connection.

        IRC protocol messages enter the queue only as they arrive, so there is
        no separate history replay to suppress when ``skip_history`` is true.
        Server history is requested only by :meth:`fetch_messages`.
        """
        if not self.connected:
            raise ConnectionError("Not connected to IRC. Call connect() first.")
        channel_id = await self._resolve_channel_id(channel) if channel is not None else None
        bot_user_id = self.config.nickname.casefold()
        channels = {channel_id} if channel_id is not None else None
        async for message in self.listen_for_messages(channels=channels):
            if skip_own and message.author is not None and message.author.id.casefold() == bot_user_id:
                continue
            yield message

    async def listen_for_messages(self, channels: set[str] | None = None, **kwargs: Any) -> AsyncIterator[IRCMessage]:
        """Compatibility helper for listening to one or more channel IDs."""
        while True:
            message = await self._messages.get()
            if message is None:
                return
            if channels is None or (message.channel is not None and message.channel.id in channels):
                yield message

    async def get_presence(self, user: str | User) -> Presence | None:
        user_id = user.id if isinstance(user, User) else user
        return self._presence.get(user_id)

    async def set_presence(self, status: str, status_text: str | None = None, **kwargs: Any) -> None:
        self._ensure_connected()
        normalized = status.lower()
        away = normalized in {"away", "idle", "dnd", "offline", "invisible"}
        await self._send_command("AWAY", trailing=(status_text or "Away") if away else None)
        own_user = await self.fetch_user(id=self.config.nickname)
        self._presence[self.config.nickname] = IRCPresence(
            user=own_user,
            status=PresenceStatus.IDLE if away else PresenceStatus.ONLINE,
            away_message=(status_text or "Away") if away else "",
        )

    async def get_bot_info(self) -> IRCUser:
        user = await self.fetch_user(id=self.config.nickname)
        assert user is not None
        return user
