"""Mock Slack backend for testing.

This module provides a mock implementation of the Slack backend
for use in tests without requiring actual Slack API credentials.
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Union

from ..base import PresenceStatus
from .backend import SlackBackend
from .channel import SlackChannel
from .message import SlackMessage
from .presence import SlackPresence, SlackPresenceStatus
from .user import SlackUser

__all__ = ("MockSlackBackend",)


class MockSlackBackend(SlackBackend):
    """Mock Slack backend for testing.

    This backend simulates Slack API responses without making
    actual network calls. Useful for unit tests and development.

    Attributes:
        mock_users: Dictionary of mock users by ID.
        mock_channels: Dictionary of mock channels by ID.
        mock_messages: Dictionary of messages by channel_id.
        mock_presence: Dictionary of presence by user_id.
        sent_messages: List of all sent messages (for assertions).
        deleted_messages: List of deleted message IDs.
        reactions: Dictionary of reactions by (channel_id, message_id).

    Example:
        >>> backend = MockSlackBackend()
        >>> backend.add_mock_user(SlackUser(id="U123", name="alice"))
        >>> backend.add_mock_channel(SlackChannel(id="C123", name="general"))
        >>> await backend.connect()
        >>> user = await backend.fetch_user("U123")
        >>> assert user.name == "alice"
    """

    name: ClassVar[str] = "mock_slack"
    display_name: ClassVar[str] = "Mock Slack"

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._mock_users: Dict[str, SlackUser] = {}
        self._mock_channels: Dict[str, SlackChannel] = {}
        self._mock_messages: Dict[str, List[SlackMessage]] = {}
        self._mock_presence: Dict[str, SlackPresence] = {}
        self._sent_messages: List[SlackMessage] = []
        self._deleted_messages: List[tuple] = []
        self._added_reactions: List[tuple] = []
        self._removed_reactions: List[tuple] = []
        self._reactions: Dict[tuple, List[str]] = {}
        self._presence_changes: List[Dict[str, Any]] = []
        self._message_counter: int = 0
        self._current_presence: str = "auto"
        self._current_status_text: str = ""

    # =========================================================================
    # Mock data management
    # =========================================================================

    def add_mock_user(
        self,
        id: str,
        name: str,
        handle: Optional[str] = None,
        *,
        display_name: Optional[str] = None,
        avatar_url: str = "",
        is_bot: bool = False,
    ) -> SlackUser:
        """Add a mock user to the backend.

        Args:
            id: The user ID.
            name: The user's display name.
            handle: The username/handle.
            display_name: Optional display name.
            avatar_url: URL to user's avatar.
            is_bot: Whether the user is a bot.

        Returns:
            The created mock user.
        """
        user = SlackUser(
            id=id,
            name=name,
            handle=handle or name.lower().replace(" ", ""),
            display_name=display_name or name,
            avatar_url=avatar_url,
            is_bot=is_bot,
        )
        self._mock_users[user.id] = user
        self.users.add(user)
        return user

    def add_mock_channel(
        self,
        id: str,
        name: str,
        *,
        topic: str = "",
        is_private: bool = False,
        is_archived: bool = False,
    ) -> SlackChannel:
        """Add a mock channel to the backend.

        Args:
            id: The channel ID.
            name: The channel name.
            topic: The channel topic.
            is_private: Whether the channel is private.
            is_archived: Whether the channel is archived.

        Returns:
            The created mock channel.
        """
        channel = SlackChannel(
            id=id,
            name=name,
            topic=topic,
            is_private=is_private,
            is_archived=is_archived,
        )
        self._mock_channels[channel.id] = channel
        self.channels.add(channel)
        if channel.id not in self._mock_messages:
            self._mock_messages[channel.id] = []
        return channel

    def add_mock_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        *,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """Add a mock message to a channel.

        Args:
            channel_id: The channel ID.
            user_id: The sender's user ID.
            content: The message content.
            message_id: Optional message ID (auto-generated if not provided).
            timestamp: Optional timestamp.

        Returns:
            The message ID.
        """
        if message_id is None:
            self._message_counter += 1
            message_id = f"msg_{self._message_counter}"

        message = SlackMessage(
            id=message_id,
            content=content,
            channel_id=channel_id,
            author_id=user_id,
            sender_id=user_id,
            timestamp=timestamp or datetime.now(),
            ts=message_id,
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
        status_text: str = "",
    ) -> SlackPresence:
        """Set mock presence for a user.

        Args:
            user_id: The user ID.
            status: The presence status.
            status_text: Optional status text.

        Returns:
            The created presence.
        """
        # Map base status to Slack status
        slack_status = SlackPresenceStatus.from_base(status)
        presence = SlackPresence(
            user_id=user_id,
            status=slack_status,
            status_text=status_text,
        )
        self._mock_presence[user_id] = presence
        self._presence_changes.append({"status": status, "status_text": status_text})
        return presence

    @property
    def sent_messages(self) -> List[SlackMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages.
        """
        return self._sent_messages

    @property
    def added_reactions(self) -> List[tuple]:
        """Get all reactions added through this backend.

        Returns:
            List of (channel_id, message_id, emoji) tuples.
        """
        return self._added_reactions

    @property
    def removed_reactions(self) -> List[tuple]:
        """Get all reactions removed through this backend.

        Returns:
            List of (channel_id, message_id, emoji) tuples.
        """
        return self._removed_reactions

    @property
    def presence_changes(self) -> List[Dict[str, Any]]:
        """Get all presence changes made through this backend.

        Returns:
            List of presence changes.
        """
        return self._presence_changes

    @property
    def mock_users(self) -> Dict[str, SlackUser]:
        """Get all mock users.

        Returns:
            Dictionary of mock users by ID.
        """
        return self._mock_users

    def reset(self) -> None:
        """Reset all mock data and tracking stores."""
        self._mock_users.clear()
        self._mock_channels.clear()
        self._mock_messages.clear()
        self._mock_presence.clear()
        self._sent_messages.clear()
        self._deleted_messages.clear()
        self._added_reactions.clear()
        self._removed_reactions.clear()
        self._reactions.clear()
        self._presence_changes.clear()
        self._message_counter = 0
        self.users.clear()
        self.channels.clear()

    def get_sent_messages(self) -> List[SlackMessage]:
        """Get all messages sent through this backend.

        Returns:
            List of sent messages (copy).
        """
        return self._sent_messages.copy()

    def get_deleted_messages(self) -> List[tuple]:
        """Get all deleted message references.

        Returns:
            List of (channel_id, message_id) tuples.
        """
        return self._deleted_messages.copy()

    def get_reactions(self, channel_id: str, message_id: str) -> List[str]:
        """Get reactions for a message.

        Args:
            channel_id: The channel ID.
            message_id: The message ID.

        Returns:
            List of emoji names.
        """
        return self._reactions.get((channel_id, message_id), [])

    def clear(self) -> None:
        """Clear all mock data."""
        self._mock_users.clear()
        self._mock_channels.clear()
        self._mock_messages.clear()
        self._mock_presence.clear()
        self._sent_messages.clear()
        self._deleted_messages.clear()
        self._reactions.clear()
        self.users = type(self.users)()
        self.channels = type(self.channels)()

    # =========================================================================
    # Backend method implementations
    # =========================================================================

    async def connect(self) -> None:
        """Connect to the mock backend."""
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from the mock backend."""
        self.connected = False

    async def fetch_user(
        self,
        identifier: Optional[Union[str, SlackUser]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[SlackUser]:
        """Fetch a mock user by ID or other attributes.

        Args:
            identifier: A SlackUser object or user ID string.
            id: User ID.
            name: Display name to search for.
            email: Email address to search for.
            handle: Username/handle to search for.

        Returns:
            The user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, SlackUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check by ID first
        if id:
            user = self._mock_users.get(id)
            if user:
                return user

        # Search by email
        if email:
            for user in self._mock_users.values():
                if hasattr(user, "email") and user.email == email:
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
        identifier: Optional[Union[str, SlackChannel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[SlackChannel]:
        """Fetch a mock channel by ID or name.

        Args:
            identifier: A SlackChannel object or channel ID string.
            id: Channel ID.
            name: Channel name to search for.

        Returns:
            The channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, SlackChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check by ID first
        if id:
            channel = self._mock_channels.get(id)
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
    ) -> List[SlackMessage]:
        """Fetch mock messages from a channel.

        Args:
            channel_id: The channel to fetch from.
            limit: Maximum number of messages.
            before: Fetch messages before this timestamp.
            after: Fetch messages after this timestamp.

        Returns:
            List of messages.
        """
        messages = self._mock_messages.get(channel_id, [])

        # Filter by before/after
        if after:
            messages = [m for m in messages if m.ts > after]
        if before:
            messages = [m for m in messages if m.ts < before]

        # Sort by timestamp and limit
        messages = sorted(messages, key=lambda m: m.ts)
        return messages[:limit]

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> SlackMessage:
        """Send a mock message.

        Args:
            channel_id: The channel to send to.
            content: The message content.
            **kwargs: Additional options.

        Returns:
            The sent message.
        """
        self._message_counter += 1
        ts = f"{datetime.now().timestamp():.6f}"

        message = SlackMessage(
            id=ts,
            ts=ts,
            content=content,
            channel=channel_id,
            channel_id=channel_id,
            created_at=datetime.now(),
            thread_ts=kwargs.get("thread_ts"),
        )

        self._sent_messages.append(message)

        if channel_id not in self._mock_messages:
            self._mock_messages[channel_id] = []
        self._mock_messages[channel_id].append(message)

        return message

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> SlackMessage:
        """Edit a mock message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp.
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        messages = self._mock_messages.get(channel_id, [])
        for i, msg in enumerate(messages):
            if msg.ts == message_id:
                edited = SlackMessage(
                    id=msg.id,
                    ts=msg.ts,
                    content=content,
                    channel=channel_id,
                    created_at=msg.created_at,
                    is_edited=True,
                )
                self._mock_messages[channel_id][i] = edited
                return edited

        raise RuntimeError(f"Message {message_id} not found in channel {channel_id}")

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a mock message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp.
        """
        self._deleted_messages.append((channel_id, message_id))

        messages = self._mock_messages.get(channel_id, [])
        self._mock_messages[channel_id] = [m for m in messages if m.ts != message_id]

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set mock presence.

        Args:
            status: Presence status ('auto' or 'away').
            status_text: Status text.
            **kwargs: Additional options.
        """
        self._current_presence = status
        if status_text is not None:
            self._current_status_text = status_text
        self._presence_changes.append({"status": status, "status_text": status_text})

    async def get_presence(self, user_id: str) -> Optional[SlackPresence]:
        """Get mock presence for a user.

        Args:
            user_id: The user ID.

        Returns:
            The user's presence.
        """
        if user_id in self._mock_presence:
            return self._mock_presence[user_id]

        # Return default presence
        return SlackPresence(
            status=PresenceStatus.ONLINE,
            slack_presence=SlackPresenceStatus.ACTIVE,
        )

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a mock reaction.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp.
            emoji: The emoji name.
        """
        key = (channel_id, message_id)
        if key not in self._reactions:
            self._reactions[key] = []

        emoji = emoji.strip(":")
        if emoji not in self._reactions[key]:
            self._reactions[key].append(emoji)
        self._added_reactions.append((channel_id, message_id, emoji))

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a mock reaction.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp.
            emoji: The emoji name.
        """
        key = (channel_id, message_id)
        emoji = emoji.strip(":")
        if key in self._reactions and emoji in self._reactions[key]:
            self._reactions[key].remove(emoji)
        self._removed_reactions.append((channel_id, message_id, emoji))
