"""Connection and registry classes for chatom.

This module provides base classes for backend connections and registries
for looking up users and channels.
"""

from abc import abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import Field

from .base import BaseModel
from .channel import Channel
from .user import User

__all__ = (
    "Connection",
    "UserRegistry",
    "ChannelRegistry",
    "LookupError",
)


class LookupError(Exception):
    """Raised when a lookup fails."""

    pass


T = TypeVar("T", bound=BaseModel)


class Registry(BaseModel, Generic[T]):
    """Base registry for storing and looking up entities.

    This is a generic base class for user and channel registries.
    Subclasses should override lookup methods for backend-specific behavior.

    Attributes:
        _cache_by_id: Internal cache mapping IDs to entities.
        _cache_by_name: Internal cache mapping names to entities.
    """

    _cache_by_id: Dict[str, T] = {}
    _cache_by_name: Dict[str, T] = {}

    def model_post_init(self, __context: Any) -> None:
        """Initialize internal caches."""
        object.__setattr__(self, "_cache_by_id", {})
        object.__setattr__(self, "_cache_by_name", {})

    def add(self, entity: T) -> None:
        """Add an entity to the registry.

        Args:
            entity: The entity to add.
        """
        if hasattr(entity, "id") and entity.id:
            self._cache_by_id[entity.id] = entity
        if hasattr(entity, "name") and entity.name:
            self._cache_by_name[entity.name] = entity

    def get_by_id(self, id: str) -> Optional[T]:
        """Get an entity by ID from cache.

        Args:
            id: The entity ID.

        Returns:
            The entity if found, None otherwise.
        """
        return self._cache_by_id.get(id)

    def get_by_name(self, name: str) -> Optional[T]:
        """Get an entity by name from cache.

        Args:
            name: The entity name.

        Returns:
            The entity if found, None otherwise.
        """
        return self._cache_by_name.get(name)

    def all(self) -> List[T]:
        """Get all entities in the registry.

        Returns:
            List of all entities.
        """
        return list(self._cache_by_id.values())

    def clear(self) -> None:
        """Clear all cached entities."""
        self._cache_by_id.clear()
        self._cache_by_name.clear()


class UserRegistry(Registry[User]):
    """Registry for looking up users by ID, name, or email.

    This can be subclassed by backends to provide additional
    lookup capabilities like fetching from an API.

    Example:
        >>> registry = UserRegistry()
        >>> registry.add(User(id="123", name="John", email="john@example.com"))
        >>> registry.get_by_id("123")
        User(id='123', name='John', ...)
    """

    _cache_by_email: Dict[str, User] = {}
    _cache_by_handle: Dict[str, User] = {}

    def model_post_init(self, __context: Any) -> None:
        """Initialize internal caches."""
        super().model_post_init(__context)
        object.__setattr__(self, "_cache_by_email", {})
        object.__setattr__(self, "_cache_by_handle", {})

    def add(self, user: User) -> None:
        """Add a user to the registry.

        Args:
            user: The user to add.
        """
        super().add(user)
        if user.email:
            self._cache_by_email[user.email.lower()] = user
        if user.handle:
            self._cache_by_handle[user.handle.lower()] = user

    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address.

        Args:
            email: The email address.

        Returns:
            The user if found, None otherwise.
        """
        return self._cache_by_email.get(email.lower())

    def get_by_handle(self, handle: str) -> Optional[User]:
        """Get a user by handle/username.

        Args:
            handle: The handle/username.

        Returns:
            The user if found, None otherwise.
        """
        return self._cache_by_handle.get(handle.lower())

    def lookup(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Look up a user by any available identifier.

        Args:
            id: User ID to look up.
            name: User name to look up.
            email: User email to look up.
            handle: User handle to look up.

        Returns:
            The user if found, None otherwise.
        """
        if id:
            result = self.get_by_id(id)
            if result:
                return result
        if email:
            result = self.get_by_email(email)
            if result:
                return result
        if handle:
            result = self.get_by_handle(handle)
            if result:
                return result
        if name:
            result = self.get_by_name(name)
            if result:
                return result
        return None

    def user_to_id(self, user: User) -> str:
        """Get the ID for a user.

        Args:
            user: The user object.

        Returns:
            The user's ID.

        Raises:
            LookupError: If user has no ID.
        """
        if user.id:
            return user.id
        raise LookupError(f"User has no ID: {user}")

    def user_to_name(self, user: User) -> str:
        """Get the display name for a user.

        Args:
            user: The user object.

        Returns:
            The user's display name.
        """
        return user.display_name

    def user_to_email(self, user: User) -> Optional[str]:
        """Get the email for a user.

        Args:
            user: The user object.

        Returns:
            The user's email or None.
        """
        return user.email if user.email else None

    def id_to_user(self, id: str) -> User:
        """Look up a user by ID.

        Args:
            id: The user ID.

        Returns:
            The user.

        Raises:
            LookupError: If user not found.
        """
        user = self.get_by_id(id)
        if user:
            return user
        raise LookupError(f"User not found with ID: {id}")

    def name_to_user(self, name: str) -> User:
        """Look up a user by name.

        Args:
            name: The user name.

        Returns:
            The user.

        Raises:
            LookupError: If user not found.
        """
        user = self.get_by_name(name)
        if user:
            return user
        raise LookupError(f"User not found with name: {name}")

    def email_to_user(self, email: str) -> User:
        """Look up a user by email.

        Args:
            email: The email address.

        Returns:
            The user.

        Raises:
            LookupError: If user not found.
        """
        user = self.get_by_email(email)
        if user:
            return user
        raise LookupError(f"User not found with email: {email}")

    def clear(self) -> None:
        """Clear all cached users."""
        super().clear()
        self._cache_by_email.clear()
        self._cache_by_handle.clear()


class ChannelRegistry(Registry[Channel]):
    """Registry for looking up channels by ID or name.

    This can be subclassed by backends to provide additional
    lookup capabilities like fetching from an API.

    Example:
        >>> registry = ChannelRegistry()
        >>> registry.add(Channel(id="C123", name="general"))
        >>> registry.get_by_id("C123")
        Channel(id='C123', name='general', ...)
    """

    def lookup(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Look up a channel by any available identifier.

        Args:
            id: Channel ID to look up.
            name: Channel name to look up.

        Returns:
            The channel if found, None otherwise.
        """
        if id:
            result = self.get_by_id(id)
            if result:
                return result
        if name:
            result = self.get_by_name(name)
            if result:
                return result
        return None

    def channel_to_id(self, channel: Channel) -> str:
        """Get the ID for a channel.

        Args:
            channel: The channel object.

        Returns:
            The channel's ID.

        Raises:
            LookupError: If channel has no ID.
        """
        if channel.id:
            return channel.id
        raise LookupError(f"Channel has no ID: {channel}")

    def channel_to_name(self, channel: Channel) -> str:
        """Get the name for a channel.

        Args:
            channel: The channel object.

        Returns:
            The channel's name.
        """
        return channel.name or channel.id

    def id_to_channel(self, id: str) -> Channel:
        """Look up a channel by ID.

        Args:
            id: The channel ID.

        Returns:
            The channel.

        Raises:
            LookupError: If channel not found.
        """
        channel = self.get_by_id(id)
        if channel:
            return channel
        raise LookupError(f"Channel not found with ID: {id}")

    def name_to_channel(self, name: str) -> Channel:
        """Look up a channel by name.

        Args:
            name: The channel name.

        Returns:
            The channel.

        Raises:
            LookupError: If channel not found.
        """
        channel = self.get_by_name(name)
        if channel:
            return channel
        raise LookupError(f"Channel not found with name: {name}")


class Connection(BaseModel):
    """Base class for a connection to a backend service.

    This provides a unified interface for connecting to chat platforms,
    managing users and channels, and sending messages.

    Subclasses should implement the abstract methods for platform-specific
    behavior.

    Attributes:
        backend: The backend type identifier (e.g., 'slack', 'discord').
        connected: Whether currently connected.
        users: Registry of users.
        channels: Registry of channels.
    """

    backend: str = Field(
        default="",
        description="The backend type identifier.",
    )
    connected: bool = Field(
        default=False,
        description="Whether currently connected.",
    )
    users: UserRegistry = Field(
        default_factory=UserRegistry,
        description="Registry of users.",
    )
    channels: ChannelRegistry = Field(
        default_factory=ChannelRegistry,
        description="Registry of channels.",
    )

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the backend.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclass must implement connect()")

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the backend.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclass must implement disconnect()")

    @abstractmethod
    async def fetch_user(self, id: str) -> Optional[User]:
        """Fetch a user from the backend by ID.

        Args:
            id: The user ID.

        Returns:
            The user if found, None otherwise.
        """
        raise NotImplementedError("Subclass must implement fetch_user()")

    @abstractmethod
    async def fetch_channel(self, id: str) -> Optional[Channel]:
        """Fetch a channel from the backend by ID.

        Args:
            id: The channel ID.

        Returns:
            The channel if found, None otherwise.
        """
        raise NotImplementedError("Subclass must implement fetch_channel()")

    async def get_user(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Get a user by any identifier, fetching from backend if needed.

        First checks the local registry, then fetches from backend if
        not found and an ID was provided.

        Args:
            id: User ID.
            name: User name.
            email: User email.
            handle: User handle.

        Returns:
            The user if found, None otherwise.
        """
        # Try local registry first
        user = self.users.lookup(id=id, name=name, email=email, handle=handle)
        if user:
            return user

        # Try fetching from backend if ID provided
        if id:
            user = await self.fetch_user(id)
            if user:
                self.users.add(user)
                return user

        return None

    async def get_channel(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Get a channel by any identifier, fetching from backend if needed.

        First checks the local registry, then fetches from backend if
        not found and an ID was provided.

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

        # Try fetching from backend if ID provided
        if id:
            channel = await self.fetch_channel(id)
            if channel:
                self.channels.add(channel)
                return channel

        return None

    def __repr__(self) -> str:
        return f"Connection(backend={self.backend!r}, connected={self.connected})"
