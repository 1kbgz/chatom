"""Mock Discord backend for testing.

This module provides a mock implementation of the Discord backend
for use in testing without requiring an actual Discord connection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import PrivateAttr

from ..base import Channel, Message, Presence, PresenceStatus, User
from .backend import DiscordBackend
from .channel import DiscordChannel, DiscordChannelType
from .message import DiscordMessage
from .presence import DiscordPresence
from .user import DiscordUser

__all__ = ("MockDiscordBackend",)


class MockDiscordBackend(DiscordBackend):
    """Mock Discord backend for testing.

    This class provides a mock implementation of the Discord backend
    that doesn't require an actual Discord connection. It stores all
    data in memory and provides methods to set up mock data for tests.

    Example:
        >>> backend = MockDiscordBackend()
        >>> backend.add_mock_user("123", "TestUser", "testuser")
        >>> backend.add_mock_channel("456", "general")
        >>> await backend.connect()
        >>> user = await backend.fetch_user("123")
        >>> assert user.name == "TestUser"
    """

    # Mock data stores (private attributes)
    _mock_users: Dict[str, DiscordUser] = PrivateAttr(default_factory=dict)
    _mock_channels: Dict[str, DiscordChannel] = PrivateAttr(default_factory=dict)
    _mock_messages: Dict[str, List[DiscordMessage]] = PrivateAttr(default_factory=dict)
    _mock_presence: Dict[str, DiscordPresence] = PrivateAttr(default_factory=dict)

    # Tracking stores (private attributes)
    _sent_messages: List[DiscordMessage] = PrivateAttr(default_factory=list)
    _edited_messages: List[DiscordMessage] = PrivateAttr(default_factory=list)
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
        id: str,
        name: str,
        handle: str,
        *,
        avatar_url: str = "",
        discriminator: str = "0",
        global_name: Optional[str] = None,
        is_bot: bool = False,
        is_system: bool = False,
    ) -> DiscordUser:
        """Add a mock user for testing.

        Args:
            id: The user ID.
            name: The user's display name.
            handle: The username.
            avatar_url: URL to user's avatar.
            discriminator: Legacy discriminator (e.g., "1234").
            global_name: Global display name.
            is_bot: Whether the user is a bot.
            is_system: Whether it's a Discord system user.

        Returns:
            The created mock user.
        """
        user = DiscordUser(
            id=id,
            name=name,
            handle=handle,
            avatar_url=avatar_url,
            discriminator=discriminator,
            global_name=global_name,
            is_bot=is_bot,
            is_system=is_system,
        )
        self._mock_users[id] = user
        self.users.add(user)
        return user

    def add_mock_channel(
        self,
        id: str,
        name: str,
        channel_type: str = "text",
        *,
        topic: str = "",
        guild_id: str = "",
        position: int = 0,
        nsfw: bool = False,
        discord_type: Optional[DiscordChannelType] = None,
    ) -> DiscordChannel:
        """Add a mock channel for testing.

        Args:
            id: The channel ID.
            name: The channel name.
            channel_type: The channel type ("text", "voice", "dm", etc.).
            topic: The channel topic.
            guild_id: The guild/server ID.
            position: Channel position.
            nsfw: Whether channel is NSFW.
            discord_type: The Discord channel type enum (overrides channel_type).

        Returns:
            The created mock channel.
        """
        # Map string channel type to DiscordChannelType
        if discord_type is None:
            type_map = {
                "text": DiscordChannelType.GUILD_TEXT,
                "voice": DiscordChannelType.GUILD_VOICE,
                "dm": DiscordChannelType.DM,
                "group_dm": DiscordChannelType.GROUP_DM,
                "category": DiscordChannelType.GUILD_CATEGORY,
                "news": DiscordChannelType.GUILD_ANNOUNCEMENT,
                "announcement": DiscordChannelType.GUILD_ANNOUNCEMENT,
            }
            discord_type = type_map.get(channel_type, DiscordChannelType.GUILD_TEXT)

        channel = DiscordChannel(
            id=id,
            name=name,
            topic=topic,
            guild_id=guild_id,
            position=position,
            nsfw=nsfw,
            discord_type=discord_type,
        )
        self._mock_channels[id] = channel
        self.channels.add(channel)
        return channel

    def add_mock_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        *,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        guild_id: str = "",
        edited: bool = False,
    ) -> str:
        """Add a mock message for testing.

        Args:
            channel_id: The channel containing the message.
            user_id: The author's user ID.
            content: The message content.
            message_id: Optional message ID (auto-generated if not provided).
            timestamp: Message timestamp (defaults to now).
            guild_id: The guild ID.
            edited: Whether the message was edited.

        Returns:
            The message ID.
        """
        if message_id is None:
            self._message_counter += 1
            message_id = str(self._message_counter)

        message = DiscordMessage(
            id=message_id,
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc),
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id,
            edited=edited,
        )
        if channel_id not in self._mock_messages:
            self._mock_messages[channel_id] = []
        self._mock_messages[channel_id].append(message)
        return message_id

    def set_mock_presence(
        self,
        user_id: str,
        status: PresenceStatus = PresenceStatus.ONLINE,
        *,
        activities: Optional[List[Dict[str, Any]]] = None,
        desktop_status: PresenceStatus = PresenceStatus.OFFLINE,
        mobile_status: PresenceStatus = PresenceStatus.OFFLINE,
        web_status: PresenceStatus = PresenceStatus.OFFLINE,
    ) -> DiscordPresence:
        """Set mock presence for a user.

        Args:
            user_id: The user ID.
            status: The presence status.
            activities: List of activity data.
            desktop_status: Desktop client status.
            mobile_status: Mobile client status.
            web_status: Web client status.

        Returns:
            The created mock presence.
        """
        presence = DiscordPresence(
            user_id=user_id,
            status=status,
            activities=activities or [],
            desktop_status=desktop_status,
            mobile_status=mobile_status,
            web_status=web_status,
        )
        self._mock_presence[user_id] = presence
        return presence

    @property
    def sent_messages(self) -> List[DiscordMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages.
        """
        return self._sent_messages

    @property
    def edited_messages(self) -> List[DiscordMessage]:
        """Get all messages edited through this backend.

        Returns:
            List of edited messages.
        """
        return self._edited_messages

    @property
    def deleted_messages(self) -> List[str]:
        """Get all message IDs deleted through this backend.

        Returns:
            List of deleted message IDs.
        """
        return self._deleted_messages

    def get_sent_messages(self) -> List[DiscordMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages (copy).
        """
        return self._sent_messages.copy()

    def get_edited_messages(self) -> List[DiscordMessage]:
        """Get all messages edited through this backend.

        Returns:
            List of edited messages.
        """
        return self._edited_messages.copy()

    def get_deleted_messages(self) -> List[Dict[str, str]]:
        """Get all messages deleted through this backend.

        Returns:
            List of deleted message info (channel_id, message_id).
        """
        return self._deleted_messages.copy()

    def get_reactions(self) -> List[Dict[str, str]]:
        """Get all reactions added/removed through this backend.

        Returns:
            List of reaction info (channel_id, message_id, emoji, action).
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
            id: User ID.
            name: Display name to search for.
            email: Unused (Discord has no email lookup).
            handle: Username to search for.

        Returns:
            The mock user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, DiscordUser):
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
            identifier: A Channel object or channel ID string.
            id: Channel ID.
            name: Channel name to search for.

        Returns:
            The mock channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, DiscordChannel):
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
        """Fetch mock messages from a channel.

        Args:
            channel_id: The channel to fetch from.
            limit: Maximum number of messages.
            before: Fetch messages before this ID.
            after: Fetch messages after this ID.

        Returns:
            List of mock messages.
        """
        messages = self._mock_messages.get(channel_id, [])

        # Apply before filter
        if before:
            messages = [m for m in messages if int(m.id) < int(before)]

        # Apply after filter
        if after:
            messages = [m for m in messages if int(m.id) > int(after)]

        # Sort by ID descending (newest first) and limit
        messages = sorted(messages, key=lambda m: int(m.id), reverse=True)
        return messages[:limit]

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a mock message.

        Args:
            channel_id: The channel to send to.
            content: The message content.
            **kwargs: Additional options.

        Returns:
            The mock sent message.
        """
        # Generate a mock message ID
        existing_count = len(self._sent_messages) + sum(len(msgs) for msgs in self._mock_messages.values())
        message_id = str(1000000000000000000 + existing_count)

        message = DiscordMessage(
            id=message_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            user_id="bot_user",  # Bot's user ID
            channel_id=channel_id,
            guild_id=kwargs.get("guild_id", ""),
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
            channel_id: The channel containing the message.
            message_id: The message ID.
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The mock edited message.
        """
        message = DiscordMessage(
            id=message_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            user_id="bot_user",
            channel_id=channel_id,
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
            channel_id: The channel containing the message.
            message_id: The message ID.
        """
        self._deleted_messages.append(message_id)
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
            status_text: Activity text.
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
            channel_id: The channel containing the message.
            message_id: The message ID.
            emoji: The emoji to add.
        """
        self._reactions.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
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
            channel_id: The channel containing the message.
            message_id: The message ID.
            emoji: The emoji to remove.
        """
        self._reactions.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji,
                "action": "remove",
            }
        )
