"""Mock Matrix backend for testing.

This module provides a mock implementation of the Matrix backend
for use in testing without requiring an actual Matrix connection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import PrivateAttr

from ..base import Channel, Message, Presence, PresenceStatus, User
from .backend import MatrixBackend
from .channel import MatrixChannel
from .message import MatrixMessage
from .presence import MatrixPresence
from .user import MatrixUser

__all__ = ("MockMatrixBackend",)


class MockMatrixBackend(MatrixBackend):
    """Mock Matrix backend for testing.

    This class provides a mock implementation of the Matrix backend
    that doesn't require an actual Matrix connection. It stores all
    data in memory and provides methods to set up mock data for tests.

    Example:
        >>> backend = MockMatrixBackend()
        >>> backend.add_mock_user("@user:matrix.org", "TestUser")
        >>> backend.add_mock_channel("!room:matrix.org", "General")
        >>> await backend.connect()
        >>> user = await backend.fetch_user("@user:matrix.org")
        >>> assert user.name == "TestUser"
    """

    # Mock data stores
    _mock_users: Dict[str, MatrixUser] = PrivateAttr(default_factory=dict)
    _mock_channels: Dict[str, MatrixChannel] = PrivateAttr(default_factory=dict)
    _mock_messages: Dict[str, List[MatrixMessage]] = PrivateAttr(default_factory=dict)
    _mock_presence: Dict[str, MatrixPresence] = PrivateAttr(default_factory=dict)

    # Tracking stores
    _sent_messages: List[MatrixMessage] = PrivateAttr(default_factory=list)
    _edited_messages: List[MatrixMessage] = PrivateAttr(default_factory=list)
    _deleted_messages: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _reactions: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _presence_updates: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _message_counter: int = PrivateAttr(default=0)

    def __init__(self, **data: Any) -> None:
        """Initialize the mock backend."""
        super().__init__(**data)
        # Initialize mutable default fields
        self._mock_users = {}
        self._mock_channels = {}
        self._mock_messages = {}
        self._mock_presence = {}
        self._sent_messages = []
        self._edited_messages = []
        self._deleted_messages = []
        self._reactions = []
        self._presence_updates = []
        self._message_counter = 0

    def add_mock_user(
        self,
        user_id: str,
        name: str,
        *,
        display_name: Optional[str] = None,
        avatar_url: str = "",
        is_verified: bool = False,
    ) -> MatrixUser:
        """Add a mock user for testing.

        Args:
            user_id: The Matrix user ID (@user:server).
            name: The user's display name.
            display_name: Optional display name (falls back to name).
            avatar_url: URL to user's avatar.
            is_verified: Whether the user is verified.

        Returns:
            The created mock user.
        """
        user = MatrixUser(
            id=user_id,
            name=display_name or name,
            handle=user_id,
            avatar_url=avatar_url,
            user_id=user_id,
        )
        self._mock_users[user_id] = user
        self.users.add(user)
        return user

    def add_mock_channel(
        self,
        room_id: str,
        name: str,
        room_alias: Optional[str] = None,
        *,
        topic: str = "",
        is_encrypted: bool = False,
        is_direct: bool = False,
    ) -> MatrixChannel:
        """Add a mock channel/room for testing.

        Args:
            room_id: The Matrix room ID (!room:server).
            name: The room name.
            room_alias: Optional room alias (#room:server).
            topic: The room topic.
            is_encrypted: Whether the room is encrypted.
            is_direct: Whether this is a direct message room.

        Returns:
            The created mock channel.
        """
        channel = MatrixChannel(
            id=room_id,
            name=name,
            topic=topic,
            room_id=room_id,
            room_alias=room_alias or "",
        )
        self._mock_channels[room_id] = channel
        self.channels.add(channel)
        return channel

    def add_mock_message(
        self,
        room_id: str,
        user_id: str,
        content: str,
        *,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        edited: bool = False,
    ) -> str:
        """Add a mock message for testing.

        Args:
            room_id: The room containing the message.
            user_id: The sender's user ID.
            content: The message content.
            event_id: The Matrix event ID (auto-generated if not provided).
            timestamp: Message timestamp (defaults to now).
            edited: Whether the message was edited.

        Returns:
            The event ID.
        """
        if event_id is None:
            self._message_counter += 1
            event_id = f"$event_{self._message_counter}"

        message = MatrixMessage(
            id=event_id,
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc),
            user_id=user_id,
            channel_id=room_id,
            event_id=event_id,
            edited=edited,
        )
        if room_id not in self._mock_messages:
            self._mock_messages[room_id] = []
        self._mock_messages[room_id].append(message)
        return event_id

    def set_mock_presence(
        self,
        user_id: str,
        status: PresenceStatus = PresenceStatus.ONLINE,
        *,
        status_text: str = "",
        last_active_ago: Optional[int] = None,
    ) -> MatrixPresence:
        """Set mock presence for a user.

        Args:
            user_id: The user ID.
            status: The presence status.
            status_text: The status message.
            last_active_ago: Milliseconds since last activity.

        Returns:
            The created mock presence.
        """
        presence = MatrixPresence(
            user_id=user_id,
            status=status,
            status_text=status_text,
            last_active_ago=last_active_ago,
        )
        self._mock_presence[user_id] = presence
        return presence

    def add_mock_room(
        self,
        room_id: str,
        name: str,
        room_alias: Optional[str] = None,
        *,
        topic: str = "",
        is_direct: bool = False,
    ) -> MatrixChannel:
        """Add a mock room for testing.

        This is an alias for add_mock_channel, using Matrix terminology.

        Args:
            room_id: The Matrix room ID (!room:server).
            name: The room name.
            room_alias: Optional room alias (#room:server).
            topic: Optional room topic.
            is_direct: Whether this is a direct message room.

        Returns:
            The created mock room (MatrixChannel).
        """
        return self.add_mock_channel(room_id, name, room_alias, topic=topic, is_direct=is_direct)

    @property
    def sent_messages(self) -> List[MatrixMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages.
        """
        return self._sent_messages

    @property
    def edited_messages(self) -> List[MatrixMessage]:
        """Get all messages edited through this backend.

        Returns:
            List of edited messages.
        """
        return self._edited_messages

    @property
    def added_reactions(self) -> List[Dict[str, str]]:
        """Get all reactions added through this backend.

        Returns:
            List of reaction info.
        """
        return self._reactions

    def get_sent_messages(self) -> List[MatrixMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages.
        """
        return self._sent_messages.copy()

    def get_edited_messages(self) -> List[MatrixMessage]:
        """Get all messages edited through this backend.

        Returns:
            List of edited messages.
        """
        return self._edited_messages.copy()

    def get_deleted_messages(self) -> List[Dict[str, str]]:
        """Get all messages deleted through this backend.

        Returns:
            List of deleted message info (room_id, event_id).
        """
        return self._deleted_messages.copy()

    def get_reactions(self) -> List[Dict[str, str]]:
        """Get all reactions added through this backend.

        Returns:
            List of reaction info (room_id, event_id, emoji).
        """
        return self._reactions.copy()

    def get_presence_updates(self) -> List[Dict[str, Any]]:
        """Get all presence updates made through this backend.

        Returns:
            List of presence update info.
        """
        return self._presence_updates.copy()

    def clear(self) -> None:
        """Clear all mock data and tracking stores."""
        self._mock_users.clear()
        self._mock_channels.clear()
        self._mock_messages.clear()
        self._mock_presence.clear()
        self._sent_messages.clear()
        self._edited_messages.clear()
        self._deleted_messages.clear()
        self._reactions.clear()
        self._presence_updates.clear()
        self.users._items.clear()
        self.channels._items.clear()

    # Override backend methods for mock behavior

    async def connect(self) -> None:
        """Mock connect - always succeeds."""
        self.connected = True

    async def disconnect(self) -> None:
        """Mock disconnect."""
        self.connected = False

    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a mock user by ID or other attributes.

        Args:
            identifier: A User object or user ID string.
            id: User ID (Matrix ID like @user:server).
            name: Display name to search for.
            email: Unused (Matrix has no email lookup).
            handle: Username to search for.

        Returns:
            The mock user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, MatrixUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check by ID first
        if id:
            user = self._mock_users.get(id) or self.users.get_by_id(id)
            if user:
                return user

        # Search by name or handle
        search_term = name or handle
        if search_term:
            search_lower = search_term.lower()
            for user in self._mock_users.values():
                if user.name.lower() == search_lower or user.handle.lower() == search_lower:
                    return user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a mock channel by ID or name.

        Args:
            identifier: A Channel object or room ID string.
            id: Room ID.
            name: Room name to search for.

        Returns:
            The mock channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, MatrixChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check by ID first
        if id:
            channel = self._mock_channels.get(id) or self.channels.get_by_id(id)
            if channel:
                return channel

        # Search by name
        if name:
            name_lower = name.lower()
            for channel in self._mock_channels.values():
                if channel.name.lower() == name_lower:
                    return channel

        return None

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch mock messages from a room.

        Args:
            channel_id: The room to fetch from.
            limit: Maximum number of messages.
            before: Pagination token (unused in mock).
            after: Pagination token (unused in mock).

        Returns:
            List of mock messages.
        """
        messages = self._mock_messages.get(channel_id, [])

        # Sort by timestamp descending (newest first) and limit
        messages = sorted(messages, key=lambda m: m.timestamp, reverse=True)
        return messages[:limit]

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a mock message.

        Args:
            channel_id: The room to send to.
            content: The message content.
            **kwargs: Additional options.

        Returns:
            The mock sent message.
        """
        # Generate a mock event ID
        existing_count = len(self._sent_messages) + sum(len(msgs) for msgs in self._mock_messages.values())
        event_id = f"$mock_event_{existing_count}"

        message = MatrixMessage(
            id=event_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            user_id=self.config.user_id or "@bot:matrix.org",
            channel_id=channel_id,
            event_id=event_id,
        )
        self._sent_messages.append(message)
        return message

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit a mock message.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The mock edited message.
        """
        existing_count = len(self._edited_messages)
        event_id = f"$mock_edit_{existing_count}"

        message = MatrixMessage(
            id=event_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            user_id=self.config.user_id or "@bot:matrix.org",
            channel_id=channel_id,
            event_id=event_id,
            edited=True,
        )
        self._edited_messages.append(message)
        return message

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a mock message.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
        """
        self._deleted_messages.append(
            {
                "room_id": channel_id,
                "event_id": message_id,
            }
        )
        # Remove from mock messages if present
        if channel_id in self._mock_messages:
            self._mock_messages[channel_id] = [m for m in self._mock_messages[channel_id] if m.id != message_id]

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set mock presence.

        Args:
            status: The status string.
            status_text: Status message.
            **kwargs: Additional options.
        """
        self._presence_updates.append(
            {
                "status": status,
                "status_text": status_text,
                **kwargs,
            }
        )

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get mock presence for a user.

        Args:
            user_id: The user ID.

        Returns:
            The mock presence if set, None otherwise.
        """
        return self._mock_presence.get(user_id)

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a mock reaction.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
            emoji: The emoji to add.
        """
        self._reactions.append(
            {
                "room_id": channel_id,
                "event_id": message_id,
                "emoji": emoji,
                "action": "add",
            }
        )

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a mock reaction.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
            emoji: The emoji to remove.
        """
        self._reactions.append(
            {
                "room_id": channel_id,
                "event_id": message_id,
                "emoji": emoji,
                "action": "remove",
            }
        )
