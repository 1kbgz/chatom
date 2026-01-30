"""Backend base class for chatom.

This module provides the base class that all backends must implement.
"""

import asyncio
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from threading import Lock
from typing import (
    Any,
    AsyncIterator,
    Callable,
    ClassVar,
    List,
    Optional,
    TypeVar,
    Union,
)

from pydantic import Field

from ..base import (
    BackendCapabilities,
    BaseModel,
    Channel,
    ChannelRegistry,
    Message,
    Organization,
    Presence,
    User,
    UserRegistry,
)
from ..format.variant import Format

__all__ = (
    "Backend",
    "BackendBase",
    "SyncHelper",
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

    # =========================================================================
    # Resolution methods for incomplete objects
    # =========================================================================

    async def resolve_user(self, user: User) -> User:
        """Resolve an incomplete user to a complete one.

        If the user is already complete (has all required fields), returns it as-is.
        Otherwise, fetches the full user data from the backend.

        Args:
            user: A User object that may be incomplete.

        Returns:
            A complete User object with all fields populated.

        Raises:
            ValueError: If the user cannot be resolved (no id or name).

        Example:
            >>> # User from a message might only have id
            >>> incomplete_user = message.author
            >>> full_user = await backend.resolve_user(incomplete_user)
            >>> print(full_user.email)  # Now populated
        """
        # If already complete and not marked incomplete, return as-is
        if user.is_complete and not user.is_incomplete:
            return user

        # Try to resolve using available identifiers
        if user.id:
            resolved = await self.fetch_user(id=user.id)
        elif user.name:
            resolved = await self.fetch_user(name=user.name)
        elif hasattr(user, "handle") and user.handle:
            resolved = await self.fetch_user(handle=user.handle)
        elif hasattr(user, "email") and user.email:
            resolved = await self.fetch_user(email=user.email)
        else:
            raise ValueError("Cannot resolve user: no id, name, handle, or email available")

        if resolved:
            resolved.mark_complete()
            return resolved

        # If we couldn't resolve but have partial info, return original
        return user

    async def resolve_channel(self, channel: Channel) -> Channel:
        """Resolve an incomplete channel to a complete one.

        If the channel is already complete (has all required fields), returns it as-is.
        Otherwise, fetches the full channel data from the backend.

        Args:
            channel: A Channel object that may be incomplete.

        Returns:
            A complete Channel object with all fields populated.

        Raises:
            ValueError: If the channel cannot be resolved (no id or name).

        Example:
            >>> # Channel from config might only have name
            >>> incomplete_channel = Channel(name="general")
            >>> full_channel = await backend.resolve_channel(incomplete_channel)
            >>> print(full_channel.id)  # Now populated
        """
        # If already complete and not marked incomplete, return as-is
        if channel.is_complete and not channel.is_incomplete:
            return channel

        # Try to resolve using available identifiers
        if channel.id:
            resolved = await self.fetch_channel(id=channel.id)
        elif channel.name:
            resolved = await self.fetch_channel(name=channel.name)
        else:
            raise ValueError("Cannot resolve channel: no id or name available")

        if resolved:
            resolved.mark_complete()
            return resolved

        # If we couldn't resolve but have partial info, return original
        return channel

    async def resolve_room(self, room: Channel) -> Channel:
        """Resolve an incomplete room to a complete one.

        This is an alias for resolve_channel. Use whichever terminology
        fits your platform (room for Symphony/Matrix, channel for Slack/Discord).

        Args:
            room: A Channel object that may be incomplete.

        Returns:
            A complete Channel object with all fields populated.
        """
        return await self.resolve_channel(room)

    # =========================================================================
    # Organization lookup methods
    # =========================================================================

    async def fetch_organization(
        self,
        identifier: Optional[Union[str, Organization]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Organization]:
        """Fetch an organization from the backend.

        An organization is the top-level container (guild, workspace, pod, etc.).

        Args:
            identifier: An Organization object or organization ID string.
            id: Organization ID (alternative to positional identifier).
            name: Organization name to search for.

        Returns:
            The organization if found, None otherwise.

        Raises:
            NotImplementedError: If the backend doesn't support organizations.
        """
        raise NotImplementedError("This backend does not support organizations")

    async def fetch_organization_by_name(
        self,
        name: str,
    ) -> Optional[Organization]:
        """Fetch an organization by name.

        This is a convenience method for looking up organizations by name.

        Args:
            name: The organization name to search for (case-insensitive).

        Returns:
            The organization if found, None otherwise.

        Raises:
            NotImplementedError: If the backend doesn't support organizations.
        """
        raise NotImplementedError("This backend does not support organizations")

    async def list_organizations(self) -> List[Organization]:
        """List all organizations the bot has access to.

        Returns:
            List of organizations.

        Raises:
            NotImplementedError: If the backend doesn't support organizations.
        """
        raise NotImplementedError("This backend does not support organizations")

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

    async def resolve_message(self, message: Message) -> Message:
        """Resolve incomplete nested objects in a Message.

        Resolves the message's author and channel if they are incomplete.
        This is useful when a message is created with partial information
        that needs to be filled in before sending.

        Args:
            message: The message to resolve.

        Returns:
            The message with resolved author and channel.

        Example:
            >>> msg = Message(
            ...     content="Hello",
            ...     channel=Channel(name="general"),
            ...     author=User(email="john@example.com"),
            ... )
            >>> resolved = await backend.resolve_message(msg)
            >>> print(resolved.channel.id)  # Now populated
        """
        if message.author and message.author.is_incomplete:
            message.author = await self.resolve_user(message.author)

        if message.channel and message.channel.is_incomplete:
            message.channel = await self.resolve_channel(message.channel)

        return message

    # =========================================================================
    # Message methods
    # =========================================================================

    async def _resolve_channel_id(self, channel: Union[str, Channel]) -> str:
        """Helper to resolve a channel argument to an ID string.

        Handles string IDs, complete Channel objects, and incomplete
        Channel objects that need resolution.

        Args:
            channel: A channel ID string or Channel object.

        Returns:
            The channel ID string.

        Raises:
            ValueError: If the channel cannot be resolved.
        """
        if isinstance(channel, str):
            return channel

        if channel.is_complete:
            return channel.id

        # Resolve incomplete channel
        resolved = await self.resolve_channel(channel)
        return resolved.id

    async def _resolve_user_id(self, user: Union[str, User]) -> str:
        """Helper to resolve a user argument to an ID string.

        Handles string IDs, complete User objects, and incomplete
        User objects that need resolution.

        Args:
            user: A user ID string or User object.

        Returns:
            The user ID string.

        Raises:
            ValueError: If the user cannot be resolved.
        """
        if isinstance(user, str):
            return user

        if user.is_complete:
            return user.id

        # Resolve incomplete user
        resolved = await self.resolve_user(user)
        return resolved.id

    async def _resolve_message_id(self, message: Union[str, Message], channel: Optional[Union[str, Channel]] = None) -> tuple[str, str]:
        """Helper to resolve a message argument to (channel_id, message_id).

        Handles string message IDs (requires channel), complete Message objects,
        and incomplete Message objects.

        Args:
            message: A message ID string or Message object.
            channel: Optional channel (required if message is a string).

        Returns:
            Tuple of (channel_id, message_id).

        Raises:
            ValueError: If the message/channel cannot be resolved.
        """
        if isinstance(message, str):
            if channel is None:
                raise ValueError("channel is required when message is a string ID")
            channel_id = await self._resolve_channel_id(channel)
            return channel_id, message

        # It's a Message object
        if message.channel:
            channel_id = await self._resolve_channel_id(message.channel)
        elif channel:
            channel_id = await self._resolve_channel_id(channel)
        else:
            raise ValueError("Message has no channel and no channel was provided")

        return channel_id, message.id

    @abstractmethod
    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages from a channel.

        Retrieves historical messages from the specified channel.

        Args:
            channel: The channel to fetch messages from (ID string or Channel object).
            limit: Maximum number of messages to fetch.
            before: Fetch messages before this message ID (for pagination).
            after: Fetch messages after this message ID (for pagination).

        Returns:
            List of messages, ordered from oldest to newest.

        Example:
            >>> # All of these work:
            >>> msgs = await backend.fetch_messages("C123")
            >>> msgs = await backend.fetch_messages(Channel(id="C123"))
            >>> msgs = await backend.fetch_messages(Channel(name="general"))  # Resolves
        """
        raise NotImplementedError("Subclass must implement fetch_messages()")

    async def search_messages(
        self,
        query: str,
        channel: Optional[Union[str, Channel]] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Message]:
        """Search for messages matching a query.

        Searches message content across channels. Requires the MESSAGE_SEARCH
        capability to be supported by the backend.

        Args:
            query: The search query string.
            channel: Optional channel to limit search to (ID string or Channel object).
            limit: Maximum number of results to return.
            **kwargs: Additional platform-specific search options (e.g., from_user,
                      has_file, date range).

        Returns:
            List of messages matching the query.

        Raises:
            NotImplementedError: If the backend doesn't support MESSAGE_SEARCH capability.

        Example:
            >>> # Search all channels
            >>> results = await backend.search_messages("important meeting")
            >>> # Search specific channel
            >>> results = await backend.search_messages("bug fix", channel="C123")
            >>> # With filters
            >>> results = await backend.search_messages("report", from_user="U123")
        """
        from ..base.capabilities import Capability

        if Capability.MESSAGE_SEARCH not in self.capabilities.capabilities:
            raise NotImplementedError(f"{self.__class__.__name__} does not support message search")

        # Default implementation - subclasses should override
        raise NotImplementedError("Subclass must implement search_messages()")

    async def fetch_new_messages(
        self,
        channel: Union[str, Channel],
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch new messages from a channel.

        This is a convenience method that fetches messages after a
        specific point, typically used for getting updates.

        Args:
            channel: The channel to fetch messages from (ID string or Channel object).
            after: Fetch messages after this message ID.

        Returns:
            List of new messages.
        """
        return await self.fetch_messages(channel=channel, after=after)

    @abstractmethod
    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to a channel.

        Args:
            channel: The channel to send to (ID string or Channel object).
            content: The message content.
            **kwargs: Additional platform-specific options (e.g., embeds,
                      attachments, thread_id).

        Returns:
            The sent message.

        Example:
            >>> # All of these work:
            >>> msg = await backend.send_message("C123", "Hello!")
            >>> msg = await backend.send_message(Channel(id="C123"), "Hello!")
            >>> msg = await backend.send_message(Channel(name="general"), "Hello!")  # Resolves
        """
        raise NotImplementedError("Subclass must implement send_message()")

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> Message:
        """Edit an existing message.

        Args:
            message: The message to edit (ID string or Message object).
            content: The new message content.
            channel: The channel containing the message (required if message is a string).
            **kwargs: Additional platform-specific options.

        Returns:
            The edited message.

        Raises:
            NotImplementedError: If the backend doesn't support editing.

        Example:
            >>> # Edit using Message object
            >>> edited = await backend.edit_message(msg, "Updated content")
            >>> # Edit using IDs
            >>> edited = await backend.edit_message("M123", "Updated", channel="C123")
        """
        raise NotImplementedError("This backend does not support message editing")

    async def delete_message(
        self,
        message: Union[str, Message],
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Delete a message.

        Args:
            message: The message to delete (ID string or Message object).
            channel: The channel containing the message (required if message is a string).

        Raises:
            NotImplementedError: If the backend doesn't support deletion.

        Example:
            >>> # Delete using Message object
            >>> await backend.delete_message(msg)
            >>> # Delete using IDs
            >>> await backend.delete_message("M123", channel="C123")
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
        channel = message.channel

        if not channel and not message.channel_id:
            raise ValueError("Cannot reply: message has no channel information")

        # Use channel object if available, otherwise use channel_id
        target_channel: Union[str, Channel] = channel if channel else message.channel_id

        return await self.send_message(
            channel=target_channel,
            content=content,
            thread_id=thread_id,
            **kwargs,
        )

    # =========================================================================
    # Real-time message streaming
    # =========================================================================

    async def stream_messages(
        self,
        channel: Optional[Union[str, Channel]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[Message]:
        """Stream incoming messages in real-time.

        This async generator yields Message objects as they arrive from
        the chat platform. It abstracts away the platform-specific
        details of real-time messaging (WebSockets, Socket Mode, datafeed, etc.).

        The stream continues until the generator is closed or an error occurs.

        Args:
            channel: Optional channel to filter messages to a specific
                     channel (ID string or Channel object). If None, yields
                     messages from all channels the bot has access to.
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
            >>> async for message in backend.stream_messages(channel="C123"):
            ...     await process_message(message)
            >>>
            >>> # Filter using Channel object
            >>> async for message in backend.stream_messages(channel=Channel(name="general")):
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

    async def get_presence(self, user: Union[str, User]) -> Optional[Presence]:
        """Get a user's presence status.

        Args:
            user: The user to get presence for (ID string or User object).

        Returns:
            The user's presence, or None if not available.

        Raises:
            NotImplementedError: If the backend doesn't support presence.

        Example:
            >>> # All of these work:
            >>> presence = await backend.get_presence("U123")
            >>> presence = await backend.get_presence(User(id="U123"))
            >>> presence = await backend.get_presence(User(email="john@example.com"))  # Resolves
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
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Add a reaction to a message.

        Args:
            message: The message to react to (ID string or Message object).
            emoji: The emoji to add (name or unicode).
            channel: The channel containing the message (required if message is a string).

        Raises:
            NotImplementedError: If the backend doesn't support reactions.

        Example:
            >>> # React using Message object
            >>> await backend.add_reaction(msg, "👍")
            >>> # React using IDs
            >>> await backend.add_reaction("M123", "👍", channel="C123")
        """
        raise NotImplementedError("This backend does not support reactions")

    async def remove_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Remove a reaction from a message.

        Args:
            message: The message to remove reaction from (ID string or Message object).
            emoji: The emoji to remove (name or unicode).
            channel: The channel containing the message (required if message is a string).

        Raises:
            NotImplementedError: If the backend doesn't support reactions.

        Example:
            >>> # Remove reaction using Message object
            >>> await backend.remove_reaction(msg, "👍")
            >>> # Remove reaction using IDs
            >>> await backend.remove_reaction("M123", "👍", channel="C123")
        """
        raise NotImplementedError("This backend does not support reactions")

    # =========================================================================
    # Channel/Room management methods
    # =========================================================================

    async def create_dm(
        self,
        users: List[Union[str, User]],
    ) -> Optional[str]:
        """Create a direct message (DM) or instant message (IM) channel.

        Creates a private conversation with one or more users.
        For single users, this creates a 1:1 DM. For multiple users,
        this may create a group DM/MIM depending on the platform.

        Args:
            users: List of users to include in the DM (ID strings or User objects).

        Returns:
            The channel/stream ID of the created DM, or None if failed.

        Raises:
            NotImplementedError: If the backend doesn't support DM creation.

        Example:
            >>> # Create DM with user IDs
            >>> dm_id = await backend.create_dm(["U123", "U456"])
            >>> # Create DM with User objects
            >>> dm_id = await backend.create_dm([User(id="U123")])
            >>> # Create DM with incomplete User (will resolve)
            >>> dm_id = await backend.create_dm([User(email="john@example.com")])
        """
        raise NotImplementedError("This backend does not support DM creation")

    async def create_im(
        self,
        users: List[Union[str, User]],
    ) -> Optional[str]:
        """Create an instant message (IM) channel.

        This is an alias for create_dm. Use whichever terminology
        fits your platform (IM for Symphony, DM for Discord/Slack).

        Args:
            users: List of users to include in the IM (ID strings or User objects).

        Returns:
            The channel/stream ID of the created IM, or None if failed.
        """
        return await self.create_dm(users)

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
        channel: Union[str, Channel],
        **kwargs: Any,
    ) -> None:
        """Join a channel.

        Makes the bot/user a member of the specified channel.

        Args:
            channel: The channel to join (ID string or Channel object).
            **kwargs: Additional platform-specific options:
                - key: Channel password/key (IRC).
                - invite_code: Invite code (Discord).

        Raises:
            NotImplementedError: If the backend doesn't support joining channels.

        Example:
            >>> # Join using channel ID
            >>> await backend.join_channel("C123")
            >>> # Join using Channel object
            >>> await backend.join_channel(Channel(name="general"))
        """
        raise NotImplementedError("This backend does not support joining channels")

    async def join_room(
        self,
        room: Union[str, Channel],
        **kwargs: Any,
    ) -> None:
        """Join a room.

        This is an alias for join_channel. Use whichever terminology
        fits your platform.

        Args:
            room: The room to join (ID string or Channel object).
            **kwargs: Additional platform-specific options.
        """
        return await self.join_channel(room, **kwargs)

    async def leave_channel(
        self,
        channel: Union[str, Channel],
        **kwargs: Any,
    ) -> None:
        """Leave a channel.

        Removes the bot/user from the specified channel.

        Args:
            channel: The channel to leave (ID string or Channel object).
            **kwargs: Additional platform-specific options:
                - message: Part message (IRC).

        Raises:
            NotImplementedError: If the backend doesn't support leaving channels.

        Example:
            >>> # Leave using channel ID
            >>> await backend.leave_channel("C123")
            >>> # Leave using Channel object
            >>> await backend.leave_channel(Channel(id="C123", name="general"))
        """
        raise NotImplementedError("This backend does not support leaving channels")

    async def leave_room(
        self,
        room: Union[str, Channel],
        **kwargs: Any,
    ) -> None:
        """Leave a room.

        This is an alias for leave_channel. Use whichever terminology
        fits your platform.

        Args:
            room: The room to leave (ID string or Channel object).
            **kwargs: Additional platform-specific options.
        """
        return await self.leave_channel(room, **kwargs)

    # =========================================================================
    # Extended messaging methods
    # =========================================================================

    async def send_action(
        self,
        target: Union[str, Channel, User],
        action: str,
    ) -> None:
        """Send an action/emote message.

        Sends an action message (like IRC's /me command).
        On IRC this is a CTCP ACTION. On other platforms,
        this may be formatted as italicized text or similar.

        Args:
            target: The channel or user to send to (ID string, Channel, or User).
            action: The action text (e.g., "waves hello").

        Raises:
            NotImplementedError: If the backend doesn't support actions.

        Example:
            >>> # Send action to channel
            >>> await backend.send_action(Channel(name="#general"), "waves hello")
            >>> # Send action to user
            >>> await backend.send_action(User(id="U123"), "waves hello")
        """
        raise NotImplementedError("This backend does not support action messages")

    async def send_notice(
        self,
        target: Union[str, Channel, User],
        text: str,
    ) -> None:
        """Send a notice message.

        Sends a notice (typically displayed differently from regular messages).
        On IRC this is a NOTICE. Other platforms may not distinguish notices.

        Args:
            target: The channel or user to send to (ID string, Channel, or User).
            text: The notice text.

        Raises:
            NotImplementedError: If the backend doesn't support notices.

        Example:
            >>> # Send notice to channel
            >>> await backend.send_notice(Channel(name="#general"), "Server maintenance")
            >>> # Send notice to user
            >>> await backend.send_notice(User(id="U123"), "You have been warned")
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
        from ..base.mention import mention_user_for_backend

        return mention_user_for_backend(user, self.__class__.name)

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for this backend.

        Args:
            channel: The channel to mention.

        Returns:
            The formatted mention string.
        """
        from ..base.mention import mention_channel_for_backend

        return mention_channel_for_backend(channel, self.__class__.name)

    def mention_here(self) -> str:
        """Format an @here mention for this backend.

        Notifies all users who are currently active/online in the channel.
        Subclasses should override this with platform-specific format.

        Returns:
            The formatted @here mention string.
        """
        return "@here"

    def mention_everyone(self) -> str:
        """Format an @everyone mention for this backend.

        Notifies all members of the channel/server.
        Subclasses should override this with platform-specific format.

        Returns:
            The formatted @everyone mention string.
        """
        return "@everyone"

    def mention_channel_all(self) -> str:
        """Format an @channel mention for this backend.

        Notifies all members of the current channel (Slack-specific concept).
        For platforms without this distinction, defaults to @everyone.
        Subclasses should override this with platform-specific format.

        Returns:
            The formatted @channel mention string.
        """
        return self.mention_everyone()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(connected={self.connected})"


# Alias for convenience
Backend = BackendBase
