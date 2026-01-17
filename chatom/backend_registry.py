"""Backend registry and base class for chatom.

This module provides the central registry for backend implementations
and the base class that all backends must implement.
"""

import asyncio
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from importlib.metadata import entry_points
from threading import Lock
from typing import (
    Any,
    AsyncIterator,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import Field

from .base import (
    BackendCapabilities,
    BaseModel,
    Channel,
    ChannelRegistry,
    Message,
    Presence,
    User,
    UserRegistry,
)
from .format.variant import Format

__all__ = (
    "BackendBase",
    "BackendRegistry",
    "get_backend",
    "get_backend_format",
    "list_backends",
    "register_backend",
)


# Type variable for backend subclasses
B = TypeVar("B", bound="BackendBase")


class SyncHelper:
    """Helper class to run async methods synchronously.

    This provides a convenient way to call async methods from sync code
    by managing an event loop in a background thread. Uses __getattr__
    to dynamically wrap any async method on the backend.

    Example:
        >>> backend = MyBackend()
        >>> # Call async method synchronously
        >>> user = backend.sync.lookup_user(id="123")
        >>> # Any async method can be called:
        >>> backend.sync.connect()
        >>> backend.sync.send_message(channel_id="C123", content="Hello")
    """

    def __init__(self, backend: "BackendBase") -> None:
        """Initialize the sync helper.

        Args:
            backend: The backend instance to wrap.
        """
        self._backend = backend
        self._executor: Optional[ThreadPoolExecutor] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = Lock()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create the event loop for sync execution."""
        if self._loop is None or self._loop.is_closed():
            with self._lock:
                if self._loop is None or self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
        return self._loop

    def _run_async(self, coro: Any) -> Any:
        """Run a coroutine synchronously.

        Args:
            coro: The coroutine to run.

        Returns:
            The result of the coroutine.
        """
        loop = self._get_loop()
        try:
            return loop.run_until_complete(coro)
        except RuntimeError:
            # If we're already in an async context, use a thread
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=1)

            def run_in_new_loop() -> Any:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            future = self._executor.submit(run_in_new_loop)
            return future.result()

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """Dynamically create sync wrappers for async backend methods.

        This method is called when accessing any attribute not found on SyncHelper.
        It looks for a corresponding method on the backend and, if it's async,
        returns a synchronous wrapper.

        Args:
            name: The method name to look up.

        Returns:
            A callable that wraps the async method synchronously.

        Raises:
            AttributeError: If the method doesn't exist on the backend.
        """
        # Avoid infinite recursion for private attributes
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Get the method from the backend
        method = getattr(self._backend, name, None)
        if method is None:
            raise AttributeError(f"'{type(self._backend).__name__}' has no attribute '{name}'")

        # Check if it's a callable
        if not callable(method):
            raise AttributeError(f"'{name}' is not a method on '{type(self._backend).__name__}'")

        # Return a wrapper that runs the coroutine synchronously
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = method(*args, **kwargs)
            # Check if it's a coroutine (async method)
            if asyncio.iscoroutine(result):
                return self._run_async(result)
            return result

        return sync_wrapper

    def close(self) -> None:
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None


class BackendBase(BaseModel):
    """Base class for all chat backend implementations.

    This provides a unified interface for interacting with chat platforms.
    All backends must implement the abstract methods.

    Backends should be registered with the BackendRegistry via entry points
    or by calling register_backend().

    Attributes:
        name: The backend identifier (e.g., 'slack', 'discord').
        display_name: Human-readable name for the backend.
        format: The preferred output format for this backend.
        capabilities: The capabilities supported by this backend.
        connected: Whether currently connected.
        users: Registry of cached users.
        channels: Registry of cached channels.

    Example:
        >>> class MyBackend(BackendBase):
        ...     name = "my_backend"
        ...     display_name = "My Backend"
        ...     format = Format.MARKDOWN
        ...
        ...     async def connect(self):
        ...         # Implementation
        ...         pass
    """

    # Class-level attributes that define the backend
    name: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    format: ClassVar[Format] = Format.MARKDOWN

    # Instance attributes
    capabilities: Optional[BackendCapabilities] = Field(
        default=None,
        description="The capabilities supported by this backend.",
    )
    connected: bool = Field(
        default=False,
        description="Whether currently connected.",
    )
    users: UserRegistry = Field(
        default_factory=UserRegistry,
        description="Registry of cached users.",
    )
    channels: ChannelRegistry = Field(
        default_factory=ChannelRegistry,
        description="Registry of cached channels.",
    )

    _sync: Optional[SyncHelper] = None
    _presence_heartbeat_running: bool = False
    _presence_heartbeat_task: Optional[asyncio.Task[None]] = None

    @cached_property
    def sync(self) -> SyncHelper:
        """Get the sync helper for calling async methods synchronously.

        Returns:
            SyncHelper instance that wraps async methods.

        Example:
            >>> backend = MyBackend()
            >>> backend.sync.connect()  # Calls connect() synchronously
            >>> user = backend.sync.lookup_user(id="123")
        """
        return SyncHelper(self)

    def get_format(self) -> Format:
        """Get the preferred format for this backend.

        Returns:
            The Format enum value for this backend.
        """
        return self.__class__.format

    # =========================================================================
    # Connection methods
    # =========================================================================

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the backend.

        This should authenticate and establish a connection to the
        chat platform. After successful connection, `connected` should
        be set to True.

        Raises:
            ConnectionError: If connection fails.
        """
        raise NotImplementedError("Subclass must implement connect()")

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the backend.

        This should cleanly close the connection and release resources.
        After disconnection, `connected` should be set to False.
        """
        raise NotImplementedError("Subclass must implement disconnect()")

    # =========================================================================
    # User lookup methods
    # =========================================================================

    async def lookup_user(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Look up a user by any identifier.

        First checks the local cache, then fetches from the backend
        if not found. This method will attempt to use the backend's
        fetch_user with whatever identifiers are provided.

        Args:
            id: User ID.
            name: User name.
            email: User email address.
            handle: User handle/username.

        Returns:
            The user if found, None otherwise.
        """
        # Try local registry first
        user = self.users.lookup(id=id, name=name, email=email, handle=handle)
        if user:
            return user

        # Try fetching from backend with whatever identifiers we have
        if id or name or email or handle:
            user = await self.fetch_user(id=id, name=name, email=email, handle=handle)
            if user:
                self.users.add(user)
                return user

        return None

    @abstractmethod
    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a user from the backend.

        This method accepts flexible input types for convenience:
        - Pass a User object to validate/refresh it
        - Pass an ID string as the first positional argument
        - Use keyword arguments for lookup by name, email, or handle

        The backend will attempt to resolve the user using the most
        efficient method available for the platform.

        Args:
            identifier: A User object or user ID string.
            id: User ID (alternative to positional identifier).
            name: User name or display name to search for.
            email: Email address to search for.
            handle: Username/handle to search for.

        Returns:
            The user if found, None otherwise.

        Example:
            >>> # All of these work:
            >>> user = await backend.fetch_user("U123456")
            >>> user = await backend.fetch_user(id="U123456")
            >>> user = await backend.fetch_user(name="John Doe")
            >>> user = await backend.fetch_user(email="john@example.com")
            >>> user = await backend.fetch_user(existing_user)  # refresh
        """
        raise NotImplementedError("Subclass must implement fetch_user()")

    # =========================================================================
    # Channel lookup methods
    # =========================================================================

    async def lookup_channel(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Look up a channel by any identifier.

        First checks the local cache, then fetches from the backend
        if not found. This method will attempt to use the backend's
        fetch_channel with whatever identifiers are provided.

        Args:
            id: Channel ID.
            name: Channel name.

        Returns:
            The channel if found, None otherwise.
        """
        # Try local registry first
        channel = self.channels.lookup(id=id, name=name)
        if channel:
            return channel

        # Try fetching from backend with whatever identifiers we have
        if id or name:
            channel = await self.fetch_channel(id=id, name=name)
            if channel:
                self.channels.add(channel)
                return channel

        return None

    async def lookup_room(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Look up a room by any identifier.

        This is an alias for lookup_channel. Use whichever terminology
        fits your platform (room for Symphony/Matrix, channel for Slack/Discord).

        Args:
            id: Room ID.
            name: Room name.

        Returns:
            The room/channel if found, None otherwise.
        """
        return await self.lookup_channel(id=id, name=name)

    @abstractmethod
    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel from the backend.

        This method accepts flexible input types for convenience:
        - Pass a Channel object to validate/refresh it
        - Pass an ID string as the first positional argument
        - Use keyword arguments for lookup by name

        The backend will attempt to resolve the channel using the most
        efficient method available for the platform.

        Args:
            identifier: A Channel object or channel ID string.
            id: Channel ID (alternative to positional identifier).
            name: Channel name to search for.

        Returns:
            The channel if found, None otherwise.

        Example:
            >>> # All of these work:
            >>> channel = await backend.fetch_channel("C123456")
            >>> channel = await backend.fetch_channel(id="C123456")
            >>> channel = await backend.fetch_channel(name="general")
            >>> channel = await backend.fetch_channel(existing_channel)  # refresh
        """
        raise NotImplementedError("Subclass must implement fetch_channel()")

    async def fetch_room(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a room from the backend.

        This is an alias for fetch_channel. Use whichever terminology
        fits your platform (room for Symphony/Matrix, channel for Slack/Discord).

        Args:
            identifier: A Channel object or room ID string.
            id: Room ID (alternative to positional identifier).
            name: Room name to search for.

        Returns:
            The room/channel if found, None otherwise.
        """
        return await self.fetch_channel(identifier, id=id, name=name)

    async def fetch_channel_members(
        self,
        channel_id: str,
    ) -> List[User]:
        """Fetch members of a channel.

        Retrieves the list of users who are members of the specified channel.
        This is useful for authorization checks, mention validation, or
        building user interfaces.

        Args:
            channel_id: The channel ID to fetch members for.

        Returns:
            List of users who are members of the channel.

        Raises:
            NotImplementedError: If the backend doesn't support member listing.

        Example:
            >>> members = await backend.fetch_channel_members("C123")
            >>> for user in members:
            ...     print(user.name)
        """
        raise NotImplementedError("This backend does not support fetching channel members")

    async def fetch_room_members(
        self,
        room_id: str,
    ) -> List[User]:
        """Fetch members of a room.

        This is an alias for fetch_channel_members. Use whichever terminology
        fits your platform.

        Args:
            room_id: The room ID to fetch members for.

        Returns:
            List of users who are members of the room.
        """
        return await self.fetch_channel_members(room_id)

    # =========================================================================
    # Message methods
    # =========================================================================

    @abstractmethod
    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages from a channel.

        Retrieves historical messages from the specified channel.

        Args:
            channel_id: The channel to fetch messages from.
            limit: Maximum number of messages to fetch.
            before: Fetch messages before this message ID (for pagination).
            after: Fetch messages after this message ID (for pagination).

        Returns:
            List of messages, ordered from oldest to newest.
        """
        raise NotImplementedError("Subclass must implement fetch_messages()")

    async def fetch_new_messages(
        self,
        channel_id: str,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch new messages from a channel.

        This is a convenience method that fetches messages after a
        specific point, typically used for getting updates.

        Args:
            channel_id: The channel to fetch messages from.
            after: Fetch messages after this message ID.

        Returns:
            List of new messages.
        """
        return await self.fetch_messages(channel_id=channel_id, after=after)

    @abstractmethod
    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to a channel.

        Args:
            channel_id: The channel to send to.
            content: The message content.
            **kwargs: Additional platform-specific options (e.g., embeds,
                      attachments, thread_id).

        Returns:
            The sent message.
        """
        raise NotImplementedError("Subclass must implement send_message()")

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit an existing message.

        Args:
            channel_id: The channel containing the message.
            message_id: The ID of the message to edit.
            content: The new message content.
            **kwargs: Additional platform-specific options.

        Returns:
            The edited message.

        Raises:
            NotImplementedError: If the backend doesn't support editing.
        """
        raise NotImplementedError("This backend does not support message editing")

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a message.

        Args:
            channel_id: The channel containing the message.
            message_id: The ID of the message to delete.

        Raises:
            NotImplementedError: If the backend doesn't support deletion.
        """
        raise NotImplementedError("This backend does not support message deletion")

    async def reply_in_thread(
        self,
        message: Message,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Reply to a message in its thread.

        This is a convenience method that sends a reply in the thread
        of the given message. If the message is not in a thread, it
        creates a new thread from that message.

        This method simplifies thread-based conversations for bot developers
        by abstracting the platform-specific details of thread handling.

        Args:
            message: The message to reply to. Thread context is extracted
                     from message.thread_id or message.id.
            content: The reply content.
            **kwargs: Additional platform-specific options (e.g., embeds,
                      attachments).

        Returns:
            The sent reply message.

        Raises:
            NotImplementedError: If the backend doesn't support threading.

        Example:
            >>> # Reply in a thread
            >>> async def on_message(message: Message):
            ...     reply = await backend.reply_in_thread(
            ...         message,
            ...         "Thanks for your message!"
            ...     )
        """
        # Default implementation uses send_message with thread_id
        # Get the thread ID: either the message's thread or start a new thread
        thread_id = message.thread_id or message.id
        channel_id = message.channel_id or (message.channel.id if message.channel else "")

        if not channel_id:
            raise ValueError("Cannot reply: message has no channel information")

        return await self.send_message(
            channel_id=channel_id,
            content=content,
            thread_id=thread_id,
            **kwargs,
        )

    # =========================================================================
    # Real-time message streaming
    # =========================================================================

    async def stream_messages(
        self,
        channel_id: Optional[str] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[Message]:
        """Stream incoming messages in real-time.

        This async generator yields Message objects as they arrive from
        the chat platform. It abstracts away the platform-specific
        details of real-time messaging (WebSockets, Socket Mode, datafeed, etc.).

        The stream continues until the generator is closed or an error occurs.

        Args:
            channel_id: Optional channel ID to filter messages to a specific
                        channel. If None, yields messages from all channels
                        the bot has access to.
            skip_own: If True (default), skip messages sent by the bot itself.
            skip_history: If True (default), skip messages that existed before
                         the stream started. Only yields new messages.

        Yields:
            Message: Each message as it arrives.

        Raises:
            NotImplementedError: If the backend doesn't support streaming.
            ConnectionError: If the real-time connection fails.

        Example:
            >>> async for message in backend.stream_messages():
            ...     print(f"Received: {message.content}")
            ...     if message.mentions_bot:
            ...         await backend.reply_in_thread(message, "Hello!")
            >>>
            >>> # Filter to a specific channel
            >>> async for message in backend.stream_messages(channel_id="C123"):
            ...     await process_message(message)
        """
        raise NotImplementedError("This backend does not support message streaming")
        # This is needed for type checking, but won't be reached
        yield  # type: ignore

    async def get_bot_info(self) -> Optional[User]:
        """Get information about the connected bot user.

        Returns the User object representing the bot/service account
        that is currently connected. This is useful for checking if
        messages mention the bot.

        Returns:
            The bot's User object, or None if not available.

        Raises:
            NotImplementedError: If the backend doesn't support this.

        Example:
            >>> bot = await backend.get_bot_info()
            >>> print(f"Connected as: {bot.name} ({bot.id})")
        """
        raise NotImplementedError("This backend does not support get_bot_info")

    # =========================================================================
    # Presence methods
    # =========================================================================

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set the current user's presence status.

        Args:
            status: The presence status (e.g., 'online', 'away', 'dnd').
            status_text: Optional status message/text.
            **kwargs: Additional platform-specific options.

        Raises:
            NotImplementedError: If the backend doesn't support presence.
        """
        raise NotImplementedError("This backend does not support presence")

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get a user's presence status.

        Args:
            user_id: The user ID to get presence for.

        Returns:
            The user's presence, or None if not available.

        Raises:
            NotImplementedError: If the backend doesn't support presence.
        """
        raise NotImplementedError("This backend does not support presence")

    def start_presence_heartbeat(
        self,
        interval_seconds: int = 60,
        status: str = "online",
        status_text: Optional[str] = None,
    ) -> None:
        """Start an automatic presence heartbeat.

        This method periodically sets the user's presence to keep
        the bot appearing online. This is useful for platforms that
        require regular presence updates or for bots that need to
        maintain an active status.

        The heartbeat runs in the background and can be stopped with
        stop_presence_heartbeat().

        Args:
            interval_seconds: How often to send presence updates (default 60).
            status: The presence status to set (default 'online').
            status_text: Optional status message/text to display.

        Example:
            >>> # Start keeping the bot online
            >>> backend.start_presence_heartbeat(60, "online", "Ready to help!")
            >>>
            >>> # Later, stop the heartbeat
            >>> backend.stop_presence_heartbeat()
        """
        # Stop any existing heartbeat
        self.stop_presence_heartbeat()

        async def _heartbeat_loop() -> None:
            while self._presence_heartbeat_running:
                try:
                    await self.set_presence(status, status_text)
                except Exception:
                    # Ignore errors, just keep trying
                    pass
                await asyncio.sleep(interval_seconds)

        self._presence_heartbeat_running = True
        self._presence_heartbeat_task = asyncio.create_task(_heartbeat_loop())

    def stop_presence_heartbeat(self) -> None:
        """Stop the automatic presence heartbeat.

        Cancels any running presence heartbeat task started by
        start_presence_heartbeat().

        Example:
            >>> backend.stop_presence_heartbeat()
        """
        self._presence_heartbeat_running = False
        if self._presence_heartbeat_task is not None:
            self._presence_heartbeat_task.cancel()
            self._presence_heartbeat_task = None

    @property
    def is_presence_heartbeat_active(self) -> bool:
        """Check if the presence heartbeat is currently running.

        Returns:
            bool: True if the heartbeat is active.
        """
        return self._presence_heartbeat_running

    # =========================================================================
    # Reaction methods
    # =========================================================================

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message to react to.
            emoji: The emoji to add (name or unicode).

        Raises:
            NotImplementedError: If the backend doesn't support reactions.
        """
        raise NotImplementedError("This backend does not support reactions")

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction from a message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message to remove reaction from.
            emoji: The emoji to remove (name or unicode).

        Raises:
            NotImplementedError: If the backend doesn't support reactions.
        """
        raise NotImplementedError("This backend does not support reactions")

    # =========================================================================
    # Channel/Room management methods
    # =========================================================================

    async def create_dm(
        self,
        user_ids: List[str],
    ) -> Optional[str]:
        """Create a direct message (DM) or instant message (IM) channel.

        Creates a private conversation with one or more users.
        For single users, this creates a 1:1 DM. For multiple users,
        this may create a group DM/MIM depending on the platform.

        Args:
            user_ids: List of user IDs to include in the DM.

        Returns:
            The channel/stream ID of the created DM, or None if failed.

        Raises:
            NotImplementedError: If the backend doesn't support DM creation.
        """
        raise NotImplementedError("This backend does not support DM creation")

    async def create_im(
        self,
        user_ids: List[str],
    ) -> Optional[str]:
        """Create an instant message (IM) channel.

        This is an alias for create_dm. Use whichever terminology
        fits your platform (IM for Symphony, DM for Discord/Slack).

        Args:
            user_ids: List of user IDs to include in the IM.

        Returns:
            The channel/stream ID of the created IM, or None if failed.
        """
        return await self.create_dm(user_ids)

    async def create_channel(
        self,
        name: str,
        description: str = "",
        public: bool = True,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a new channel.

        Creates a channel/room for group communication.

        Args:
            name: The channel name.
            description: Optional channel description/purpose.
            public: Whether the channel is public (default True).
            **kwargs: Additional platform-specific options:
                - read_only: Whether the channel is read-only (Symphony).
                - topic: Channel topic (Slack).
                - category_id: Category to create under (Discord).

        Returns:
            The channel ID of the created channel, or None if failed.

        Raises:
            NotImplementedError: If the backend doesn't support channel creation.
        """
        raise NotImplementedError("This backend does not support channel creation")

    async def create_room(
        self,
        name: str,
        description: str = "",
        public: bool = True,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a new room.

        This is an alias for create_channel. Use whichever terminology
        fits your platform (room for Symphony/Matrix, channel for Slack/Discord).

        Args:
            name: The room name.
            description: Optional room description.
            public: Whether the room is public (default True).
            **kwargs: Additional platform-specific options.

        Returns:
            The room/stream ID of the created room, or None if failed.
        """
        return await self.create_channel(name, description, public, **kwargs)

    async def join_channel(
        self,
        channel_id: str,
        **kwargs: Any,
    ) -> None:
        """Join a channel.

        Makes the bot/user a member of the specified channel.

        Args:
            channel_id: The channel ID or name to join.
            **kwargs: Additional platform-specific options:
                - key: Channel password/key (IRC).
                - invite_code: Invite code (Discord).

        Raises:
            NotImplementedError: If the backend doesn't support joining channels.
        """
        raise NotImplementedError("This backend does not support joining channels")

    async def join_room(
        self,
        room_id: str,
        **kwargs: Any,
    ) -> None:
        """Join a room.

        This is an alias for join_channel. Use whichever terminology
        fits your platform.

        Args:
            room_id: The room ID or name to join.
            **kwargs: Additional platform-specific options.
        """
        return await self.join_channel(room_id, **kwargs)

    async def leave_channel(
        self,
        channel_id: str,
        **kwargs: Any,
    ) -> None:
        """Leave a channel.

        Removes the bot/user from the specified channel.

        Args:
            channel_id: The channel ID or name to leave.
            **kwargs: Additional platform-specific options:
                - message: Part message (IRC).

        Raises:
            NotImplementedError: If the backend doesn't support leaving channels.
        """
        raise NotImplementedError("This backend does not support leaving channels")

    async def leave_room(
        self,
        room_id: str,
        **kwargs: Any,
    ) -> None:
        """Leave a room.

        This is an alias for leave_channel. Use whichever terminology
        fits your platform.

        Args:
            room_id: The room ID or name to leave.
            **kwargs: Additional platform-specific options.
        """
        return await self.leave_channel(room_id, **kwargs)

    # =========================================================================
    # Extended messaging methods
    # =========================================================================

    async def send_action(
        self,
        target: str,
        action: str,
    ) -> None:
        """Send an action/emote message.

        Sends an action message (like IRC's /me command).
        On IRC this is a CTCP ACTION. On other platforms,
        this may be formatted as italicized text or similar.

        Args:
            target: The channel or user to send to.
            action: The action text (e.g., "waves hello").

        Raises:
            NotImplementedError: If the backend doesn't support actions.
        """
        raise NotImplementedError("This backend does not support action messages")

    async def send_notice(
        self,
        target: str,
        text: str,
    ) -> None:
        """Send a notice message.

        Sends a notice (typically displayed differently from regular messages).
        On IRC this is a NOTICE. Other platforms may not distinguish notices.

        Args:
            target: The channel or user to send to.
            text: The notice text.

        Raises:
            NotImplementedError: If the backend doesn't support notices.
        """
        raise NotImplementedError("This backend does not support notice messages")

    # =========================================================================
    # Mention methods
    # =========================================================================

    def mention_user(self, user: User) -> str:
        """Format a user mention for this backend.

        Args:
            user: The user to mention.

        Returns:
            The formatted mention string.
        """
        from .base.mention import mention_user_for_backend

        return mention_user_for_backend(user, self.__class__.name)

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for this backend.

        Args:
            channel: The channel to mention.

        Returns:
            The formatted mention string.
        """
        from .base.mention import mention_channel_for_backend

        return mention_channel_for_backend(channel, self.__class__.name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(connected={self.connected})"


class BackendRegistry:
    """Central registry for all backend implementations.

    This registry allows discovering and instantiating backends by name.
    Backends can be registered via entry points or programmatically.

    Example:
        >>> # Get a registered backend class
        >>> SlackBackend = BackendRegistry.get("slack")
        >>> backend = SlackBackend()
        >>>
        >>> # List all available backends
        >>> for name in BackendRegistry.list():
        ...     print(name)
    """

    _backends: ClassVar[Dict[str, Type[BackendBase]]] = {}
    _format_map: ClassVar[Dict[str, Format]] = {}
    _instances: ClassVar[Dict[str, BackendBase]] = {}
    _loaded: ClassVar[bool] = False
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def register(
        cls,
        backend_class: Type[BackendBase],
        name: Optional[str] = None,
    ) -> Type[BackendBase]:
        """Register a backend class.

        Args:
            backend_class: The backend class to register.
            name: Optional name override. If not provided, uses
                  backend_class.name.

        Returns:
            The registered backend class (for use as decorator).

        Example:
            >>> @BackendRegistry.register
            ... class MyBackend(BackendBase):
            ...     name = "my_backend"
            ...     ...
        """
        backend_name = name or backend_class.name
        if not backend_name:
            raise ValueError(f"Backend class {backend_class.__name__} must have a name")
        cls._backends[backend_name.lower()] = backend_class
        cls._format_map[backend_name.lower()] = backend_class.format
        return backend_class

    @classmethod
    def get(cls, name: str) -> Type[BackendBase]:
        """Get a backend class by name.

        Args:
            name: The backend name.

        Returns:
            The backend class.

        Raises:
            KeyError: If the backend is not registered.
        """
        cls._ensure_loaded()
        name_lower = name.lower()
        if name_lower not in cls._backends:
            raise KeyError(f"Backend '{name}' not found. Available: {list(cls._backends.keys())}")
        return cls._backends[name_lower]

    @classmethod
    def get_instance(cls, name: str, **kwargs: Any) -> BackendBase:
        """Get or create a backend instance.

        If an instance already exists for this name, returns it.
        Otherwise creates a new instance.

        Args:
            name: The backend name.
            **kwargs: Arguments passed to the backend constructor.

        Returns:
            The backend instance.
        """
        cls._ensure_loaded()
        name_lower = name.lower()
        if name_lower not in cls._instances:
            backend_class = cls.get(name)
            cls._instances[name_lower] = backend_class(**kwargs)
        return cls._instances[name_lower]

    @classmethod
    def get_format(cls, name: str) -> Format:
        """Get the preferred format for a backend.

        Args:
            name: The backend name.

        Returns:
            The Format enum value.
        """
        cls._ensure_loaded()
        return cls._format_map.get(name.lower(), Format.MARKDOWN)

    @classmethod
    def list(cls) -> List[str]:
        """List all registered backend names.

        Returns:
            List of backend names.
        """
        cls._ensure_loaded()
        return list(cls._backends.keys())

    @classmethod
    def items(cls) -> Iterator[tuple[str, Type[BackendBase]]]:
        """Iterate over all registered backends.

        Yields:
            Tuples of (name, backend_class).
        """
        cls._ensure_loaded()
        yield from cls._backends.items()

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached backend instances."""
        cls._instances.clear()

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Ensure entry points have been loaded."""
        if not cls._loaded:
            with cls._lock:
                if not cls._loaded:
                    cls._load_entry_points()
                    cls._loaded = True

    @classmethod
    def _load_entry_points(cls) -> None:
        """Load backends from entry points."""
        try:
            eps = entry_points(group="chatom.backends")
            for ep in eps:
                try:
                    backend_class = ep.load()
                    if isinstance(backend_class, type) and issubclass(backend_class, BackendBase):
                        cls.register(backend_class, name=ep.name)
                except Exception:
                    # Log but don't fail on individual entry point errors
                    pass
        except Exception:
            # Entry points may not be available in all environments
            pass

    @classmethod
    def register_all_types(cls) -> None:
        """Register all backend types for type conversion.

        This iterates over all registered backends and registers their
        user_class, channel_class, and presence_class with the conversion
        module. Each backend class should define these ClassVar attributes.

        This is called lazily when conversion functions are first used.
        """
        # Import here to avoid circular imports
        from .base.conversion import register_backend_type

        cls._ensure_loaded()

        for backend_name, backend_class in cls._backends.items():
            try:
                # Check if the backend class has the type class attributes
                user_class = getattr(backend_class, "user_class", None)
                channel_class = getattr(backend_class, "channel_class", None)
                presence_class = getattr(backend_class, "presence_class", None)

                # Register types if they exist
                if user_class is not None:
                    register_backend_type(backend_name, User, user_class)
                if channel_class is not None:
                    register_backend_type(backend_name, Channel, channel_class)
                if presence_class is not None:
                    register_backend_type(backend_name, Presence, presence_class)
            except Exception:
                # Skip backends that fail to register
                pass


# Convenience functions
def register_backend(
    backend_class: Optional[Type[BackendBase]] = None,
    *,
    name: Optional[str] = None,
) -> Union[Type[BackendBase], Callable[[Type[BackendBase]], Type[BackendBase]]]:
    """Register a backend class with the registry.

    Can be used as a decorator with or without arguments.

    Args:
        backend_class: The backend class to register.
        name: Optional name override.

    Returns:
        The registered class or a decorator.

    Example:
        >>> @register_backend
        ... class MyBackend(BackendBase):
        ...     name = "my_backend"
        ...
        >>> @register_backend(name="custom_name")
        ... class AnotherBackend(BackendBase):
        ...     ...
    """
    if backend_class is None:
        # Called with arguments: @register_backend(name="...")
        def decorator(cls: Type[BackendBase]) -> Type[BackendBase]:
            return BackendRegistry.register(cls, name=name)

        return decorator
    else:
        # Called without arguments: @register_backend
        return BackendRegistry.register(backend_class, name=name)


def get_backend(name: str) -> Type[BackendBase]:
    """Get a backend class by name.

    Args:
        name: The backend name.

    Returns:
        The backend class.
    """
    return BackendRegistry.get(name)


def get_backend_format(name: str) -> Format:
    """Get the preferred format for a backend.

    This function replaces get_format_for_backend and uses the
    backend registry.

    Args:
        name: The backend name.

    Returns:
        The Format enum value.
    """
    return BackendRegistry.get_format(name)


def list_backends() -> List[str]:
    """List all available backend names.

    Returns:
        List of registered backend names.
    """
    return BackendRegistry.list()
