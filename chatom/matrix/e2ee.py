"""Matrix backend with end-to-end encryption, using matrix-sdk-python."""

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any

from pydantic import PrivateAttr

from ..base import Channel, ChannelType, Message, MessageReference, MessageType, Thread, User
from .backend import _MATRIX_TO_USER, MatrixBackend
from .channel import MatrixChannel
from .message import MatrixMessage
from .presence import MatrixPresence
from .user import MatrixUser

__all__ = ("MatrixE2EEBackend",)

_log = getLogger(__name__)


def _diff_items(diff: Any) -> list[Any]:
    if hasattr(diff, "values"):
        return list(diff.values)
    if hasattr(diff, "value"):
        return [diff.value]
    return []


def _apply_diff(items: list[Any], diff: Any) -> None:
    """Apply one timeline VectorDiff to a local copy of the timeline."""
    kind = type(diff).__name__.rpartition(".")[2]
    if kind == "APPEND":
        items.extend(diff.values)
    elif kind == "CLEAR":
        items.clear()
    elif kind == "INSERT":
        items.insert(diff.index, diff.value)
    elif kind == "POP_BACK":
        items.pop()
    elif kind == "POP_FRONT":
        items.pop(0)
    elif kind == "PUSH_BACK":
        items.append(diff.value)
    elif kind == "PUSH_FRONT":
        items.insert(0, diff.value)
    elif kind == "REMOVE":
        del items[diff.index]
    elif kind == "RESET":
        items[:] = diff.values
    elif kind == "SET":
        items[diff.index] = diff.value
    elif kind == "TRUNCATE":
        del items[diff.length :]


def _event_json(item: Any) -> tuple[Any, dict] | None:
    """Return the timeline event and its decrypted JSON, once the server has echoed it."""
    event = item.as_event()
    if event is None or not event.is_remote or not event.event_or_transaction_id.is_EVENT_ID():
        return None
    raw = event.lazy_provider.debug_info().original_json
    if not raw:
        return None
    return event, json.loads(raw)


class _Listener:
    """Forward callbacks from matrix-sdk threads to the backend's event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop, handler, *args):
        self._loop = loop
        self._handler = handler
        self._args = args

    def on_update(self, update: Any) -> None:
        self._loop.call_soon_threadsafe(self._handler, *self._args, update)


class _Room:
    def __init__(self, room: Any, timeline: Any, encrypted: bool):
        self.room = room
        self.timeline = timeline
        self.encrypted = encrypted
        self.items: list[Any] = []
        self.handles: list[Any] = []
        self.send_lock = asyncio.Lock()
        self.awaiting_local: list[asyncio.Future] = []
        self.awaiting_sent: dict[str, asyncio.Future] = {}


class MatrixE2EEBackend(MatrixBackend):
    """Matrix backend that reads and posts in end-to-end encrypted rooms.

    It needs ``store_path`` for the device's encryption keys and saves the
    login session there, so restarts reuse the same device. Set
    ``recovery_key`` to have a new device restore the account's
    cross-signing identity and sign itself; clients that exclude insecure
    devices only share room keys with signed devices.
    """

    _sdk: Any = PrivateAttr(default=None)
    _loop: Any = PrivateAttr(default=None)
    _rooms: dict[str, _Room] = PrivateAttr(default_factory=dict)
    _attaching: set[str] = PrivateAttr(default_factory=set)
    _sync_handle: Any = PrivateAttr(default=None)
    _subscribers: list[asyncio.Queue] = PrivateAttr(default_factory=list)
    _seen: set[str] = PrivateAttr(default_factory=set)
    _started_ms: int = PrivateAttr(default=0)

    async def connect(self) -> None:
        """Log in or restore the saved session, then start syncing."""
        try:
            import matrix_sdk_python
        except ImportError as exc:
            raise ImportError("matrix-sdk-python is required for encrypted Matrix rooms. Install with: pip install matrix-sdk-python") from exc

        if not self.config.homeserver:
            raise ValueError("homeserver is required in MatrixConfig")
        if not self.config.user_id:
            raise ValueError("user_id is required in MatrixConfig")
        if not self.config.store_path:
            raise ValueError("store_path is required for encrypted Matrix rooms")

        # The bindings are generated at build time, so type checkers cannot see their members.
        sdk: Any = matrix_sdk_python
        self._sdk = sdk
        self._loop = asyncio.get_running_loop()
        store = Path(self.config.store_path).expanduser()
        store.mkdir(parents=True, exist_ok=True)
        os.chmod(store, 0o700)
        self._client = await (
            sdk.ClientBuilder()
            .homeserver_url(self.config.homeserver)
            .session_paths(str(store / "data"), str(store / "cache"))
            .auto_enable_cross_signing(True)
            .auto_enable_backups(True)
            .build()
        )
        await self._login(store / "session.json")
        await self._client.sync_once_v2(sdk.SyncSettingsV2(timeout_ms=0))
        await self._verify_device()

        self._bot_user_id = self._client.user_id()
        self._started_ms = int(time.time() * 1000)
        for room in self._client.rooms():
            await self._attach(room)
        self._sync_handle = self._client.sync_v2(
            sdk.SyncSettingsV2(timeout_ms=self.config.sync_timeout),
            _Listener(self._loop, self._on_sync),
        )
        self.connected = True

    async def _login(self, session_file: Path) -> None:
        sdk = self._sdk
        if session_file.exists():
            saved = json.loads(session_file.read_text())
            saved["sliding_sync_version"] = sdk.SlidingSyncVersion[saved["sliding_sync_version"]]
            await self._client.restore_session(sdk.Session(**saved))
            return
        if self.config.access_token_str:
            if not self.config.device_id:
                raise ValueError("device_id is required when using access_token")
            session = sdk.Session(
                access_token=self.config.access_token_str,
                refresh_token=None,
                user_id=self.config.user_id,
                device_id=self.config.device_id,
                homeserver_url=self.config.homeserver,
                oauth_data=None,
                sliding_sync_version=sdk.SlidingSyncVersion.NONE,
            )
            await self._client.restore_session(session)
        elif self.config.password_str:
            await self._client.login(self.config.user_id, self.config.password_str, self.config.device_name, self.config.device_id or None)
        else:
            raise ValueError("access_token or password is required in MatrixConfig")

        session = self._client.session()
        saved = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": session.user_id,
            "device_id": session.device_id,
            "homeserver_url": session.homeserver_url,
            "oauth_data": session.oauth_data,
            "sliding_sync_version": session.sliding_sync_version.name,
        }
        session_file.touch(mode=0o600)
        session_file.write_text(json.dumps(saved))

    async def _verify_device(self) -> None:
        encryption = self._client.encryption()
        await encryption.wait_for_e2ee_initialization_tasks()
        if encryption.verification_state() == self._sdk.VerificationState.VERIFIED:
            return
        if self.config.recovery_key_str:
            await encryption.recover(self.config.recovery_key_str)
        if encryption.verification_state() != self._sdk.VerificationState.VERIFIED:
            _log.warning("Matrix device %s is not cross-signed; encrypted rooms may not share keys with it", self._client.device_id())

    async def disconnect(self) -> None:
        """Stop syncing and drop the room listeners."""
        if self._sync_handle is not None:
            self._sync_handle.cancel()
        for state in self._rooms.values():
            for handle in state.handles:
                handle.cancel()
        self._sync_handle = None
        self._rooms = {}
        self._client = None
        self._bot_user_id = None
        self.connected = False

    async def _attach(self, room: Any) -> _Room:
        room_id = room.id()
        if room_id in self._rooms:
            return self._rooms[room_id]
        state = _Room(room, await room.timeline(), await room.is_encrypted())
        self._rooms[room_id] = state
        # Dropping a TaskHandle cancels its listener, so keep them for the life of the room.
        state.handles.append(await state.timeline.add_listener(_Listener(self._loop, self._on_timeline, room_id)))
        state.handles.append(await room.subscribe_to_send_queue_updates(_Listener(self._loop, self._on_send_queue, room_id)))
        self.channels.add(self._channel(state))
        return state

    def _on_sync(self, response: Any) -> None:
        for room_id in response.rooms.joined:
            if room_id not in self._rooms and room_id not in self._attaching:
                room = self._client.get_room(room_id)
                if room is not None:
                    self._attaching.add(room_id)
                    task = asyncio.ensure_future(self._attach(room))
                    task.add_done_callback(lambda _, room_id=room_id: self._attaching.discard(room_id))

    def _on_timeline(self, room_id: str, diffs: list[Any]) -> None:
        state = self._rooms.get(room_id)
        if state is None:
            return
        for diff in diffs:
            _apply_diff(state.items, diff)
            for item in _diff_items(diff):
                self._publish(room_id, item)

    def _publish(self, room_id: str, item: Any) -> None:
        found = _event_json(item)
        if found is None:
            return
        event, raw = found
        # An event that fails to decrypt arrives as m.room.encrypted and is
        # replaced in the timeline once its key arrives, so only mark it seen
        # after it parses as a message.
        if raw.get("event_id") in self._seen or event.timestamp < self._started_ms:
            return
        message = self._parse_message_event(raw, room_id)
        if message is None:
            return
        self._seen.add(message.id)
        for queue in self._subscribers:
            queue.put_nowait(message)

    def _on_send_queue(self, room_id: str, update: Any) -> None:
        state = self._rooms.get(room_id)
        if state is None:
            return
        if update.is_NEW_LOCAL_EVENT() and state.awaiting_local:
            state.awaiting_sent[update.transaction_id] = state.awaiting_local.pop(0)
        elif update.is_SENT_EVENT():
            future = state.awaiting_sent.pop(update.transaction_id, None)
            if future is not None and not future.done():
                future.set_result(update.event_id)
        elif update.is_SEND_ERROR():
            future = state.awaiting_sent.pop(update.transaction_id, None)
            if future is not None and not future.done():
                future.set_exception(RuntimeError(f"Matrix send failed: {update.error}"))

    def _channel(self, state: _Room) -> MatrixChannel:
        room = state.room
        return MatrixChannel(
            id=room.id(),
            name=room.display_name() or room.id(),
            topic=room.topic() or "",
            canonical_alias=room.canonical_alias() or "",
            encrypted=state.encrypted,
            member_count=room.joined_members_count(),
            channel_type=ChannelType.PRIVATE,
        )

    async def _room_state(self, channel: str | Channel) -> _Room:
        room_id = await self._resolve_channel_id(channel)
        if room_id.startswith("#"):
            resolved = await self._client.resolve_room_alias(room_id)
            room_id = resolved.room_id if resolved else room_id
        state = self._rooms.get(room_id)
        if state is None:
            room = self._client.get_room(room_id)
            if room is None:
                raise ValueError(f"Not joined to Matrix room {room_id}")
            state = await self._attach(room)
        return state

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
        try:
            profile = await self._client.get_profile(id)
        except Exception:  # noqa: BLE001
            return None
        display_name = profile.display_name or id
        user = MatrixUser(id=id, name=display_name, display_name=display_name, handle=id, avatar_mxc=profile.avatar_url or "")
        self.users.add(user)
        return user

    async def fetch_channel(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> MatrixChannel | None:
        """Fetch a joined Matrix room by room ID, alias, or name."""
        self._ensure_connected()
        if isinstance(identifier, MatrixChannel):
            return identifier
        if identifier is not None and hasattr(identifier, "id"):
            id = str(identifier.id)
        elif isinstance(identifier, str) and not id:
            id = identifier
        if id:
            try:
                return self._channel(await self._room_state(id))
            except ValueError:
                return None
        if name:
            cached = self.channels.lookup(name=name)
            return cached if isinstance(cached, MatrixChannel) else None
        return None

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | Message | datetime | None = None,
        after: str | Message | datetime | None = None,
    ) -> list[Message]:
        """Fetch recent room messages, decrypted, newest first."""
        self._ensure_connected()
        state = await self._room_state(channel)
        room_id = state.room.id()
        at_start = False
        while True:
            messages: list[Message] = []
            for item in reversed(state.items):
                found = _event_json(item)
                message = self._parse_message_event(found[1], room_id) if found else None
                if message is not None:
                    messages.append(message)
            filtered = self._filter_message_bounds(messages, before, after)
            if len(filtered) >= limit or at_start:
                return filtered[:limit]
            at_start = await state.timeline.paginate_backwards(max(limit, 1))
            # Let the timeline listener apply the page before reading the items again.
            await asyncio.sleep(0)

    def _content(self, content: str, formatted: bool) -> Any:
        sdk = self._sdk
        if not formatted:
            return sdk.message_event_content_new(sdk.MessageType.TEXT(sdk.TextMessageContent(body=content, formatted=None)))
        html_content = self._translate_mentions(content)
        mentioned = list(dict.fromkeys(_MATRIX_TO_USER.findall(html_content)))
        message = sdk.message_event_content_from_html(self._plain_fallback(html_content), html_content)
        return message.with_mentions(sdk.Mentions(user_ids=mentioned, room=False))

    async def _send(self, state: _Room, send) -> str:
        """Run a send and wait for the server's event ID from the room's send queue."""
        async with state.send_lock:
            future = self._loop.create_future()
            state.awaiting_local.append(future)
            try:
                await send()
                return await asyncio.wait_for(future, timeout=60)
            finally:
                if future in state.awaiting_local:
                    state.awaiting_local.remove(future)

    async def send_message(self, channel: str | Channel, content: str, **kwargs: Any) -> MatrixMessage:
        """Send an HTML-formatted message, encrypted when the room is."""
        self._ensure_connected()
        state = await self._room_state(channel)
        formatted = kwargs.pop("formatted", True)
        message = self._content(content, formatted)
        thread_id = self._extract_thread_id(kwargs.pop("thread", None)) or kwargs.pop("thread_id", None)
        reply_id = self._extract_reply_to_id(kwargs.pop("reply_to", None))
        # A reply to a threaded event stays in its thread.
        target = reply_id or thread_id
        if target:
            event_id = await self._send(state, lambda: state.timeline.send_reply(message, target))
        else:
            event_id = await self._send(state, lambda: state.timeline.send(message))
        room_id = state.room.id()
        body = self._plain_fallback(self._translate_mentions(content)) if formatted else content
        return MatrixMessage(
            id=event_id,
            content=body,
            formatted_content=self._translate_mentions(content) if formatted else "",
            author=MatrixUser(id=self._bot_user_id or self.config.user_id),
            channel=MatrixChannel(id=room_id, name=room_id),
            thread=Thread(id=thread_id) if thread_id else None,
            reference=(MessageReference(message_id=reply_id, channel_id=room_id) if reply_id else None),
            message_type=MessageType.REPLY if reply_id else MessageType.DEFAULT,
            backend="matrix",
        )

    async def edit_message(
        self,
        message: str | Message,
        content: str,
        channel: str | Channel | None = None,
        **kwargs: Any,
    ) -> MatrixMessage:
        """Replace a message's content, encrypted when the room is."""
        self._ensure_connected()
        room_id, event_id = await self._resolve_message_id(message, channel)
        state = await self._room_state(room_id)
        formatted = kwargs.pop("formatted", True)
        replacement_id = await self._send(state, lambda: state.room.edit(event_id, self._content(content, formatted)))
        return MatrixMessage(
            id=event_id,
            replacement_event_id=replacement_id,
            content=self._plain_fallback(self._translate_mentions(content)) if formatted else content,
            formatted_content=self._translate_mentions(content) if formatted else "",
            author=MatrixUser(id=self._bot_user_id or self.config.user_id),
            channel=MatrixChannel(id=room_id, name=room_id),
            is_edited=True,
            relates_to={"rel_type": "m.replace", "event_id": event_id},
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
        state = await self._room_state(room_id)
        await state.room.redact(event_id, None)

    async def get_presence(self, user: str | User) -> MatrixPresence | None:
        """matrix-sdk-python does not expose presence lookups."""
        return None

    async def set_presence(self, status: str, status_text: str | None = None, **kwargs: Any) -> None:
        """matrix-sdk-python does not expose presence updates."""
        raise NotImplementedError("Presence is not available with matrix-sdk-python")

    async def stream_messages(
        self,
        channel: str | Channel | None = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[MatrixMessage]:
        """Yield new room messages, decrypted, as the sync delivers them."""
        self._ensure_connected()
        channel_id = (await self._room_state(channel)).room.id() if channel is not None else None
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                message = await queue.get()
                if channel_id and message.channel_id != channel_id:
                    continue
                if skip_own and message.author_id == self._bot_user_id:
                    continue
                yield message
        except asyncio.CancelledError:
            return
        finally:
            self._subscribers.remove(queue)
