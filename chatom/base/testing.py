"""Base mock backend for testing.

This module provides a generic MockBackendBase that implements common
mock functionality, reducing duplication across backend-specific mock classes.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import Field, PrivateAttr

from .base import BaseModel
from .channel import Channel
from .message import Message
from .presence import Presence, PresenceStatus
from .user import User

__all__ = ("MockBackendMixin", "MockDataStore")


# Type variables for backend-specific types
UserT = TypeVar("UserT", bound=User)
ChannelT = TypeVar("ChannelT", bound=Channel)
MessageT = TypeVar("MessageT", bound=Message)
PresenceT = TypeVar("PresenceT", bound=Presence)


class MockDataStore(BaseModel, Generic[UserT, ChannelT, MessageT, PresenceT]):
    """Generic data store for mock backends.

    This provides common storage and tracking for mock backend implementations,
    reducing code duplication across backend-specific mock classes.

    Type Parameters:
        UserT: The backend-specific User type.
        ChannelT: The backend-specific Channel type.
        MessageT: The backend-specific Message type.
        PresenceT: The backend-specific Presence type.
    """

    # Mock data stores
    mock_users: Dict[str, Any] = Field(default_factory=dict)
    mock_channels: Dict[str, Any] = Field(default_factory=dict)
    mock_messages: Dict[str, List[Any]] = Field(default_factory=dict)
    mock_presence: Dict[str, Any] = Field(default_factory=dict)

    # Tracking stores
    sent_messages: List[Any] = Field(default_factory=list)
    edited_messages: List[Any] = Field(default_factory=list)
    deleted_messages: List[Dict[str, str]] = Field(default_factory=list)
    reactions_added: List[Dict[str, str]] = Field(default_factory=list)
    reactions_removed: List[Dict[str, str]] = Field(default_factory=list)
    presence_updates: List[Dict[str, Any]] = Field(default_factory=list)
    message_counter: int = Field(default=0)

    def reset(self) -> None:
        """Reset all mock data and tracking stores."""
        self.mock_users.clear()
        self.mock_channels.clear()
        self.mock_messages.clear()
        self.mock_presence.clear()
        self.sent_messages.clear()
        self.edited_messages.clear()
        self.deleted_messages.clear()
        self.reactions_added.clear()
        self.reactions_removed.clear()
        self.presence_updates.clear()
        self.message_counter = 0

    def get_next_message_id(self) -> str:
        """Generate the next message ID.

        Returns:
            A unique message ID string.
        """
        self.message_counter += 1
        return f"msg_{self.message_counter}"


class MockBackendMixin:
    """Mixin providing common mock backend functionality.

    This mixin provides reusable implementations of mock backend methods,
    reducing code duplication across backend-specific mock classes.

    Classes using this mixin should:
    1. Define _data as a MockDataStore
    2. Define _user_class, _channel_class, _message_class, _presence_class
    3. Call super().__init__() and then _init_mock_data()
    """

    # Type classes - should be overridden by subclasses
    _user_class: Type[User] = User
    _channel_class: Type[Channel] = Channel
    _message_class: Type[Message] = Message
    _presence_class: Type[Presence] = Presence

    # Data store - should be set in __init__
    _data: MockDataStore = PrivateAttr(default_factory=MockDataStore)

    def _init_mock_data(self) -> None:
        """Initialize mock data stores. Call after super().__init__()."""
        self._data = MockDataStore()

    # =========================================================================
    # Mock data management
    # =========================================================================

    def add_mock_user_data(
        self,
        id: str,
        name: str,
        handle: Optional[str] = None,
        **extra_fields: Any,
    ) -> User:
        """Add a mock user to the backend.

        Args:
            id: The user ID.
            name: The user's display name.
            handle: The username/handle.
            **extra_fields: Additional backend-specific fields.

        Returns:
            The created mock user.
        """
        user_data = {
            "id": id,
            "name": name,
            "handle": handle or name.lower().replace(" ", ""),
            **extra_fields,
        }
        user = self._user_class.model_validate(user_data)
        self._data.mock_users[id] = user
        if hasattr(self, "users"):
            self.users.add(user)
        return user

    def add_mock_channel_data(
        self,
        id: str,
        name: str,
        **extra_fields: Any,
    ) -> Channel:
        """Add a mock channel to the backend.

        Args:
            id: The channel ID.
            name: The channel name.
            **extra_fields: Additional backend-specific fields.

        Returns:
            The created mock channel.
        """
        channel_data = {
            "id": id,
            "name": name,
            **extra_fields,
        }
        channel = self._channel_class.model_validate(channel_data)
        self._data.mock_channels[id] = channel
        if hasattr(self, "channels"):
            self.channels.add(channel)
        if id not in self._data.mock_messages:
            self._data.mock_messages[id] = []
        return channel

    def add_mock_message_data(
        self,
        channel_id: str,
        content: str,
        author_id: Optional[str] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        **extra_fields: Any,
    ) -> Message:
        """Add a mock message to a channel.

        Args:
            channel_id: The channel ID.
            content: The message content.
            author_id: The sender's user ID.
            message_id: Optional message ID (auto-generated if not provided).
            timestamp: Optional timestamp.
            **extra_fields: Additional backend-specific fields.

        Returns:
            The created mock message.
        """
        if message_id is None:
            message_id = self._data.get_next_message_id()

        message_data = {
            "id": message_id,
            "content": content,
            "channel_id": channel_id,
            "author_id": author_id,
            "timestamp": timestamp or datetime.now(timezone.utc),
            **extra_fields,
        }
        message = self._message_class.model_validate(message_data)

        if channel_id not in self._data.mock_messages:
            self._data.mock_messages[channel_id] = []
        self._data.mock_messages[channel_id].append(message)

        return message

    def set_mock_presence_data(
        self,
        user_id: str,
        status: PresenceStatus = PresenceStatus.ONLINE,
        status_text: str = "",
        **extra_fields: Any,
    ) -> Presence:
        """Set mock presence for a user.

        Args:
            user_id: The user ID.
            status: The presence status.
            status_text: Optional status text.
            **extra_fields: Additional backend-specific fields.

        Returns:
            The created presence.
        """
        presence_data = {
            "user_id": user_id,
            "status": status,
            "status_text": status_text,
            **extra_fields,
        }
        presence = self._presence_class.model_validate(presence_data)
        self._data.mock_presence[user_id] = presence
        self._data.presence_updates.append({"status": status, "status_text": status_text})
        return presence

    def reset_mock_data(self) -> None:
        """Reset all mock data and tracking stores."""
        self._data.reset()
        if hasattr(self, "users"):
            self.users.clear()
        if hasattr(self, "channels"):
            self.channels.clear()

    @property
    def sent_messages_data(self) -> List[Any]:
        """Get all messages sent through this backend."""
        return self._data.sent_messages

    @property
    def deleted_messages_data(self) -> List[Dict[str, str]]:
        """Get all deleted message references."""
        return self._data.deleted_messages

    @property
    def reactions_added_data(self) -> List[Dict[str, str]]:
        """Get all reactions added through this backend."""
        return self._data.reactions_added

    @property
    def reactions_removed_data(self) -> List[Dict[str, str]]:
        """Get all reactions removed through this backend."""
        return self._data.reactions_removed

    @property
    def presence_updates_data(self) -> List[Dict[str, Any]]:
        """Get all presence updates made through this backend."""
        return self._data.presence_updates

    # =========================================================================
    # Common mock backend operations
    # =========================================================================

    async def _mock_connect(self) -> None:
        """Mock connect implementation."""
        if hasattr(self, "connected"):
            self.connected = True

    async def _mock_disconnect(self) -> None:
        """Mock disconnect implementation."""
        if hasattr(self, "connected"):
            self.connected = False

    async def _mock_fetch_user(self, id: str) -> Optional[User]:
        """Fetch a mock user by ID.

        Args:
            id: The user ID.

        Returns:
            The user if found, None otherwise.
        """
        return self._data.mock_users.get(id)

    async def _mock_fetch_channel(self, id: str) -> Optional[Channel]:
        """Fetch a mock channel by ID.

        Args:
            id: The channel ID.

        Returns:
            The channel if found, None otherwise.
        """
        return self._data.mock_channels.get(id)

    async def _mock_fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch mock messages from a channel.

        Args:
            channel_id: The channel to fetch from.
            limit: Maximum number of messages.
            before: Fetch messages before this ID.
            after: Fetch messages after this ID.

        Returns:
            List of messages.
        """
        messages = self._data.mock_messages.get(channel_id, [])
        # Note: before/after filtering should be implemented based on backend-specific ID format
        return messages[:limit]

    async def _mock_send_message(
        self,
        channel_id: str,
        content: str,
        message_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Message:
        """Send a mock message.

        Args:
            channel_id: The channel to send to.
            content: The message content.
            message_id: Optional message ID.
            **kwargs: Additional options.

        Returns:
            The sent message.
        """
        if message_id is None:
            message_id = self._data.get_next_message_id()

        message_data = {
            "id": message_id,
            "content": content,
            "channel_id": channel_id,
            "timestamp": datetime.now(timezone.utc),
            **kwargs,
        }
        message = self._message_class.model_validate(message_data)

        self._data.sent_messages.append(message)

        if channel_id not in self._data.mock_messages:
            self._data.mock_messages[channel_id] = []
        self._data.mock_messages[channel_id].append(message)

        return message

    async def _mock_delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a mock message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
        """
        self._data.deleted_messages.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
            }
        )

        messages = self._data.mock_messages.get(channel_id, [])
        self._data.mock_messages[channel_id] = [m for m in messages if m.id != message_id]

    async def _mock_add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a mock reaction.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
            emoji: The emoji name.
        """
        self._data.reactions_added.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji.strip(":"),
            }
        )

    async def _mock_remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a mock reaction.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
            emoji: The emoji name.
        """
        self._data.reactions_removed.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji.strip(":"),
            }
        )

    async def _mock_set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set mock presence.

        Args:
            status: Presence status.
            status_text: Status text.
            **kwargs: Additional options.
        """
        self._data.presence_updates.append(
            {
                "status": status,
                "status_text": status_text,
                **kwargs,
            }
        )

    async def _mock_get_presence(self, user_id: str) -> Optional[Presence]:
        """Get mock presence for a user.

        Args:
            user_id: The user ID.

        Returns:
            The user's presence.
        """
        return self._data.mock_presence.get(user_id)
