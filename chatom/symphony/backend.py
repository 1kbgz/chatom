"""Symphony backend implementation for chatom.

This module provides the Symphony backend using the Symphony BDK
(Bot Development Kit).
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend import BackendBase
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

# Try to import symphony-bdk
try:
    from symphony.bdk.core.config.model.bdk_config import BdkConfig
    from symphony.bdk.core.service.presence.presence_service import PresenceStatus
    from symphony.bdk.core.symphony_bdk import SymphonyBdk

    HAS_SYMPHONY = True
except ImportError:
    HAS_SYMPHONY = False
    SymphonyBdk = None  # type: ignore
    BdkConfig = None  # type: ignore
    PresenceStatus = None  # type: ignore

__all__ = ("SymphonyBackend",)


# Map presence statuses
PRESENCE_MAP = {
    "available": "AVAILABLE",
    "online": "AVAILABLE",
    "busy": "BUSY",
    "dnd": "BUSY",
    "away": "AWAY",
    "idle": "AWAY",
    "on_the_phone": "ON_THE_PHONE",
    "brb": "BE_RIGHT_BACK",
    "be_right_back": "BE_RIGHT_BACK",
    "in_a_meeting": "IN_A_MEETING",
    "meeting": "IN_A_MEETING",
    "out_of_office": "OUT_OF_OFFICE",
    "ooo": "OUT_OF_OFFICE",
    "off_work": "OFF_WORK",
    "offline": "OFF_WORK",
}


class SymphonyBackend(BackendBase):
    """Symphony backend implementation using Symphony BDK.

    This provides the backend interface for Symphony using the official
    Symphony Bot Development Kit (BDK).

    Attributes:
        name: The backend identifier ('symphony').
        display_name: Human-readable name.
        format: Symphony uses MessageML format.
        capabilities: Symphony-specific capabilities.
        config: Symphony-specific configuration.

    Example:
        >>> from chatom.symphony import SymphonyBackend, SymphonyConfig
        >>> config = SymphonyConfig(
        ...     host="mycompany.symphony.com",
        ...     bot_username="my-bot",
        ...     bot_private_key_path="/path/to/private-key.pem",
        ... )
        >>> backend = SymphonyBackend(config=config)
        >>> await backend.connect()
    """

    name: ClassVar[str] = "symphony"
    display_name: ClassVar[str] = "Symphony"
    format: ClassVar[Format] = Format.SYMPHONY_MESSAGEML

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = SymphonyUser
    channel_class: ClassVar[type] = SymphonyChannel
    presence_class: ClassVar[type] = SymphonyPresence

    capabilities: Optional[BackendCapabilities] = SYMPHONY_CAPABILITIES
    config: SymphonyConfig = Field(default_factory=SymphonyConfig)

    # SDK instance
    _bdk: Any = None
    _bot_user_id_int: Optional[int] = None
    _bot_user_name_cached: Optional[str] = None

    @property
    def bot_user_id(self) -> Optional[str]:
        """Get the bot's user ID as a string (cached from connect)."""
        return str(self._bot_user_id_int) if self._bot_user_id_int else None

    @property
    def bot_user_name(self) -> Optional[str]:
        """Get the bot's username (from config or cached from connect)."""
        return self._bot_user_name_cached or self.config.bot_username

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    async def connect(self) -> None:
        """Connect to Symphony using the BDK.

        This initializes the Symphony BDK and authenticates the bot.

        Raises:
            RuntimeError: If symphony-bdk is not installed or connection fails.
        """
        if not HAS_SYMPHONY:
            raise RuntimeError("symphony-bdk is not installed. Install with: pip install symphony-bdk-python")

        if not self.config.host or not self.config.bot_username:
            raise RuntimeError("Symphony host and bot_username are required")

        if not self.config.has_rsa_auth and not self.config.has_cert_auth:
            raise RuntimeError("Either RSA private key or certificate must be configured")

        try:
            # Create BDK configuration
            bdk_config = BdkConfig(**self.config.to_bdk_config())

            # Initialize BDK
            self._bdk = SymphonyBdk(bdk_config)

            # Get bot session info
            session_service = self._bdk.sessions()
            session = await session_service.get_session()
            self._bot_user_id_int = session.id
            self._bot_user_name_cached = getattr(session, "username", None) or self.config.bot_username

            self.connected = True

        except Exception as e:
            raise RuntimeError(f"Failed to connect to Symphony: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Symphony."""
        if self._bdk is not None:
            try:
                await self._bdk.close_clients()
            except Exception:
                pass
            self._bdk = None

        self._bot_user_id_int = None
        self._bot_user_name_cached = None
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
        """Fetch a user from Symphony.

        Accepts flexible inputs:
        - User ID as positional arg or id=
        - User object (returns as-is or refreshes)
        - name= to search by display name
        - email= to search by email address
        - handle= to search by username

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
        if isinstance(identifier, (SymphonyUser, User)):
            if isinstance(identifier, SymphonyUser):
                return identifier
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first for ID lookup
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

        if self._bdk is None:
            return None

        # If we have an ID, fetch directly
        if id:
            return await self._fetch_user_by_id(id)

        # Try to look up by email
        if email:
            try:
                user_service = self._bdk.users()
                results = await user_service.list_users_by_emails([email])
                if results:
                    # Results is a dict with 'users' key
                    users_list = results.get("users", []) if isinstance(results, dict) else getattr(results, "users", [])
                    if users_list and len(users_list) > 0:
                        user_data = users_list[0]
                        # Build SymphonyUser directly from this data instead of fetching again
                        result = self._build_user_from_data(user_data)
                        if result:
                            return result
            except Exception:
                pass

        # Try to look up by username (handle)
        if handle:
            try:
                user_service = self._bdk.users()
                results = await user_service.list_users_by_usernames([handle])
                if results:
                    # Results is a dict with 'users' key
                    users_list = results.get("users", []) if isinstance(results, dict) else getattr(results, "users", [])
                    if users_list and len(users_list) > 0:
                        user_data = users_list[0]
                        # Build SymphonyUser directly from this data instead of fetching again
                        result = self._build_user_from_data(user_data)
                        if result:
                            return result
            except Exception:
                pass

        # Search by display name
        if name:
            try:
                from symphony.bdk.gen.pod_model.user_search_query import UserSearchQuery

                user_service = self._bdk.users()
                query = UserSearchQuery(query=name)
                results = await user_service.search_users(query=query, local=True)
                if results and hasattr(results, "users") and results.users:
                    # Find best match
                    for user_data in results.users:
                        display = getattr(user_data, "display_name", None) or getattr(user_data, "displayName", "")
                        if display.lower() == name.lower():
                            return await self._fetch_user_by_id(str(user_data.id))
                    # If no exact match, return first result
                    if results.users:
                        return await self._fetch_user_by_id(str(results.users[0].id))
            except Exception:
                pass

        return None

    def _build_user_from_data(self, user_data: Union[dict, Any]) -> Optional[SymphonyUser]:
        """Build a SymphonyUser from API response data (dict or object)."""
        try:
            if isinstance(user_data, dict):
                uid = user_data.get("id")
                display_name = user_data.get("display_name") or user_data.get("displayName")
                username = user_data.get("username")
                email = user_data.get("email_address") or user_data.get("emailAddress")
            else:
                uid = getattr(user_data, "id", None)
                display_name = getattr(user_data, "display_name", None) or getattr(user_data, "displayName", None)
                username = getattr(user_data, "username", None)
                email = getattr(user_data, "email_address", None) or getattr(user_data, "emailAddress", None)

            if not uid:
                return None

            # If email is not set but username looks like an email, use it
            if not email and username and "@" in username:
                email = username

            user = SymphonyUser(
                id=str(uid),
                name=display_name or username or "",
                handle=username or "",
                email=email or "",
                user_id=uid,
            )
            self.users.add(user)
            return user
        except Exception:
            return None

    async def _fetch_user_by_id(self, user_id: str) -> Optional[SymphonyUser]:
        """Fetch a user by ID from the Symphony API."""
        try:
            user_service = self._bdk.users()
            user_data = await user_service.get_user_detail(int(user_id))

            # Handle both dict and object responses
            if isinstance(user_data, dict):
                uid = user_data.get("id")
                display_name = user_data.get("display_name") or user_data.get("displayName")
                username = user_data.get("username")
                email = user_data.get("email_address") or user_data.get("emailAddress") or user_data.get("email")
            else:
                uid = user_data.id
                display_name = getattr(user_data, "display_name", None) or getattr(user_data, "displayName", None)
                username = user_data.username
                # Try multiple email field names
                email = getattr(user_data, "email_address", None) or getattr(user_data, "emailAddress", None) or getattr(user_data, "email", None)
                # V2UserDetail has email in user_attributes.email_address
                if not email and hasattr(user_data, "user_attributes"):
                    attrs = user_data.user_attributes
                    if attrs:
                        email = getattr(attrs, "email_address", None) or getattr(attrs, "emailAddress", None)

            # If email is not set but username looks like an email, use it
            if not email and username and "@" in username:
                email = username

            user = SymphonyUser(
                id=str(uid),
                name=display_name or username,
                handle=username,
                email=email or "",
                user_id=uid,
            )
            self.users.add(user)
            return user
        except Exception:
            return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel (stream/room) from Symphony.

        Accepts flexible inputs:
        - Stream ID as positional arg or id=
        - Channel object (returns as-is or refreshes)
        - name= to search by room name

        Args:
            identifier: A Channel object or stream ID string.
            id: Stream ID.
            name: Room name to search for.

        Returns:
            The channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, (SymphonyChannel, Channel)):
            if isinstance(identifier, SymphonyChannel):
                return identifier
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first for ID lookup
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached

        if self._bdk is None:
            return None

        # If we have an ID, fetch directly
        if id:
            return await self._fetch_channel_by_id(id)

        # Search by room name
        if name:
            try:
                from symphony.bdk.gen.pod_model.v2_room_search_criteria import V2RoomSearchCriteria

                stream_service = self._bdk.streams()
                results = await stream_service.search_rooms(V2RoomSearchCriteria(query=name), limit=10)
                if results and results.rooms:
                    # Find exact match first
                    for room in results.rooms:
                        room_attrs = room.room_attributes
                        room_info = room.room_system_info
                        if room_attrs and room_info and room_attrs.name == name:
                            return await self._fetch_channel_by_id(room_info.id)
                    # If no exact match, use first result
                    if results.rooms:
                        room = results.rooms[0]
                        if room.room_system_info:
                            return await self._fetch_channel_by_id(room.room_system_info.id)
            except Exception:
                pass

        return None

    async def _fetch_channel_by_id(self, stream_id: str) -> Optional[SymphonyChannel]:
        """Fetch a channel by stream ID from the Symphony API."""
        try:
            stream_service = self._bdk.streams()
            stream_info = await stream_service.get_stream(stream_id)

            channel = SymphonyChannel(
                id=stream_id,
                name=getattr(stream_info, "name", None) or stream_id,
                stream_id=stream_id,
            )
            self.channels.add(channel)
            return channel
        except Exception:
            return None

    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[Union[str, Message]] = None,
        after: Optional[Union[str, Message]] = None,
    ) -> List[Message]:
        """Fetch messages from a Symphony stream.

        Args:
            channel: The stream to fetch messages from (ID string or Channel object).
            limit: Maximum number of messages.
            before: Fetch messages before this message (ID string or Message object).
            after: Fetch messages after this message (ID string or Message object).

        Returns:
            List of messages.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        # Resolve channel ID
        channel_id = await self._resolve_channel_id(channel)

        # Resolve after message ID
        after_id = None
        if after:
            if isinstance(after, Message):
                after_id = after.id
            else:
                after_id = after

        try:
            message_service = self._bdk.messages()

            # Build parameters
            kwargs: dict = {"stream_id": channel_id, "limit": limit}

            # Symphony uses timestamps for pagination
            if after_id:
                # Try to parse as timestamp
                kwargs["since"] = int(after_id)

            messages_data = await message_service.list_messages(**kwargs)

            messages: List[Message] = []
            for msg in messages_data:
                message = SymphonyMessage(
                    id=msg.message_id,
                    content=msg.message,  # MessageML content
                    timestamp=datetime.fromtimestamp(msg.timestamp / 1000, tz=timezone.utc),
                    user_id=str(msg.user.user_id) if msg.user else None,
                    channel_id=channel_id,
                )
                messages.append(message)

            return messages

        except Exception as e:
            raise RuntimeError(f"Failed to fetch messages: {e}") from e

    async def search_messages(
        self,
        query: str,
        channel: Optional[Union[str, Channel]] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Message]:
        """Search for messages matching a query.

        Uses Symphony's message search API.

        Args:
            query: The search query string.
            channel: Optional stream to limit search to (ID string or Channel object).
            limit: Maximum number of results.
            **kwargs: Additional options:
                      - from_user: Filter by sender user ID
                      - hashtags: List of hashtags to filter by
                      - cashtags: List of cashtags to filter by

        Returns:
            List of messages matching the query.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        try:
            message_service = self._bdk.messages()

            # Build search parameters
            search_params: dict = {
                "query": query,
                "limit": limit,
            }

            # Add stream filter if provided
            if channel:
                channel_id = await self._resolve_channel_id(channel)
                search_params["stream_id"] = channel_id

            # Add optional filters
            if "from_user" in kwargs:
                search_params["from_user_id"] = kwargs["from_user"]
            if "hashtags" in kwargs:
                search_params["hashtags"] = kwargs["hashtags"]
            if "cashtags" in kwargs:
                search_params["cashtags"] = kwargs["cashtags"]

            # Use Symphony search API
            messages_data = await message_service.search_messages(**search_params)

            messages: List[Message] = []
            for msg in messages_data:
                stream_id = getattr(msg, "stream_id", "") or ""
                message = SymphonyMessage(
                    id=msg.message_id,
                    content=msg.message,
                    timestamp=datetime.fromtimestamp(msg.timestamp / 1000, tz=timezone.utc),
                    user_id=str(msg.user.user_id) if msg.user else None,
                    channel_id=stream_id,
                )
                messages.append(message)

            return messages

        except Exception as e:
            raise RuntimeError(f"Failed to search messages: {e}") from e

    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to a Symphony stream.

        Args:
            channel: The stream to send to (ID string or Channel object).
            content: The message content (MessageML).
            **kwargs: Additional options:
                - data: Template data as dict.
                - attachments: List of attachment file paths.

        Returns:
            The sent message.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        # Resolve channel ID
        channel_id = await self._resolve_channel_id(channel)

        try:
            message_service = self._bdk.messages()

            # Ensure content is wrapped in messageML tags
            if not content.strip().startswith("<messageML>"):
                content = f"<messageML>{content}</messageML>"

            # Build message params
            data = kwargs.get("data")
            attachments = kwargs.get("attachments")

            result = await message_service.send_message(
                stream_id=channel_id,
                message=content,
                data=data,
                attachment=attachments,
            )

            return SymphonyMessage(
                id=result.message_id,
                content=content,
                timestamp=datetime.fromtimestamp(result.timestamp / 1000, tz=timezone.utc),
                user_id=str(self._bot_user_id_int) if self._bot_user_id_int else None,
                channel_id=channel_id,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to send message: {e}") from e

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> Message:
        """Edit a Symphony message.

        Note: Symphony has limited support for message editing via the
        update_message API.

        Args:
            message: The message to edit (ID string or Message object).
            content: The new content (MessageML).
            channel: The stream containing the message (required if message is a string).
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        # Resolve message and channel IDs
        message_id, channel_id = await self._resolve_message_id(message, channel)

        try:
            message_service = self._bdk.messages()

            # Ensure content is wrapped in messageML tags
            if not content.strip().startswith("<messageML>"):
                content = f"<messageML>{content}</messageML>"

            result = await message_service.update_message(
                stream_id=channel_id,
                message_id=message_id,
                message=content,
                data=kwargs.get("data"),
            )

            return SymphonyMessage(
                id=result.message_id,
                content=content,
                timestamp=datetime.now(timezone.utc),
                user_id=str(self._bot_user_id_int) if self._bot_user_id_int else None,
                channel_id=channel_id,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to edit message: {e}") from e

    async def delete_message(
        self,
        message: Union[str, Message],
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Delete (suppress) a Symphony message.

        Args:
            message: The message to delete (ID string or Message object).
            channel: The stream containing the message (not used for Symphony).
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        # Resolve message ID (channel not needed for Symphony suppress)
        if isinstance(message, Message):
            message_id = message.id
        else:
            message_id = message

        try:
            message_service = self._bdk.messages()
            await message_service.suppress_message(message_id)

        except Exception as e:
            raise RuntimeError(f"Failed to delete message: {e}") from e

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set user presence on Symphony.

        Args:
            status: Presence status (available, busy, away, etc.).
            status_text: Not supported by Symphony.
            **kwargs: Additional options:
                - soft: If True, respect current activity state.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        if not HAS_SYMPHONY:
            raise RuntimeError("symphony-bdk is not installed")

        try:
            presence_service = self._bdk.presence()

            # Map status to Symphony presence
            mapped_status = PRESENCE_MAP.get(status.lower(), "AVAILABLE")

            # Get PresenceStatus enum value
            presence_status = getattr(PresenceStatus, mapped_status, PresenceStatus.AVAILABLE)

            soft = kwargs.get("soft", True)

            await presence_service.set_presence(presence_status, soft=soft)

        except Exception as e:
            raise RuntimeError(f"Failed to set presence: {e}") from e

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get a user's presence on Symphony.

        Args:
            user_id: The user ID.

        Returns:
            The user's presence.
        """
        if self._bdk is None:
            return None

        try:
            presence_service = self._bdk.presence()
            presence_data = await presence_service.get_user_presence(int(user_id), local=False)

            # Map Symphony presence to our enum
            status_map = {
                "AVAILABLE": SymphonyPresenceStatus.AVAILABLE,
                "BUSY": SymphonyPresenceStatus.BUSY,
                "AWAY": SymphonyPresenceStatus.AWAY,
                "ON_THE_PHONE": SymphonyPresenceStatus.ON_THE_PHONE,
                "BE_RIGHT_BACK": SymphonyPresenceStatus.BE_RIGHT_BACK,
                "IN_A_MEETING": SymphonyPresenceStatus.IN_A_MEETING,
                "OUT_OF_OFFICE": SymphonyPresenceStatus.OUT_OF_OFFICE,
                "OFF_WORK": SymphonyPresenceStatus.OFF_WORK,
                "OFFLINE": SymphonyPresenceStatus.OFFLINE,
            }

            status = status_map.get(presence_data.category, SymphonyPresenceStatus.OFFLINE)

            return SymphonyPresence(
                user_id=user_id,
                status=status,
            )

        except Exception:
            return None

    async def add_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Add a reaction to a message.

        Note: Symphony doesn't support reactions in the same way.
        This raises NotImplementedError.

        Args:
            message: The message to react to (ID string or Message object).
            emoji: The emoji.
            channel: The stream containing the message (not used).

        Raises:
            NotImplementedError: Symphony doesn't support emoji reactions.
        """
        raise NotImplementedError("Symphony does not support emoji reactions. Consider using signals or inline forms instead.")

    async def remove_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Remove a reaction from a message.

        Note: Symphony doesn't support reactions.

        Args:
            message: The message to remove reaction from (ID string or Message object).
            emoji: The emoji to remove.
            channel: The stream containing the message (not used).

        Raises:
            NotImplementedError: Symphony doesn't support emoji reactions.
        """
        raise NotImplementedError("Symphony does not support emoji reactions")

    def mention_user(self, user: User) -> str:
        """Format a user mention for Symphony.

        Args:
            user: The user to mention.

        Returns:
            Symphony user mention format (<mention uid="..."/>).
        """
        if isinstance(user, SymphonyUser):
            return _mention_user(user)
        # For base User, use ID as user_id
        return f'<mention uid="{user.id}"/>'

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for Symphony.

        Symphony doesn't have channel mentions in the same way.
        Returns the channel name.

        Args:
            channel: The channel to mention.

        Returns:
            The channel name.
        """
        if isinstance(channel, SymphonyChannel):
            return channel.name or channel.stream_id or channel.id
        return channel.name or channel.id

    def mention_here(self) -> str:
        """Format an @here mention for Symphony.

        Symphony doesn't have an @here equivalent.
        Returns an empty string (no-op).

        Returns:
            Empty string (Symphony doesn't support @here).
        """
        return ""

    def mention_everyone(self) -> str:
        """Format an @everyone mention for Symphony.

        Uses Symphony's mention all users tag.

        Returns:
            Symphony MessageML mention all tag.
        """
        return '<mention uid="all"/>'

    def mention_channel_all(self) -> str:
        """Format an @channel mention for Symphony.

        Symphony uses the same tag for all broadcast mentions.

        Returns:
            Symphony MessageML mention all tag.
        """
        return '<mention uid="all"/>'

    # Additional Symphony-specific methods

    async def create_dm(self, users: List[Union[str, User]]) -> Optional[str]:
        """Create a direct message (IM) or multi-party IM.

        Args:
            users: List of users to include in the DM (ID strings or User objects).
                   If one user, creates a 1:1 IM.
                   If multiple users, uses admin endpoint for MIM.

        Returns:
            The stream ID of the created DM.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        try:
            stream_service = self._bdk.streams()

            # Resolve user IDs
            user_ids: List[str] = []
            for user in users:
                if isinstance(user, User):
                    if user.is_incomplete:
                        resolved = await self.resolve_user(user)
                        user_ids.append(resolved.id)
                    else:
                        user_ids.append(user.id)
                else:
                    user_ids.append(user)

            # Convert string IDs to int for Symphony API
            int_user_ids = [int(uid) for uid in user_ids]

            if len(int_user_ids) == 1:
                # Single user - use create_im which takes a single user_id
                stream = await stream_service.create_im(int_user_ids[0])
            else:
                # Multiple users - use admin endpoint for MIM
                stream = await stream_service.create_im_admin(int_user_ids)

            return stream.id

        except Exception as e:
            raise RuntimeError(f"Failed to create DM: {e}") from e

    async def create_im(self, users: List[Union[str, User]]) -> Optional[str]:
        """Create an instant message (IM) or multi-party IM.

        This is an alias for create_dm, using Symphony's terminology.

        Args:
            users: List of users to include in the IM (ID strings or User objects).

        Returns:
            The stream ID of the created IM.
        """
        return await self.create_dm(users)

    async def create_channel(
        self,
        name: str,
        description: str = "",
        public: bool = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a room (chat room).

        Args:
            name: The room name.
            description: The room description.
            public: Whether the room is public.
            **kwargs: Additional options:
                - read_only: Whether the room is read-only.

        Returns:
            The stream ID of the created room.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        try:
            from symphony.bdk.gen.pod_model.v3_room_attributes import V3RoomAttributes

            stream_service = self._bdk.streams()
            read_only = kwargs.get("read_only", False)

            # Create V3RoomAttributes with proper fields
            room_attrs = V3RoomAttributes(
                name=name,
                description=description,
                public=public,
                read_only=read_only,
            )

            room = await stream_service.create_room(room_attrs)

            return room.room_system_info.id

        except Exception as e:
            raise RuntimeError(f"Failed to create room: {e}") from e

    async def create_room(
        self,
        name: str,
        description: str = "",
        public: bool = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a room (chat room).

        This is an alias for create_channel, using Symphony's terminology.

        Args:
            name: The room name.
            description: The room description.
            public: Whether the room is public.
            **kwargs: Additional options:
                - read_only: Whether the room is read-only.

        Returns:
            The stream ID of the created room.
        """
        return await self.create_channel(name, description, public, **kwargs)

    async def get_bot_info(self) -> Optional[User]:
        """Get information about the connected bot user.

        Returns:
            The bot's User object.
        """
        if self._bdk is None:
            return None

        try:
            session = await self._bdk.sessions().get_session()
            return SymphonyUser(
                id=str(session.id),
                name=session.display_name or session.username or str(session.id),
                handle=session.username or str(session.id),
                email=getattr(session, "email_address", None) or "",
                user_id=session.id,
            )
        except Exception:
            return None

    async def stream_messages(
        self,
        channel: Optional[Union[str, Channel]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> "AsyncIterator[Message]":
        """Stream incoming messages in real-time using Symphony datafeed.

        This async generator yields Message objects as they arrive.

        Args:
            channel: Optional stream to filter messages (ID string or Channel object).
            skip_own: If True (default), skip messages sent by the bot itself.
            skip_history: If True (default), skip messages that existed before
                         the stream started. Only yields new messages.

        Yields:
            Message: Each message as it arrives.
        """
        if self._bdk is None:
            raise RuntimeError("Symphony not connected")

        # Resolve channel ID if provided
        channel_id: Optional[str] = None
        if channel is not None:
            channel_id = await self._resolve_channel_id(channel)

        try:
            from symphony.bdk.core.service.datafeed.real_time_event_listener import (
                RealTimeEventListener,
            )
            from symphony.bdk.gen.agent_model.v4_initiator import V4Initiator
            from symphony.bdk.gen.agent_model.v4_message_sent import V4MessageSent
        except ImportError as e:
            raise RuntimeError(f"symphony-bdk-python required for streaming: {e}") from e

        # Get bot info for filtering
        bot_info = await self.get_bot_info()
        bot_user_id = str(bot_info.id) if bot_info else None

        # Track when the stream started for skip_history
        stream_start_time = datetime.now(tz=timezone.utc)

        # Create a queue for messages
        message_queue: "asyncio.Queue[Message]" = asyncio.Queue()
        stop_event = asyncio.Event()

        class MessageCollector(RealTimeEventListener):
            """Internal listener that puts messages into the queue."""

            def __init__(
                self,
                queue: "asyncio.Queue[Message]",
                filter_channel: Optional[str],
                bot_id: Optional[str],
                backend: "SymphonyBackend",
                start_time: datetime,
                do_skip_own: bool,
                do_skip_history: bool,
            ):
                self._queue = queue
                self._filter_channel = filter_channel
                self._bot_id = bot_id
                self._backend = backend
                self._start_time = start_time
                self._skip_own = do_skip_own
                self._skip_history = do_skip_history

            async def on_message_sent(self, initiator: V4Initiator, event: V4MessageSent):
                msg = event.message
                if not msg or not msg.stream:
                    return

                stream_id = msg.stream.stream_id
                sender_id = str(initiator.user.user_id) if initiator.user else None

                # Skip bot's own messages
                if self._skip_own and sender_id == self._bot_id:
                    return

                # Filter by channel if specified
                if self._filter_channel and stream_id != self._filter_channel:
                    return

                # Extract mentions from data field and convert to User objects
                mention_ids_int = SymphonyMessage.extract_mentions_from_data(msg.data)
                # Convert integer IDs to SymphonyUser objects for the mentions field
                mention_users = [SymphonyUser(id=str(uid)) for uid in mention_ids_int]

                # Parse message timestamp
                msg_timestamp = datetime.fromtimestamp(int(msg.timestamp) / 1000, tz=timezone.utc) if msg.timestamp else datetime.now(tz=timezone.utc)

                # Skip messages from before the stream started
                if self._skip_history and msg_timestamp < self._start_time:
                    return

                # Determine stream type from the stream object
                stream_type_str = getattr(msg.stream, "stream_type", None) or "ROOM"
                try:
                    from .channel import SymphonyChannel, SymphonyStreamType

                    stream_type = SymphonyStreamType(stream_type_str)
                except (ValueError, ImportError):
                    stream_type = None

                # Lookup channel to get full info (id AND name)
                channel = await self._backend._fetch_channel_by_id(stream_id)
                if channel is None and stream_type is not None:
                    # Create channel with at least the stream_type
                    channel = SymphonyChannel(
                        id=stream_id,
                        name="",  # Name not available in event
                        stream_type=stream_type,
                    )
                elif channel is not None and stream_type is not None:
                    # Update stream_type if we have it
                    channel = SymphonyChannel(
                        id=channel.id,
                        name=channel.name,
                        stream_type=stream_type,
                        stream_id=stream_id,
                    )

                # Lookup author to get full info (id AND name)
                author = None
                if sender_id:
                    author = await self._backend._fetch_user_by_id(sender_id)

                # Convert to SymphonyMessage
                symphony_msg = SymphonyMessage(
                    id=msg.message_id,
                    content=msg.message or "",
                    presentation_ml=msg.message or "",
                    author=author,  # Use looked-up author with full info
                    channel=channel,
                    timestamp=msg_timestamp,
                    data=msg.data,
                    mentions=mention_users,  # List of SymphonyUser objects
                )

                # If we didn't find the author via lookup, use info from initiator
                if author is None and initiator.user:
                    username = getattr(initiator.user, "username", "") or str(initiator.user.user_id)
                    # If username looks like an email, use it as email
                    email = username if "@" in username else ""
                    user = SymphonyUser(
                        id=sender_id or "",
                        name=initiator.user.display_name or str(initiator.user.user_id),
                        handle=username,
                        email=email,
                        user_id=initiator.user.user_id,
                    )
                    self._backend.users.add(user)
                    symphony_msg.author = user

                await self._queue.put(symphony_msg)

        # Set up the datafeed
        datafeed_loop = self._bdk.datafeed()
        collector = MessageCollector(
            message_queue,
            channel_id,
            bot_user_id,
            self,
            stream_start_time,
            skip_own,
            skip_history,
        )
        datafeed_loop.subscribe(collector)

        # Start datafeed in background
        datafeed_task = asyncio.create_task(datafeed_loop.start())

        try:
            while not stop_event.is_set():
                try:
                    # Wait for messages with a timeout to allow checking stop_event
                    message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                    yield message
                except asyncio.TimeoutError:
                    continue
        finally:
            # Clean up
            stop_event.set()
            await datafeed_loop.stop()
            datafeed_task.cancel()
            try:
                await datafeed_task
            except asyncio.CancelledError:
                pass
