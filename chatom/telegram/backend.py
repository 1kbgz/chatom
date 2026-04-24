"""Telegram backend implementation for chatom."""

import asyncio
from logging import getLogger
from typing import Any, AsyncIterator, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend import BackendBase
from ..base import (
    BackendCapabilities,
    Capability,
    Channel,
    Message,
    MessageType,
    Presence,
    User,
)
from ..format.variant import Format
from .channel import TelegramChannel
from .config import TelegramConfig
from .mention import mention_channel as _mention_channel, mention_user as _mention_user
from .message import TelegramMessage
from .presence import TelegramPresence
from .user import TelegramUser

__all__ = ("TelegramBackend",)

_log = getLogger(__name__)

# Telegram capabilities
TELEGRAM_CAPABILITIES = BackendCapabilities(
    capabilities=frozenset(
        {
            Capability.PLAINTEXT,
            Capability.MARKDOWN,
            Capability.HTML,
            Capability.CODE_BLOCKS,
            Capability.IMAGES,
            Capability.FILES,
            Capability.VIDEOS,
            Capability.AUDIO,
            Capability.REPLIES,
            Capability.USER_MENTIONS,
            Capability.EMOJI_REACTIONS,
        }
    )
)


class TelegramBackend(BackendBase):
    """Telegram backend implementation using python-telegram-bot.

    Uses the Telegram Bot API via python-telegram-bot library for
    all API interactions. Supports sending/receiving messages,
    reactions, file uploads, and real-time message streaming via polling.

    Attributes:
        name: The backend identifier ('telegram').
        display_name: Human-readable name.
        format: Telegram uses HTML format for rich text.
        capabilities: Telegram-specific capabilities.
        config: Telegram-specific configuration.

    Example:
        >>> config = TelegramConfig(bot_token="123456:ABC-DEF...")
        >>> backend = TelegramBackend(config=config)
        >>> await backend.connect()
        >>> msg = await backend.send_message("-100123456789", "Hello!")
    """

    name: ClassVar[str] = "telegram"
    display_name: ClassVar[str] = "Telegram"
    format: ClassVar[Format] = Format.HTML

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = TelegramUser
    channel_class: ClassVar[type] = TelegramChannel
    presence_class: ClassVar[type] = TelegramPresence

    capabilities: Optional[BackendCapabilities] = TELEGRAM_CAPABILITIES
    config: TelegramConfig = Field(default_factory=TelegramConfig)

    # Internal bot instance (set during connect)
    _bot: Any = None

    # Cached bot info
    _bot_user_id: Optional[str] = None
    _bot_user_name: Optional[str] = None

    @property
    def bot_user_id(self) -> Optional[str]:
        """Get the bot's user ID."""
        return self._bot_user_id

    @property
    def bot_user_name(self) -> Optional[str]:
        """Get the bot's username."""
        return self._bot_user_name

    model_config = {"arbitrary_types_allowed": True}

    async def connect(self) -> None:
        """Connect to Telegram by initializing the Bot and verifying credentials.

        Raises:
            ImportError: If python-telegram-bot is not installed.
            RuntimeError: If the token is missing or invalid.
        """
        try:
            from telegram import Bot
        except ImportError:
            raise ImportError("python-telegram-bot is required for Telegram backend. Install with: pip install python-telegram-bot")

        token = self.config.bot_token_str
        if not token:
            raise ValueError("bot_token is required in TelegramConfig")

        self._bot = Bot(token=token)
        await self._bot.initialize()

        # Verify credentials with getMe
        me = await self._bot.get_me()
        self._bot_user_id = str(me.id)
        self._bot_user_name = me.username
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._bot is not None:
            await self._bot.shutdown()
            self._bot = None
        self._bot_user_id = None
        self._bot_user_name = None
        self.connected = False

    def _ensure_connected(self) -> None:
        """Ensure the bot is connected."""
        if not self.connected or self._bot is None:
            raise ConnectionError("Not connected to Telegram. Call connect() first.")

    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a user from Telegram.

        Note: Telegram Bot API does not support arbitrary user lookup.
        Users can only be fetched if the bot has interacted with them
        via getChatMember in a known chat. ID-based lookup checks the
        cache first. name/handle lookup is cache-only.

        Args:
            identifier: A TelegramUser object or user ID string.
            id: User ID.
            name: Display name to search for (cache only).
            email: Email (not supported by Telegram).
            handle: Username to search for (cache only).

        Returns:
            The user if found, None otherwise.
        """
        self._ensure_connected()

        # Handle User object input
        if isinstance(identifier, TelegramUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = str(identifier.id)

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier) if isinstance(identifier, str) else str(identifier.id)

        # Check cache first
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

        # Search by name or handle in cache
        if name or handle:
            for cached_user in self.users.all():
                if isinstance(cached_user, TelegramUser):
                    if name and cached_user.name.lower() == name.lower():
                        return cached_user
                    if handle and (cached_user.handle.lower() == handle.lower() or cached_user.username.lower() == handle.lower()):
                        return cached_user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel (chat) from Telegram.

        Uses the getChat API to fetch chat information by ID.
        Name-based lookup checks cache only.

        Args:
            identifier: A TelegramChannel object or chat ID string.
            id: Chat ID.
            name: Chat name to search for (cache only).

        Returns:
            The channel if found, None otherwise.
        """
        self._ensure_connected()

        # Handle Channel object input
        if isinstance(identifier, TelegramChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = str(identifier.id)

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier) if isinstance(identifier, str) else str(identifier.id)

        # Check cache first
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached

        # Fetch by ID from API
        if id:
            return await self._fetch_channel_by_id(id)

        # Search by name in cache (match on title or username)
        if name:
            name_lower = name.lower()
            name_stripped = name.lstrip("@").lower()
            for cached_channel in self.channels.all():
                if isinstance(cached_channel, TelegramChannel):
                    if cached_channel.name.lower() == name_lower:
                        return cached_channel
                    if cached_channel.username and cached_channel.username.lower() == name_stripped:
                        return cached_channel

            # Try @username lookup via getChat (works for public groups/channels)
            try:
                chat = await self._bot.get_chat(chat_id=f"@{name_stripped}")
                if chat:
                    channel = TelegramChannel.from_telegram_chat(chat)
                    self.channels.add(channel)
                    return channel
            except Exception as e:
                _log.debug("getChat(@%s) failed: %s", name_stripped, e)

        return None

    async def _fetch_channel_by_id(self, chat_id: str) -> Optional[TelegramChannel]:
        """Fetch a chat by ID from the Telegram API."""
        try:
            chat = await self._bot.get_chat(chat_id=int(chat_id))
            if chat:
                channel = TelegramChannel.from_telegram_chat(chat)
                self.channels.add(channel)
                return channel
        except Exception as e:
            _log.warning("Error fetching chat %s: %s", chat_id, e)
        return None

    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[Union[str, Message]] = None,
        after: Optional[Union[str, Message]] = None,
    ) -> List[Message]:
        """Fetch messages from a Telegram chat.

        Note: The Telegram Bot API does not support fetching message history.
        Bots can only receive messages in real-time via updates/webhooks.
        This method returns an empty list as message history is not available.

        Args:
            channel: The channel to fetch messages from.
            limit: Maximum number of messages.
            before: Fetch messages before this message.
            after: Fetch messages after this message.

        Returns:
            Empty list (Telegram Bot API limitation).
        """
        self._ensure_connected()
        # Telegram Bot API does not provide a message history endpoint
        return []

    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> TelegramMessage:
        """Send a message to a Telegram chat.

        Uses the sendMessage API. Supports HTML parse mode by default.

        Args:
            channel: The chat to send to (ID string or Channel object).
            content: The message content (HTML formatted).
            **kwargs: Additional options:
                - thread: ``str | Thread | Message`` — forum topic thread.
                  Translated to ``message_thread_id``. ``thread_id`` is
                  still accepted as a legacy alias.
                - reply_to: ``str | Message`` — message to reply to.
                  Translated to ``reply_to_message_id``.
                - parse_mode: Parse mode ('HTML', 'MarkdownV2', or None).
                - disable_notification: Send silently.
                - protect_content: Protect message from forwarding.

        Returns:
            The sent message.
        """
        self._ensure_connected()

        chat_id = await self._resolve_channel_id(channel)

        # Build send kwargs
        send_kwargs: dict[str, Any] = {"chat_id": int(chat_id), "text": content}

        # Default to HTML parse mode
        send_kwargs["parse_mode"] = kwargs.pop("parse_mode", "HTML")

        # Handle thread (standardized) / thread_id (legacy) for forum topics
        thread_val = self._extract_thread_id(kwargs.pop("thread", None))
        if thread_val is None and "thread_id" in kwargs:
            thread_val = kwargs.pop("thread_id")
        if thread_val is not None:
            send_kwargs["message_thread_id"] = int(thread_val)

        # Handle reply_to
        reply_to_id = self._extract_reply_to_id(kwargs.pop("reply_to", None))
        if reply_to_id is not None:
            send_kwargs["reply_to_message_id"] = int(reply_to_id)

        # Pass through supported kwargs
        for key in ("disable_notification", "protect_content"):
            if key in kwargs:
                send_kwargs[key] = kwargs.pop(key)

        msg = await self._bot.send_message(**send_kwargs)
        result = TelegramMessage.from_telegram_message(msg)

        return result

    async def upload_file(
        self,
        channel: Union[str, Channel],
        data: bytes,
        filename: str = "file",
        content_type: str = "",
        title: str = "",
        content: str = "",
        **kwargs: Any,
    ) -> Message:
        """Upload a file to a Telegram chat.

        Uses ``send_photo`` for image MIME types and ``send_document``
        for everything else.
        """
        import io

        self._ensure_connected()

        chat_id = await self._resolve_channel_id(channel)
        buf = io.BytesIO(data)
        buf.name = filename  # python-telegram-bot reads .name for the filename

        send_kwargs: dict[str, Any] = {"chat_id": int(chat_id)}
        if content:
            send_kwargs["caption"] = content
            send_kwargs["parse_mode"] = "HTML"

        if content_type.startswith("image/"):
            msg = await self._bot.send_photo(photo=buf, **send_kwargs)
        else:
            msg = await self._bot.send_document(document=buf, **send_kwargs)

        return TelegramMessage.from_telegram_message(msg)

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> TelegramMessage:
        """Edit a Telegram message.

        Uses the editMessageText API.

        Args:
            message: The message to edit (ID string or TelegramMessage).
            content: The new content.
            channel: The chat containing the message (required if message is str).
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        self._ensure_connected()

        chat_id, message_id = await self._resolve_message_id(message, channel)

        edit_kwargs: dict[str, Any] = {
            "chat_id": int(chat_id),
            "message_id": int(message_id),
            "text": content,
            "parse_mode": kwargs.pop("parse_mode", "HTML"),
        }

        result = await self._bot.edit_message_text(**edit_kwargs)
        return TelegramMessage.from_telegram_message(result)

    async def delete_message(
        self,
        message: Union[str, Message],
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Delete a Telegram message.

        Uses the deleteMessage API.

        Args:
            message: The message to delete (ID string or TelegramMessage).
            channel: The chat containing the message (required if message is str).
        """
        self._ensure_connected()

        chat_id, message_id = await self._resolve_message_id(message, channel)
        await self._bot.delete_message(chat_id=int(chat_id), message_id=int(message_id))

    async def forward_message(
        self,
        message: Union[str, Message],
        to_channel: Union[str, Channel],
        *,
        include_attribution: bool = True,
        prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> TelegramMessage:
        """Forward a message to another Telegram chat.

        Telegram has native forward support via the forwardMessage API.
        If include_attribution is False and source info is available,
        uses native forwarding. Otherwise sends a new message with attribution.

        Args:
            message: The message to forward (TelegramMessage object).
            to_channel: The destination chat.
            include_attribution: If True, include info about original source.
            prefix: Optional text to prepend.
            **kwargs: Additional options.

        Returns:
            The forwarded message.
        """
        self._ensure_connected()

        if isinstance(message, str):
            raise ValueError("forward_message requires a Message object, not just a message ID. Use fetch_messages() to get the full message first.")

        dest_chat_id = await self._resolve_channel_id(to_channel)

        # Try native Telegram forwarding if we have the source chat info
        if not prefix and isinstance(message, TelegramMessage) and message.chat_id:
            try:
                msg = await self._bot.forward_message(
                    chat_id=int(dest_chat_id),
                    from_chat_id=int(message.chat_id),
                    message_id=int(message.id),
                )
                result = TelegramMessage.from_telegram_message(msg)
                result.message_type = MessageType.FORWARD
                result.forwarded_from = message
                return result
            except Exception:
                pass  # Fall back to manual forwarding

        # Manual forwarding with attribution
        content_parts = []
        if prefix:
            content_parts.append(prefix)
        if include_attribution:
            author_name = message.author.name if message.author else "Unknown"
            channel_name = message.channel.name if message.channel else "unknown chat"
            content_parts.append(f"<i>Forwarded from {channel_name} by {author_name}</i>\n")
        content_parts.append(message.content)

        forwarded_content = "".join(content_parts)
        result = await self.send_message(dest_chat_id, forwarded_content)
        result.message_type = MessageType.FORWARD
        result.forwarded_from = message
        return result

    async def add_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Add a reaction to a message.

        Uses the setMessageReaction API (Telegram Bot API 7.0+).

        Args:
            message: The message to react to.
            emoji: The emoji to react with (Unicode emoji).
            channel: The chat containing the message.
        """
        self._ensure_connected()

        chat_id, message_id = await self._resolve_message_id(message, channel)

        from telegram import ReactionTypeEmoji

        await self._bot.set_message_reaction(
            chat_id=int(chat_id),
            message_id=int(message_id),
            reaction=[ReactionTypeEmoji(emoji=emoji)],
        )

    async def remove_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Remove a reaction from a message.

        Telegram's API sets the full reaction list, so removing means
        setting an empty list.

        Args:
            message: The message to remove reaction from.
            emoji: The emoji to remove (unused - clears all bot reactions).
            channel: The chat containing the message.
        """
        self._ensure_connected()

        chat_id, message_id = await self._resolve_message_id(message, channel)

        await self._bot.set_message_reaction(
            chat_id=int(chat_id),
            message_id=int(message_id),
            reaction=[],
        )

    def mention_user(self, user: User) -> str:
        """Format a user mention for Telegram.

        Args:
            user: The user to mention.

        Returns:
            Telegram user mention string.
        """
        if isinstance(user, TelegramUser):
            return _mention_user(user)
        if hasattr(user, "handle") and user.handle:
            return f"@{user.handle}"
        return f'<a href="tg://user?id={user.id}">{user.display_name}</a>'

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for Telegram.

        Args:
            channel: The channel to mention.

        Returns:
            Telegram channel mention string.
        """
        if isinstance(channel, TelegramChannel):
            return _mention_channel(channel)
        return f"#{channel.name}" if channel.name else f"#{channel.id}"

    async def get_bot_info(self) -> Optional[User]:
        """Get information about the connected bot.

        Returns:
            The bot's User object.
        """
        self._ensure_connected()

        try:
            me = await self._bot.get_me()
            user = TelegramUser.from_telegram_user(me)
            self._bot_user_id = user.id
            self._bot_user_name = user.username or user.handle
            return user
        except Exception:
            pass
        return None

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set bot presence.

        Note: Telegram bots don't have traditional presence/status.
        This is a no-op for API compatibility.

        Args:
            status: Status string (ignored).
            status_text: Status text (ignored).
        """
        # Telegram bots don't support presence changes

    async def get_presence(self, user: Union[str, User]) -> Optional[Presence]:
        """Get a user's presence.

        Note: Telegram bots have very limited access to user presence.
        Returns None as presence is not reliably available.

        Args:
            user: The user to check.

        Returns:
            None (Telegram limitation).
        """
        return None

    async def create_dm(self, users: List[Union[str, User]]) -> Optional[str]:
        """Create a DM with a user.

        In Telegram, DMs are just private chats identified by the user's ID.
        The bot must have been contacted by the user first.

        Args:
            users: List of users (only first is used for 1:1 DM).

        Returns:
            The chat ID (same as user ID for private chats).
        """
        if not users:
            return None

        user = users[0]
        user_id = str(user.id) if isinstance(user, User) else str(user)
        return user_id

    async def discover_chats(
        self,
        timeout: float = 5.0,
    ) -> list[TelegramChannel]:
        """Discover chats by consuming recent getUpdates.

        Useful for finding chat IDs / usernames when you know the bot
        has received messages in specific groups or channels.

        Args:
            timeout: Seconds to wait for updates (default 5).

        Returns:
            List of unique TelegramChannel objects found.
        """
        self._ensure_connected()

        seen: dict[str, TelegramChannel] = {}
        try:
            updates = await self._bot.get_updates(offset=0, timeout=int(timeout))
            for update in updates:
                chat = None
                if update.message:
                    chat = update.message.chat
                elif update.channel_post:
                    chat = update.channel_post.chat
                elif getattr(update, "my_chat_member", None):
                    chat = update.my_chat_member.chat
                if chat and str(chat.id) not in seen:
                    channel = TelegramChannel.from_telegram_chat(chat)
                    self.channels.add(channel)
                    seen[str(chat.id)] = channel
        except Exception as e:
            _log.warning("Error discovering chats: %s", e)

        return list(seen.values())

    async def stream_messages(
        self,
        channel: Optional[Union[str, Channel]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[TelegramMessage]:
        """Stream incoming messages in real-time using polling.

        Uses Telegram's getUpdates long-polling to receive messages.

        Args:
            channel: Optional chat to filter messages by.
            skip_own: If True, skip messages sent by the bot itself.
            skip_history: If True, skip old messages.

        Yields:
            TelegramMessage: Each message as it arrives.
        """
        self._ensure_connected()

        channel_id: Optional[str] = None
        if channel is not None:
            channel_id = await self._resolve_channel_id(channel)

        bot_user_id = self._bot_user_id
        offset = 0

        # First call with offset=-1 to skip old updates if skip_history
        if skip_history:
            try:
                updates = await self._bot.get_updates(offset=-1, timeout=0)
                if updates:
                    offset = updates[-1].update_id + 1
            except Exception:
                pass

        while True:
            try:
                updates = await self._bot.get_updates(
                    offset=offset,
                    timeout=30,
                    allowed_updates=["message"],
                )

                for update in updates:
                    offset = update.update_id + 1

                    if update.message is None:
                        continue

                    msg = update.message

                    # Skip bot's own messages
                    if skip_own and msg.from_user and str(msg.from_user.id) == bot_user_id:
                        continue

                    # Filter by channel if specified
                    if channel_id and str(msg.chat.id) != channel_id:
                        continue

                    yield TelegramMessage.from_telegram_message(msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                _log.warning("Error polling Telegram updates: %s", e)
                await asyncio.sleep(1)
