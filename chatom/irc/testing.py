"""Mock IRC backend for testing.

This module provides a mock implementation of the IRC backend
for use in testing without requiring an actual IRC connection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import PrivateAttr

from ..base import Channel, Message, Presence, User
from .backend import IRCBackend
from .channel import IRCChannel
from .message import IRCMessage
from .user import IRCUser

__all__ = ("MockIRCBackend",)


class MockIRCBackend(IRCBackend):
    """Mock IRC backend for testing.

    This class provides a mock implementation of the IRC backend
    that doesn't require an actual IRC connection. It stores all
    data in memory and provides methods to set up mock data for tests.

    Example:
        >>> backend = MockIRCBackend()
        >>> backend.add_mock_user("testuser", "TestUser")
        >>> backend.add_mock_channel("#general")
        >>> await backend.connect()
        >>> user = await backend.fetch_user("testuser")
        >>> assert user.name == "TestUser"
    """

    # Mock data stores
    _mock_users: Dict[str, IRCUser] = PrivateAttr(default_factory=dict)
    _mock_channels: Dict[str, IRCChannel] = PrivateAttr(default_factory=dict)
    _mock_messages: Dict[str, List[IRCMessage]] = PrivateAttr(default_factory=dict)

    # Tracking stores
    _sent_messages: List[IRCMessage] = PrivateAttr(default_factory=list)
    _sent_notices: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _sent_actions: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _joined_channels: List[str] = PrivateAttr(default_factory=list)
    _parted_channels: List[Dict[str, str]] = PrivateAttr(default_factory=list)
    _presence_updates: List[Dict[str, Any]] = PrivateAttr(default_factory=list)

    def __init__(self, **data: Any) -> None:
        """Initialize the mock backend."""
        super().__init__(**data)
        # Initialize mutable default fields
        self._mock_users = {}
        self._mock_channels = {}
        self._mock_messages = {}
        self._sent_messages = []
        self._sent_notices = []
        self._sent_actions = []
        self._joined_channels = []
        self._parted_channels = []
        self._presence_updates = []

    def add_mock_user(
        self,
        nick: str,
        name: Optional[str] = None,
        *,
        ident: str = "",
        host: str = "",
        realname: str = "",
        is_operator: bool = False,
    ) -> IRCUser:
        """Add a mock user for testing.

        Args:
            nick: The IRC nickname.
            name: Display name (defaults to nick).
            ident: The user's ident/username.
            host: The user's hostname.
            realname: The user's realname/GECOS.
            is_operator: Whether the user is an IRC operator.

        Returns:
            The created mock user.
        """
        user = IRCUser(
            id=nick,
            name=name or nick,
            handle=nick,
            nick=nick,
            ident=ident,
            host=host,
        )
        self._mock_users[nick] = user
        self.users.add(user)
        return user

    def add_mock_channel(
        self,
        name: str,
        *,
        topic: str = "",
        modes: str = "",
        user_count: int = 0,
    ) -> IRCChannel:
        """Add a mock channel for testing.

        Args:
            name: The channel name (with or without #).
            topic: The channel topic.
            modes: The channel modes.
            user_count: Number of users in channel.

        Returns:
            The created mock channel.
        """
        if not name.startswith("#"):
            name = f"#{name}"

        channel = IRCChannel(
            id=name,
            name=name,
            topic=topic,
        )
        self._mock_channels[name] = channel
        self.channels.add(channel)
        return channel

    def add_mock_message(
        self,
        channel: str,
        message_id: str,
        content: str,
        user_nick: str,
        *,
        timestamp: Optional[datetime] = None,
    ) -> IRCMessage:
        """Add a mock message for testing.

        Note: IRC normally doesn't have message IDs or history,
        but this is useful for testing purposes.

        Args:
            channel: The channel name.
            message_id: A mock message ID.
            content: The message content.
            user_nick: The sender's nickname.
            timestamp: Message timestamp (defaults to now).

        Returns:
            The created mock message.
        """
        if not channel.startswith("#"):
            channel = f"#{channel}"

        message = IRCMessage(
            id=message_id,
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc),
            user_id=user_nick,
            channel_id=channel,
        )
        if channel not in self._mock_messages:
            self._mock_messages[channel] = []
        self._mock_messages[channel].append(message)
        return message

    @property
    def sent_messages(self) -> List[IRCMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages.
        """
        return self._sent_messages

    @property
    def joined_channels(self) -> List[str]:
        """Get all channels joined through this backend.

        Returns:
            List of channel names.
        """
        return self._joined_channels

    @property
    def parted_channels(self) -> List[str]:
        """Get all channels parted through this backend.

        Returns:
            List of channel names.
        """
        return self._parted_channels

    @property
    def presence_changes(self) -> List[Dict[str, Any]]:
        """Get all presence/status changes made through this backend.

        Returns:
            List of presence changes (status, message).
        """
        return self._presence_updates

    def get_sent_messages(self) -> List[IRCMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages.
        """
        return self._sent_messages.copy()

    def get_sent_notices(self) -> List[Dict[str, str]]:
        """Get all notices sent through this backend.

        Returns:
            List of notice info (target, text).
        """
        return self._sent_notices.copy()

    def get_sent_actions(self) -> List[Dict[str, str]]:
        """Get all actions (/me) sent through this backend.

        Returns:
            List of action info (target, action).
        """
        return self._sent_actions.copy()

    def get_joined_channels(self) -> List[str]:
        """Get all channels joined through this backend.

        Returns:
            List of channel names.
        """
        return self._joined_channels.copy()

    def get_parted_channels(self) -> List[Dict[str, str]]:
        """Get all channels parted through this backend.

        Returns:
            List of part info (channel, message).
        """
        return self._parted_channels.copy()

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
        self._sent_messages.clear()
        self._sent_notices.clear()
        self._sent_actions.clear()
        self._joined_channels.clear()
        self._parted_channels.clear()
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
        """Fetch a mock user by nick or other attributes.

        Args:
            identifier: A User object or nickname string.
            id: Nickname.
            name: Display name to search for.
            email: Unused (IRC has no email lookup).
            handle: Nickname to search for (same as id).

        Returns:
            The mock user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, IRCUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # handle= is same as id= for IRC
        if not id:
            id = handle

        # Check by ID (nickname) first
        if id:
            user = self._mock_users.get(id) or self.users.get_by_id(id)
            if user:
                return user

        # Search by name
        if name:
            name_lower = name.lower()
            for user in self._mock_users.values():
                if user.name.lower() == name_lower:
                    return user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a mock channel by name.

        Args:
            identifier: A Channel object or channel name string.
            id: Channel name.
            name: Channel name (same as id).

        Returns:
            The mock channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, IRCChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # name= is same as id= for IRC
        if not id:
            id = name

        if not id:
            return None

        # Normalize channel name
        channel_name = id if id.startswith("#") else f"#{id}"
        return self._mock_channels.get(channel_name) or self.channels.get_by_id(channel_name)

    async def fetch_messages(
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
            before: Unused in IRC.
            after: Unused in IRC.

        Returns:
            List of mock messages (normally empty for real IRC).
        """
        name = channel_id if channel_id.startswith("#") else f"#{channel_id}"
        messages = self._mock_messages.get(name, [])

        # Sort by timestamp descending and limit
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
            channel_id: The channel or nick to send to.
            content: The message content.
            **kwargs: Additional options.

        Returns:
            The mock sent message.
        """
        # Generate a mock message ID
        message_id = str(len(self._sent_messages) + 1)

        message = IRCMessage(
            id=message_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            user_id=self.config.nickname or "mockbot",
            channel_id=channel_id,
        )
        self._sent_messages.append(message)
        return message

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set mock presence (AWAY status).

        Args:
            status: The status string.
            status_text: Away message.
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
            user_id: The nickname.

        Returns:
            None (IRC doesn't support presence queries).
        """
        return None

    async def join_channel(self, channel_id: str, **kwargs: Any) -> None:
        """Mock join a channel.

        Args:
            channel_id: The channel name.
            **kwargs: Additional options:
                - key: Channel password/key.
        """
        self._joined_channels.append(channel_id)

    async def leave_channel(self, channel_id: str, **kwargs: Any) -> None:
        """Mock leave a channel.

        Args:
            channel_id: The channel name.
            **kwargs: Additional options:
                - message: Part message.
        """
        self._parted_channels.append(
            {
                "channel": channel_id,
                "message": kwargs.get("message", ""),
            }
        )

    async def part_channel(self, channel: str, message: str = "") -> None:
        """Mock part a channel.

        This is an alias for leave_channel using IRC terminology.

        Args:
            channel: The channel name.
            message: Part message.
        """
        await self.leave_channel(channel, message=message)

    async def send_action(self, target: str, action: str) -> None:
        """Send a mock action (/me).

        Args:
            target: The channel or nick.
            action: The action text.
        """
        self._sent_actions.append(
            {
                "target": target,
                "action": action,
            }
        )

    async def send_notice(self, target: str, text: str) -> None:
        """Send a mock notice.

        Args:
            target: The channel or nick.
            text: The notice text.
        """
        self._sent_notices.append(
            {
                "target": target,
                "text": text,
            }
        )
