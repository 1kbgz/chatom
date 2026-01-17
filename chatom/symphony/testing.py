"""Mock Symphony backend for testing.

This module provides a mock implementation of the Symphony backend
that doesn't require actual Symphony servers.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field

from ..backend_registry import BackendBase
from ..base import (
    SYMPHONY_CAPABILITIES,
    BackendCapabilities,
    Channel,
    Message,
    Presence,
    User,
)
from ..format.variant import Format
from .channel import SymphonyChannel
from .config import SymphonyConfig
from .mention import mention_user as _mention_user
from .message import SymphonyMessage
from .presence import SymphonyPresence, SymphonyPresenceStatus
from .user import SymphonyUser

__all__ = ("MockSymphonyBackend",)


class MockSymphonyBackend(BackendBase):
    """Mock Symphony backend for testing.

    This provides a testing-friendly implementation that simulates
    Symphony operations without requiring actual servers.

    Attributes:
        mock_users: Dictionary of mock users by ID.
        mock_streams: Dictionary of mock streams (channels) by ID.
        mock_messages: Dictionary of messages by stream ID.
        mock_presence: Dictionary of presence by user ID.
        sent_messages: List of sent messages for verification.
        edited_messages: List of edited message IDs.
        deleted_messages: List of deleted message IDs.
        presence_changes: List of presence changes for verification.

    Example:
        >>> from chatom.symphony import MockSymphonyBackend, SymphonyConfig
        >>> backend = MockSymphonyBackend()
        >>> await backend.connect()
        >>> # Add mock data
        >>> backend.add_mock_user(123456789, "Test User", "testuser")
        >>> backend.add_mock_stream("stream123", "Test Room")
        >>> # Verify operations
        >>> await backend.send_message("stream123", "<messageML>Hello</messageML>")
        >>> assert len(backend.sent_messages) == 1
    """

    name: ClassVar[str] = "symphony"
    display_name: ClassVar[str] = "Symphony (Mock)"
    format: ClassVar[Format] = Format.SYMPHONY_MESSAGEML

    capabilities: Optional[BackendCapabilities] = SYMPHONY_CAPABILITIES
    config: SymphonyConfig = Field(default_factory=SymphonyConfig)

    # Mock data stores
    mock_users: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    mock_streams: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    mock_messages: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    mock_presence: Dict[str, SymphonyPresenceStatus] = Field(default_factory=dict)

    # Tracking for verification
    sent_messages: List[Dict[str, Any]] = Field(default_factory=list)
    edited_messages: List[Dict[str, Any]] = Field(default_factory=list)
    deleted_messages: List[str] = Field(default_factory=list)
    presence_changes: List[Dict[str, Any]] = Field(default_factory=list)
    created_ims: List[List[int]] = Field(default_factory=list)
    created_rooms: List[Dict[str, Any]] = Field(default_factory=list)

    # Mock bot info
    _mock_bot_user_id: int = 999999999

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    def add_mock_user(
        self,
        user_id: int,
        display_name: str,
        username: str,
        email: Optional[str] = None,
    ) -> None:
        """Add a mock user.

        Args:
            user_id: The user's Symphony ID.
            display_name: The user's display name.
            username: The user's username.
            email: The user's email address.
        """
        self.mock_users[str(user_id)] = {
            "id": user_id,
            "display_name": display_name,
            "username": username,
            "email": email or f"{username}@example.com",
        }

    def add_mock_stream(
        self,
        stream_id: str,
        name: str,
        stream_type: str = "ROOM",
    ) -> None:
        """Add a mock stream (channel).

        Args:
            stream_id: The stream ID.
            name: The stream name.
            stream_type: The stream type (ROOM, IM, MIM).
        """
        self.mock_streams[stream_id] = {
            "id": stream_id,
            "name": name,
            "type": stream_type,
        }
        if stream_id not in self.mock_messages:
            self.mock_messages[stream_id] = []

    def add_mock_message(
        self,
        stream_id: str,
        user_id: int,
        content: str,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """Add a mock message to a stream.

        Args:
            stream_id: The stream ID.
            user_id: The sender's user ID.
            content: The message content (MessageML).
            message_id: Optional message ID. Generated if not provided.
            timestamp: Optional timestamp. Uses current time if not provided.

        Returns:
            The message ID.
        """
        if stream_id not in self.mock_messages:
            self.mock_messages[stream_id] = []

        if message_id is None:
            message_id = str(uuid.uuid4())

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        msg = {
            "message_id": message_id,
            "user_id": user_id,
            "content": content,
            "timestamp": timestamp,
            "stream_id": stream_id,
        }
        self.mock_messages[stream_id].append(msg)
        return message_id

    def set_mock_presence(
        self,
        user_id: str,
        status: SymphonyPresenceStatus,
    ) -> None:
        """Set mock presence for a user.

        Args:
            user_id: The user ID.
            status: The presence status.
        """
        self.mock_presence[user_id] = status

    async def connect(self) -> None:
        """Connect to mock Symphony.

        Always succeeds immediately.
        """
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from mock Symphony."""
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
            id: User ID.
            name: Display name to search for.
            email: Email address to search for.
            handle: Username to search for.

        Returns:
            The user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, SymphonyUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

            # Check mock data
            if id in self.mock_users:
                data = self.mock_users[id]
                user = SymphonyUser(
                    id=str(data["id"]),
                    name=data["display_name"],
                    handle=data["username"],
                    email=data["email"],
                    user_id=data["id"],
                )
                self.users.add(user)
                return user

        # Search by email
        if email:
            for uid, data in self.mock_users.items():
                if data.get("email") == email:
                    return await self.fetch_user(uid)

        # Search by name or handle
        search_term = name or handle
        if search_term:
            search_lower = search_term.lower()
            for uid, data in self.mock_users.items():
                if data["display_name"].lower() == search_lower or data["username"].lower() == search_lower:
                    return await self.fetch_user(uid)

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a mock channel (stream) by ID or name.

        Args:
            identifier: A Channel object or stream ID string.
            id: Stream ID.
            name: Stream name to search for.

        Returns:
            The channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, SymphonyChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached

            # Check mock data
            if id in self.mock_streams:
                data = self.mock_streams[id]
                channel = SymphonyChannel(
                    id=id,
                    name=data["name"],
                    stream_id=id,
                )
                self.channels.add(channel)
                return channel

        # Search by name
        if name:
            name_lower = name.lower()
            for sid, data in self.mock_streams.items():
                if data["name"].lower() == name_lower:
                    return await self.fetch_channel(sid)

        return None

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages from a mock stream.

        Args:
            channel_id: The stream ID.
            limit: Maximum number of messages.
            before: Fetch messages before this timestamp (ms).
            after: Fetch messages after this timestamp (ms).

        Returns:
            List of messages.
        """
        if channel_id not in self.mock_messages:
            return []

        messages_data = self.mock_messages[channel_id]

        # Filter by timestamp if specified
        filtered = messages_data
        if before:
            before_ts = int(before)
            before_dt = datetime.fromtimestamp(before_ts / 1000, tz=timezone.utc)
            filtered = [m for m in filtered if m["timestamp"] < before_dt]
        if after:
            after_ts = int(after)
            after_dt = datetime.fromtimestamp(after_ts / 1000, tz=timezone.utc)
            filtered = [m for m in filtered if m["timestamp"] >= after_dt]

        # Sort by timestamp (newest first) and limit
        filtered = sorted(filtered, key=lambda m: m["timestamp"], reverse=True)
        filtered = filtered[:limit]

        messages: List[Message] = []
        for raw in filtered:
            message = SymphonyMessage(
                id=raw["message_id"],
                content=raw["content"],
                timestamp=raw["timestamp"],
                user_id=str(raw["user_id"]),
                channel_id=channel_id,
            )
            messages.append(message)

        return messages

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a mock message.

        Args:
            channel_id: The stream ID.
            content: The message content (MessageML).
            **kwargs: Additional options (data, attachments).

        Returns:
            The sent message.
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Track sent message
        sent = {
            "message_id": message_id,
            "stream_id": channel_id,
            "content": content,
            "timestamp": timestamp,
            "data": kwargs.get("data"),
            "attachments": kwargs.get("attachments"),
        }
        self.sent_messages.append(sent)

        # Also add to mock messages
        if channel_id not in self.mock_messages:
            self.mock_messages[channel_id] = []
        self.mock_messages[channel_id].append(
            {
                "message_id": message_id,
                "user_id": self._mock_bot_user_id,
                "content": content,
                "timestamp": timestamp,
                "stream_id": channel_id,
            }
        )

        return SymphonyMessage(
            id=message_id,
            content=content,
            timestamp=timestamp,
            user_id=str(self._mock_bot_user_id),
            channel_id=channel_id,
        )

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit a mock message.

        Args:
            channel_id: The stream ID.
            message_id: The message ID.
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        timestamp = datetime.now(timezone.utc)

        # Track edit
        self.edited_messages.append(
            {
                "message_id": message_id,
                "stream_id": channel_id,
                "new_content": content,
                "timestamp": timestamp,
            }
        )

        # Update in mock messages
        if channel_id in self.mock_messages:
            for msg in self.mock_messages[channel_id]:
                if msg["message_id"] == message_id:
                    msg["content"] = content
                    break

        return SymphonyMessage(
            id=message_id,
            content=content,
            timestamp=timestamp,
            user_id=str(self._mock_bot_user_id),
            channel_id=channel_id,
        )

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete (suppress) a mock message.

        Args:
            channel_id: The stream ID.
            message_id: The message ID.
        """
        self.deleted_messages.append(message_id)

        # Remove from mock messages
        if channel_id in self.mock_messages:
            self.mock_messages[channel_id] = [m for m in self.mock_messages[channel_id] if m["message_id"] != message_id]

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set mock presence.

        Args:
            status: Presence status.
            status_text: Not used in Symphony.
            **kwargs: Additional options.
        """
        # Map status
        status_map = {
            "available": SymphonyPresenceStatus.AVAILABLE,
            "online": SymphonyPresenceStatus.AVAILABLE,
            "busy": SymphonyPresenceStatus.BUSY,
            "dnd": SymphonyPresenceStatus.BUSY,
            "away": SymphonyPresenceStatus.AWAY,
            "idle": SymphonyPresenceStatus.AWAY,
            "offline": SymphonyPresenceStatus.OFFLINE,
        }

        mapped_status = status_map.get(status.lower(), SymphonyPresenceStatus.AVAILABLE)

        # Track change
        self.presence_changes.append(
            {
                "status": status,
                "mapped_status": mapped_status,
                "soft": kwargs.get("soft", True),
            }
        )

        # Update bot's presence
        self.mock_presence[str(self._mock_bot_user_id)] = mapped_status

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get mock presence for a user.

        Args:
            user_id: The user ID.

        Returns:
            The user's presence.
        """
        symphony_status = self.mock_presence.get(user_id, SymphonyPresenceStatus.OFFLINE)

        # Map Symphony status to base PresenceStatus
        from ..base import PresenceStatus

        status_map = {
            SymphonyPresenceStatus.AVAILABLE: PresenceStatus.ONLINE,
            SymphonyPresenceStatus.BUSY: PresenceStatus.DND,
            SymphonyPresenceStatus.AWAY: PresenceStatus.IDLE,
            SymphonyPresenceStatus.ON_THE_PHONE: PresenceStatus.DND,
            SymphonyPresenceStatus.BE_RIGHT_BACK: PresenceStatus.IDLE,
            SymphonyPresenceStatus.IN_A_MEETING: PresenceStatus.DND,
            SymphonyPresenceStatus.OUT_OF_OFFICE: PresenceStatus.IDLE,
            SymphonyPresenceStatus.OFF_WORK: PresenceStatus.OFFLINE,
            SymphonyPresenceStatus.OFFLINE: PresenceStatus.OFFLINE,
        }
        base_status = status_map.get(symphony_status, PresenceStatus.UNKNOWN)

        return SymphonyPresence(
            user_id=user_id,
            status=base_status,
            symphony_status=symphony_status,
        )

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction.

        Symphony doesn't support reactions.

        Raises:
            NotImplementedError: Symphony doesn't support reactions.
        """
        raise NotImplementedError("Symphony does not support emoji reactions")

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction.

        Symphony doesn't support reactions.

        Raises:
            NotImplementedError: Symphony doesn't support reactions.
        """
        raise NotImplementedError("Symphony does not support emoji reactions")

    def mention_user(self, user: User) -> str:
        """Format a user mention.

        Args:
            user: The user to mention.

        Returns:
            Symphony mention format.
        """
        if isinstance(user, SymphonyUser):
            return _mention_user(user)
        return f'<mention uid="{user.id}"/>'

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention.

        Args:
            channel: The channel to mention.

        Returns:
            The channel name.
        """
        if isinstance(channel, SymphonyChannel):
            return channel.name or channel.stream_id or channel.id
        return channel.name or channel.id

    async def create_dm(self, user_ids: List[str]) -> Optional[str]:
        """Create a mock DM/IM.

        Args:
            user_ids: List of user IDs.

        Returns:
            The stream ID.
        """
        # Convert to ints for tracking (Symphony uses int IDs)
        int_ids = [int(uid) for uid in user_ids]
        self.created_ims.append(int_ids)
        stream_id = f"im_{uuid.uuid4()}"
        self.add_mock_stream(stream_id, f"IM with {len(user_ids)} users", "IM")
        return stream_id

    async def create_im(self, user_ids: List[str]) -> Optional[str]:
        """Create a mock IM.

        This is an alias for create_dm.

        Args:
            user_ids: List of user IDs.

        Returns:
            The stream ID.
        """
        return await self.create_dm(user_ids)

    async def create_channel(
        self,
        name: str,
        description: str = "",
        public: bool = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a mock channel/room.

        Args:
            name: The room name.
            description: The room description.
            public: Whether the room is public.
            **kwargs: Additional options:
                - read_only: Whether the room is read-only.

        Returns:
            The stream ID.
        """
        stream_id = f"room_{uuid.uuid4()}"
        self.created_rooms.append(
            {
                "stream_id": stream_id,
                "name": name,
                "description": description,
                "public": public,
                "read_only": kwargs.get("read_only", False),
            }
        )
        self.add_mock_stream(stream_id, name, "ROOM")
        return stream_id

    async def create_room(
        self,
        name: str,
        description: str = "",
        public: bool = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a mock room.

        This is an alias for create_channel.

        Args:
            name: The room name.
            description: The room description.
            public: Whether the room is public.
            **kwargs: Additional options.

        Returns:
            The stream ID.
        """
        return await self.create_channel(name, description, public, **kwargs)

    def reset(self) -> None:
        """Reset all mock data and tracking.

        Useful for cleaning up between tests.
        """
        self.mock_users.clear()
        self.mock_streams.clear()
        self.mock_messages.clear()
        self.mock_presence.clear()
        self.sent_messages.clear()
        self.edited_messages.clear()
        self.deleted_messages.clear()
        self.presence_changes.clear()
        self.created_ims.clear()
        self.created_rooms.clear()
        self.users.clear()
        self.channels.clear()
